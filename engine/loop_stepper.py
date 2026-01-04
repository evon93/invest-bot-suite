"""
engine/loop_stepper.py

Deterministic live-like loop stepper for Phase 3C.

Provides:
- step(bar) -> list[dict]: Process single bar, return event dicts
- run(bars, max_steps, sleep_ms) -> dict: Run full simulation
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from contracts.event_messages import OrderIntent
from risk_manager_v0_6 import RiskManagerV06
from risk_manager_v_0_4 import RiskManager as RiskManagerV04
from adapters.risk_input_adapter import adapt_order_intent_to_risk_input
from strategy_engine.strategy_v0_7 import generate_order_intents
from execution.execution_adapter_v0_2 import simulate_execution
from state.position_store_sqlite import PositionStoreSQLite


logger = logging.getLogger(__name__)


class LoopStepper:
    """
    Deterministic live-like loop stepper.
    
    Orchestrates: Strategy -> Risk -> Execution -> State
    All operations are deterministic given the same seed.
    """

    def __init__(
        self,
        *,
        risk_rules: Optional[Union[Dict, str, Path]] = None,
        risk_version: str = "v0.4",
        ticker: str = "BTC-USD",
        strategy_params: Optional[Dict[str, Any]] = None,
        execution_config: Optional[Dict[str, Any]] = None,
        state_db: Optional[Union[str, Path]] = None,
        seed: int = 42,
    ):
        """
        Initialize the loop stepper.
        
        Args:
            risk_rules: Risk rules config path or dict
            risk_version: "v0.4" or "v0.6"
            ticker: Symbol for orders
            strategy_params: Strategy parameters (fast_period, slow_period)
            execution_config: Execution config (slippage_bps, etc.)
            state_db: Path to SQLite state database (optional)
            seed: Random seed for determinism
        """
        self.seed = seed
        self.ticker = ticker
        self.risk_version = risk_version
        self.strategy_params = strategy_params or {"fast_period": 3, "slow_period": 5}
        self.execution_config = execution_config or {"slippage_bps": 5.0, "partial_fill": False}
        
        # Initialize risk manager
        rules = risk_rules if risk_rules else {}
        if risk_version == "v0.6":
            self._risk_v06 = RiskManagerV06(rules)
            self._risk_v04 = self._risk_v06.v04
        else:
            self._risk_v04 = RiskManagerV04(rules)
            self._risk_v06 = None
        
        # Initialize state store if provided
        self._state_store: Optional[PositionStoreSQLite] = None
        if state_db:
            self._state_store = PositionStoreSQLite(state_db)
            self._state_store.ensure_schema()
        
        # Metrics
        self._step_count = 0
        self._event_count = 0
        self._fill_count = 0
        self._rejected_count = 0

    def step(self, ohlcv_slice: pd.DataFrame, bar_idx: int) -> List[Dict[str, Any]]:
        """
        Process a single bar and return list of event dicts.
        
        Args:
            ohlcv_slice: DataFrame containing OHLCV data up to current bar
            bar_idx: Current bar index (for seeding)
            
        Returns:
            List of event dicts (OrderIntent, RiskDecision, ExecutionReport)
        """
        events = []
        self._step_count += 1
        
        if ohlcv_slice.empty:
            return events
        
        # Get current bar timestamp
        last_row = ohlcv_slice.iloc[-1]
        asof_ts = last_row['timestamp'] if 'timestamp' in last_row else pd.Timestamp.now()
        current_price = float(last_row['close'])
        
        # 1. Strategy: Generate order intents
        intents = generate_order_intents(
            ohlcv_slice, self.strategy_params, self.ticker, asof_ts
        )
        
        for intent in intents:
            # Enrich with price context
            intent.meta['current_price'] = current_price
            intent.meta['close'] = current_price
            
            # Convert to event dict
            intent_dict = {
                "type": "OrderIntent",
                "payload": intent.to_dict(),
            }
            events.append(intent_dict)
            self._event_count += 1
            
            # 2. Risk evaluation
            if self.risk_version == "v0.6" and self._risk_v06:
                # Convert to V1 contract
                intent_v1 = OrderIntentV1(
                    symbol=intent.symbol,
                    side=intent.side,
                    qty=intent.qty,
                    notional=intent.notional,
                    order_type=intent.order_type,
                    limit_price=intent.limit_price,
                    event_id=intent.event_id,
                    trace_id=intent.trace_id,
                    meta=intent.meta,
                )
                decision = self._risk_v06.assess(intent_v1)
                decision_dict = {
                    "type": "RiskDecisionV1",
                    "payload": decision.to_dict(),
                }
            else:
                # Use v0.4 shim
                signal = {
                    "assets": [intent.symbol],
                    "deltas": {intent.symbol: 0.10},
                }
                allowed, annotated = self._risk_v04.filter_signal(signal, {}, nav_eur=10000.0)
                decision_dict = {
                    "type": "RiskDecision",
                    "payload": {
                        "ref_order_event_id": intent.event_id,
                        "allowed": allowed,
                        "rejection_reasons": annotated.get("risk_reasons", []),
                    },
                }
                decision = type('Decision', (), {'allowed': allowed, 'rejection_reasons': annotated.get("risk_reasons", [])})()
            
            events.append(decision_dict)
            self._event_count += 1
            
            # 3. Execution (if allowed)
            if decision.allowed:
                exec_seed = self.seed + bar_idx + self._step_count
                reports = simulate_execution([intent], self.execution_config, seed=exec_seed)
                
                for rep in reports:
                    report_dict = {
                        "type": "ExecutionReport",
                        "payload": rep.to_dict(),
                    }
                    events.append(report_dict)
                    self._event_count += 1
                    self._fill_count += 1
                    
                    # Apply to state store if available
                    if self._state_store and rep.status in ("FILLED", "PARTIALLY_FILLED"):
                        self._state_store.apply_fill(
                            symbol=intent.symbol,
                            side=intent.side,
                            qty=rep.filled_qty,
                            price=rep.avg_price,
                        )
            else:
                self._rejected_count += 1
        
        return events

    def run(
        self,
        ohlcv_df: pd.DataFrame,
        *,
        max_steps: Optional[int] = None,
        sleep_ms: int = 0,
        warmup: int = 10,
    ) -> Dict[str, Any]:
        """
        Run full simulation over OHLCV data.
        
        Args:
            ohlcv_df: Full OHLCV DataFrame
            max_steps: Maximum bars to process (None = all after warmup)
            sleep_ms: Sleep between steps (for live-like feel)
            warmup: Warmup period (bars to skip)
            
        Returns:
            Dict with metrics and events
        """
        all_events = []
        
        if len(ohlcv_df) <= warmup:
            logger.warning("Not enough data for simulation (need > %d rows)", warmup)
            return {"events": [], "metrics": self._get_metrics()}
        
        end_idx = len(ohlcv_df)
        if max_steps:
            end_idx = min(warmup + max_steps, len(ohlcv_df))
        
        for i in range(warmup, end_idx):
            # Slice up to current bar (inclusive)
            current_slice = ohlcv_df.iloc[:i+1]
            
            step_events = self.step(current_slice, bar_idx=i)
            all_events.extend(step_events)
            
            if sleep_ms > 0:
                time.sleep(sleep_ms / 1000.0)
        
        return {
            "events": all_events,
            "metrics": self._get_metrics(),
        }

    def _get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "steps": self._step_count,
            "events": self._event_count,
            "fills": self._fill_count,
            "rejected": self._rejected_count,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions from state store."""
        if self._state_store:
            return self._state_store.list_positions()
        return []

    def close(self) -> None:
        """Close resources."""
        if self._state_store:
            self._state_store.close()
