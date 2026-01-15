"""
engine/loop_stepper.py

Deterministic live-like loop stepper for Phase 3C.
Extended with granular metrics in AG-3H-1-1.

Provides:
- step(bar) -> list[dict]: Process single bar, return event dicts
- run(bars, max_steps, sleep_ms) -> dict: Run full simulation
- run_bus_mode(): Bus-based event flow with optional metrics instrumentation
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from engine.time_provider import TimeProvider, SimulatedTimeProvider
from engine.exchange_adapter import ExchangeAdapter

import pandas as pd

from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from contracts.event_messages import OrderIntent
from risk_manager_v0_6 import RiskManagerV06
from risk_manager_v_0_4 import RiskManager as RiskManagerV04
from adapters.risk_input_adapter import adapt_order_intent_to_risk_input
from strategy_engine.strategy_registry import get_strategy_fn, DEFAULT_STRATEGY
from execution.execution_adapter_v0_2 import simulate_execution
from state.position_store_sqlite import PositionStoreSQLite


logger = logging.getLogger(__name__)

# Deterministic stage latency deltas for simulated clock mode (nanoseconds)
# These are advanced between metrics timing points to ensure non-zero latencies.
#
# BATCH LATENCY CONTRACT (AG-3I-1-2):
# - strategy: Fixed latency per bar (1ms). Applied once per bar regardless of
#   whether intents are generated. Represents signal generation cost.
#
# - risk, exec, position: Variable latency per item (batch scaling).
#   Total latency = STAGE_LATENCY_NS[stage] * processed
#   Where 'processed' is the number of items processed in that drain iteration.
#   This models backlog/batch processing costs accurately in simulated mode.
#
# Example: If risk_worker processes 3 items in one step:
#   risk_latency_ns = 500_000 * 3 = 1_500_000 ns (1.5ms)
#
STAGE_LATENCY_NS = {
    "strategy": 1_000_000,   # 1ms - signal generation (per bar)
    "risk": 500_000,         # 0.5ms - risk evaluation (per item)
    "exec": 2_000_000,       # 2ms - execution/exchange latency (per item)
    "position": 300_000,     # 0.3ms - position update (per item)
}


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
        time_provider: Optional[TimeProvider] = None,
        seed: int = 42,
        strategy_fn = None,  # AG-3J-1-1: Strategy function injection
    ):
        """
        Initialize the loop stepper.
        """
        self.seed = seed
        import random
        self._rng = random.Random(seed)
        
        # Initialize time provider (default to Simulated for determinism)
        if time_provider:
            self.time_provider = time_provider
        else:
            self.time_provider = SimulatedTimeProvider(seed=seed)
        
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
        self._rejected_count = 0
        
        # AG-3J-1-1: Strategy function (default to v0_7)
        self._strategy_fn = strategy_fn if strategy_fn else get_strategy_fn(DEFAULT_STRATEGY)

    def _gen_uuid(self) -> str:
        """Generate deterministic UUID based on seed."""
        import uuid
        return str(uuid.UUID(int=self._rng.getrandbits(128), version=4))

    def step(self, ohlcv_slice: pd.DataFrame, bar_idx: int) -> List[Dict[str, Any]]:
        """
        Process a single bar and return list of event dicts.
        """
        events = []
        self._step_count += 1
        
        if ohlcv_slice.empty:
            return events
        
        # Get current bar timestamp
        # Advance logical time
        self.time_provider.advance_steps(1)

        last_row = ohlcv_slice.iloc[-1]
        
        if 'timestamp' in last_row:
            asof_ts = last_row['timestamp']
        else:
            # Deterministic fallback using time_provider
            now_ns = self.time_provider.now_ns()
            asof_ts = pd.Timestamp(now_ns, unit='ns', tz='UTC')
        current_price = float(last_row['close'])
        
        # Use ISO format for events, ensuring UTC aware if possible
        if hasattr(asof_ts, "tz") and asof_ts.tz is None:
             # Assume UTC if naive, or just use isoformat
             pass
        
        ts_str = asof_ts.isoformat() if hasattr(asof_ts, "isoformat") else str(asof_ts)

        # 1. Strategy: Generate order intents
        intents = self._strategy_fn(
            ohlcv_slice, self.strategy_params, self.ticker, asof_ts
        )
        
        for intent in intents:
            # Overwrite with deterministic IDs and TS to ensure reproducibility
            # (Strategy might have used random UUIDs)
            intent.event_id = self._gen_uuid()
            intent.trace_id = self._gen_uuid()
            intent.ts = ts_str

            # Enrich with observability metadata
            intent.meta.update({
                "current_price": current_price,
                "close": current_price,
                "step_idx": self._step_count,
                "bar_idx": bar_idx,
                "bar_ts": ts_str,
                "engine_version": "3C.5.2",
                "risk_version": self.risk_version,
            })
            
            # Convert to event dict
            intent_dict = {
                "type": "OrderIntent",
                "payload": intent.to_dict(),
            }
            events.append(intent_dict)
            self._event_count += 1
            
            # 2. Risk evaluation (Always output RiskDecisionV1 canonical)
            decision_event_id = self._gen_uuid()
            
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
                
                # Override with deterministic ID and TS
                decision.event_id = decision_event_id
                decision.ts = ts_str
                
                # Ensure trace_id propagation
                if decision.trace_id != intent.trace_id:
                    decision.trace_id = intent.trace_id
                    
            else:
                # Use v0.4 shim but emit V1 contract
                signal = {
                    "assets": [intent.symbol],
                    "deltas": {intent.symbol: 0.10},
                }
                allowed, annotated = self._risk_v04.filter_signal(signal, {}, nav_eur=10000.0)
                rejection_reasons = annotated.get("risk_reasons", [])
                
                decision = RiskDecisionV1(
                    ref_order_event_id=intent.event_id,
                    allowed=allowed,
                    rejection_reasons=rejection_reasons,
                    trace_id=intent.trace_id,
                    event_id=decision_event_id, # Deterministic ID
                    ts=ts_str, # Deterministic TS
                    extra={
                        "risk_engine": "v0.4",
                        "annotated": annotated,
                        "step_idx": self._step_count,
                    }
                )

            decision_dict = {
                "type": "RiskDecisionV1",
                "payload": decision.to_dict(),
            }
            events.append(decision_dict)
            self._event_count += 1
            
            # 3. Execution (if allowed)
            if decision.allowed:
                exec_seed = self.seed + bar_idx + self._step_count
                reports = simulate_execution([intent], self.execution_config, seed=exec_seed)
                
                for rep in reports:
                    # Enforce V1 conversion/wrapping
                    
                    # Create canonical ExecutionReportV1
                    rep_v1 = ExecutionReportV1(
                        ref_order_event_id=rep.ref_order_event_id,
                        status=rep.status,
                        filled_qty=rep.filled_qty,
                        avg_price=rep.avg_price,
                        fee=rep.fee,
                        slippage=rep.slippage,
                        latency_ms=rep.latency_ms,
                        ref_risk_event_id=decision.event_id,
                        trace_id=intent.trace_id,
                        event_id=self._gen_uuid(), # Deterministic ID
                        ts=ts_str, # Deterministic TS
                        extra=rep.extra or {}
                    )
                    
                    # Add observability
                    rep_v1.extra.update({
                        "step_idx": self._step_count,
                        "engine_version": "3C.5.2",
                    })
                    
                    report_dict = {
                        "type": "ExecutionReportV1",
                        "payload": rep_v1.to_dict(),
                    }
                    events.append(report_dict)
                    self._event_count += 1
                    self._fill_count += 1
                    
                    # Apply to state store if available
                    if self._state_store and rep_v1.status in ("FILLED", "PARTIALLY_FILLED"):
                        self._state_store.apply_fill(
                            symbol=intent.symbol,
                            side=intent.side,
                            qty=rep_v1.filled_qty,
                            price=rep_v1.avg_price,
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

    def run_bus_mode(
        self,
        ohlcv_df: pd.DataFrame,
        bus,  # InMemoryBus
        *,
        max_steps: Optional[int] = None,
        warmup: int = 10,
        max_drain_iterations: int = 100,
        log_jsonl_path: Optional[Union[str, Path]] = None,
        exchange_adapter: Optional[ExchangeAdapter] = None,
        idempotency_store = None,  # Optional IdempotencyStore for crash recovery
        checkpoint = None,  # Optional Checkpoint for progress tracking
        checkpoint_path: Optional[Path] = None,  # Path to save checkpoint
        start_idx: int = 0,  # Start index for resume (0 = from beginning after warmup)
        metrics_collector = None,  # Optional MetricsCollector for granular observability (3H.1)
        stop_controller = None,  # AG-3O-2-1: Graceful shutdown
    ) -> Dict[str, Any]:
        """
        Run simulation using bus-based event flow.
        
        Flow:
        1. Generate OrderIntentV1 and publish to order_intent topic
        2. RiskWorker processes → risk_decision topic
        3. ExecWorker processes → execution_report topic
        4. PositionStoreWorker processes → SQLite updates
        
        Args:
            ohlcv_df: Full OHLCV DataFrame
            bus: InMemoryBus instance
            max_steps: Maximum bars to process (None = all after warmup)
            warmup: Warmup period (bars to skip)
            max_drain_iterations: Max iterations to drain queues (prevents deadlock)
            
        Returns:
            Dict with metrics and published envelopes count
            
        Raises:
            RuntimeError: If queues not drained within max_drain_iterations
        """
        if stop_controller and stop_controller.is_stop_requested:
            return {"metrics": self._get_metrics(), "published": 0, "status": "stopped_early"}

        from engine.bus_workers import (
            RiskWorker, ExecWorker, PositionStoreWorker, DrainWorker,
            TOPIC_ORDER_INTENT, TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
        )
        
        # Initialize JSONL logger if path provided
        jsonl_logger = None
        if log_jsonl_path:
            from engine.structured_jsonl_logger import get_jsonl_logger, log_event, close_jsonl_logger
            jsonl_logger = get_jsonl_logger(log_jsonl_path)
        
        # Initialize workers
        intent_cache: Dict[str, Dict] = {}  # Cache intents for ExecWorker
        
        risk_worker = RiskWorker(
            self._risk_v04,
            gen_event_id=self._gen_uuid,
            jsonl_logger=jsonl_logger,
        )
        exec_worker = ExecWorker(
            self.execution_config,
            gen_event_id=self._gen_uuid,
            intent_cache=intent_cache,
            jsonl_logger=jsonl_logger,
            exchange_adapter=exchange_adapter,
            idempotency_store=idempotency_store,
        )
        pos_worker = PositionStoreWorker(self._state_store, jsonl_logger=jsonl_logger) if self._state_store else None
        # Drain execution_report if no pos_worker (prevents deadlock)
        exec_report_drainer = DrainWorker(TOPIC_EXECUTION_REPORT) if not pos_worker else None
        
        published_count = 0
        
        # Helper for deterministic metrics clock
        def _metrics_clock():
            """Return deterministic time for metrics (seconds from time_provider)."""
            return self.time_provider.now_ns() / 1e9
        
        if len(ohlcv_df) <= warmup:
            logger.warning("Not enough data for simulation (need > %d rows)", warmup)
            return {"metrics": self._get_metrics(), "published": 0}
        
        end_idx = len(ohlcv_df)
        if max_steps:
            end_idx = min(warmup + max_steps, len(ohlcv_df))
        
        # Phase 1: Publish all OrderIntentV1 to bus
        # Resume support: skip already processed indices
        actual_start = warmup + start_idx
        for i in range(actual_start, end_idx):
            # AG-3O-2-1: Check for graceful shutdown request
            if stop_controller and stop_controller.is_stop_requested:
                logger.info("Bus mode: stop requested (%s), draining and exiting...", stop_controller.stop_reason)
                break

            current_slice = ohlcv_df.iloc[:i+1]
            self._step_count += 1
            
            if current_slice.empty:
                continue
            
            last_row = current_slice.iloc[-1]
            last_row = current_slice.iloc[-1]
            if 'timestamp' in last_row:
                asof_ts = last_row['timestamp']
            else:
                # Deterministic fallback
                now_ns = self.time_provider.now_ns()
                asof_ts = pd.Timestamp(now_ns, unit='ns', tz='UTC')
            ts_str = asof_ts.isoformat() if hasattr(asof_ts, "isoformat") else str(asof_ts)
            
            # Metrics: start strategy stage
            strategy_t0 = _metrics_clock() if metrics_collector else 0.0
            
            intents = self._strategy_fn(
                current_slice, self.strategy_params, self.ticker, asof_ts
            )
            
            # Advance simulated time for strategy stage (deterministic latency)
            if hasattr(self.time_provider, 'advance_ns'):
                self.time_provider.advance_ns(STAGE_LATENCY_NS["strategy"])
            
            # Metrics: end strategy stage (per intent)
            strategy_t1 = _metrics_clock() if metrics_collector else 0.0
            
            # Record strategy stage metric (once per bar, regardless of intents generated)
            if metrics_collector:
                metrics_collector.record_stage(
                    stage="strategy",
                    step_id=self._step_count,
                    trace_id=f"bar_{i}",
                    t_start=strategy_t0,
                    t_end=strategy_t1,
                    outcome="ok" if intents else "no_signal",
                )
            
            for intent in intents:
                # Deterministic IDs
                intent.event_id = self._gen_uuid()
                intent.trace_id = self._gen_uuid()
                intent.ts = ts_str
                
                # Cache for ExecWorker (add bar_close for price fallback)
                intent_dict = intent.to_dict()
                if "meta" not in intent_dict or intent_dict["meta"] is None:
                    intent_dict["meta"] = {}
                intent_dict["meta"]["bar_close"] = last_row.get("close", 0.0) if hasattr(last_row, "get") else last_row["close"]
                intent_cache[intent.event_id] = intent_dict
                
                # Publish to bus
                bus.publish(
                    topic=TOPIC_ORDER_INTENT,
                    event_type="OrderIntentV1",
                    trace_id=intent.trace_id,
                    payload=intent_dict,
                )
                published_count += 1
                self._event_count += 1
                
                # Log publish event
                if jsonl_logger:
                    from engine.structured_jsonl_logger import log_event
                    log_event(
                        jsonl_logger,
                        trace_id=intent.trace_id,
                        event_type="OrderIntentV1",
                        step_id=self._step_count,
                        action="publish",
                        topic=TOPIC_ORDER_INTENT,
                        extra={"event_id": intent.event_id, "symbol": intent.symbol},
                    )
            
            # Update checkpoint after processing this bar index
            if checkpoint and checkpoint_path:
                checkpoint = checkpoint.update(i - warmup)  # idx relative to warmup
                checkpoint.save_atomic(checkpoint_path)
        
        # Phase 2: Drain queues with workers
        drain_iter = 0
        while drain_iter < max_drain_iterations:
            drain_iter += 1
            
            # -- Risk Worker Stage --
            risk_t0 = _metrics_clock() if metrics_collector else 0.0
            risk_processed = risk_worker.step(bus, max_items=100)
            # Advance simulated time for risk stage
            if hasattr(self.time_provider, 'advance_ns') and risk_processed > 0:
                self.time_provider.advance_ns(STAGE_LATENCY_NS["risk"] * risk_processed)
            risk_t1 = _metrics_clock() if metrics_collector else 0.0
            
            # Record risk stage metrics (one per processed item)
            if metrics_collector and risk_processed > 0:
                # We record aggregate for the batch with a synthetic trace_id
                metrics_collector.record_stage(
                    stage="risk",
                    step_id=self._step_count,
                    trace_id=f"batch_risk_{drain_iter}",
                    t_start=risk_t0,
                    t_end=risk_t1,
                    outcome="ok",
                )
            
            # -- Exec Worker Stage --
            exec_t0 = _metrics_clock() if metrics_collector else 0.0
            exec_processed = exec_worker.step(bus, max_items=100)
            # Advance simulated time for exec stage
            if hasattr(self.time_provider, 'advance_ns') and exec_processed > 0:
                self.time_provider.advance_ns(STAGE_LATENCY_NS["exec"] * exec_processed)
            exec_t1 = _metrics_clock() if metrics_collector else 0.0
            
            if metrics_collector and exec_processed > 0:
                metrics_collector.record_stage(
                    stage="exec",
                    step_id=self._step_count,
                    trace_id=f"batch_exec_{drain_iter}",
                    t_start=exec_t0,
                    t_end=exec_t1,
                    outcome="ok",
                )
            
            # -- Position Store Stage --
            pos_t0 = _metrics_clock() if metrics_collector else 0.0
            if pos_worker:
                pos_processed = pos_worker.step(bus, max_items=100)
            elif exec_report_drainer:
                pos_processed = exec_report_drainer.step(bus, max_items=100)
            else:
                pos_processed = 0
            # Advance simulated time for position stage
            if hasattr(self.time_provider, 'advance_ns') and pos_processed > 0:
                self.time_provider.advance_ns(STAGE_LATENCY_NS["position"] * pos_processed)
            pos_t1 = _metrics_clock() if metrics_collector else 0.0
            
            if metrics_collector and pos_processed > 0:
                metrics_collector.record_stage(
                    stage="position",
                    step_id=self._step_count,
                    trace_id=f"batch_position_{drain_iter}",
                    t_start=pos_t0,
                    t_end=pos_t1,
                    outcome="ok",
                )
            
            total_processed = risk_processed + exec_processed + pos_processed
            
            # Check if all queues are empty
            intent_pending = bus.size(TOPIC_ORDER_INTENT)
            decision_pending = bus.size(TOPIC_RISK_DECISION)
            report_pending = bus.size(TOPIC_EXECUTION_REPORT)
            
            if intent_pending == 0 and decision_pending == 0 and report_pending == 0:
                logger.info("Bus mode: all queues drained after %d iterations", drain_iter)
                break
            
            if total_processed == 0 and (intent_pending + decision_pending + report_pending) > 0:
                # Stuck: events in queue but no progress
                raise RuntimeError(
                    f"Bus mode deadlock: pending events but no progress. "
                    f"intent={intent_pending}, decision={decision_pending}, report={report_pending}"
                )
        else:
            raise RuntimeError(
                f"Bus mode: max_drain_iterations ({max_drain_iterations}) exceeded. "
                f"Queues not empty: intent={bus.size(TOPIC_ORDER_INTENT)}, "
                f"decision={bus.size(TOPIC_RISK_DECISION)}, report={bus.size(TOPIC_EXECUTION_REPORT)}"
            )
        
        # Update metrics from workers
        self._fill_count = exec_worker._fill_count
        self._rejected_count = risk_worker._processed_count - exec_worker._fill_count
        
        # Close JSONL logger
        if jsonl_logger:
            from engine.structured_jsonl_logger import log_event, close_jsonl_logger
            log_event(
                jsonl_logger,
                trace_id="SYSTEM",
                event_type="BusModeDone",
                step_id=self._step_count,
                action="complete",
                extra={"published": published_count, "drain_iterations": drain_iter},
            )
            close_jsonl_logger(jsonl_logger)
        
        return {
            "metrics": self._get_metrics(),
            "published": published_count,
            "drain_iterations": drain_iter,
        }

    def _step_with_adapter(
        self,
        ohlcv_slice: pd.DataFrame,
        bar_idx: int,
        exchange_adapter: ExchangeAdapter,
        current_step_ts: int,
    ) -> List[Dict[str, Any]]:
        """
        Process single bar with ExchangeAdapter for execution.
        
        AG-3M-1-1: End-to-end wiring:
        Strategy -> Risk -> Exec (via ExchangeAdapter) -> PositionStore
        
        Args:
            ohlcv_slice: OHLCV DataFrame up to current bar
            bar_idx: Current bar index
            exchange_adapter: ExchangeAdapter instance (paper/stub)
            current_step_ts: Current step timestamp in milliseconds
            
        Returns:
            List of event dicts (OrderIntent, RiskDecisionV1, ExecutionReportV1)
        """
        from engine.exchange_adapter import ExecutionContext
        
        events = []
        self._step_count += 1
        
        if ohlcv_slice.empty:
            return events
        
        # Advance logical time
        self.time_provider.advance_steps(1)
        
        last_row = ohlcv_slice.iloc[-1]
        
        if 'timestamp' in last_row:
            asof_ts = last_row['timestamp']
        else:
            now_ns = self.time_provider.now_ns()
            asof_ts = pd.Timestamp(now_ns, unit='ns', tz='UTC')
        current_price = float(last_row['close'])
        ts_str = asof_ts.isoformat() if hasattr(asof_ts, "isoformat") else str(asof_ts)
        
        # 1. Strategy: Generate order intents
        intents = self._strategy_fn(
            ohlcv_slice, self.strategy_params, self.ticker, asof_ts
        )
        
        for intent in intents:
            # Deterministic IDs
            intent.event_id = self._gen_uuid()
            intent.trace_id = self._gen_uuid()
            intent.ts = ts_str
            
            # Enrich with metadata
            intent.meta.update({
                "current_price": current_price,
                "close": current_price,
                "step_idx": self._step_count,
                "bar_idx": bar_idx,
                "bar_ts": ts_str,
                "engine_version": "3M.1",
                "risk_version": self.risk_version,
            })
            
            # Emit OrderIntent event
            intent_dict = {
                "type": "OrderIntent",
                "payload": intent.to_dict(),
            }
            events.append(intent_dict)
            self._event_count += 1
            
            # 2. Risk evaluation
            decision_event_id = self._gen_uuid()
            
            if self.risk_version == "v0.6" and self._risk_v06:
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
                decision.event_id = decision_event_id
                decision.ts = ts_str
                if decision.trace_id != intent.trace_id:
                    decision.trace_id = intent.trace_id
            else:
                signal = {
                    "assets": [intent.symbol],
                    "deltas": {intent.symbol: 0.10},
                }
                allowed, annotated = self._risk_v04.filter_signal(signal, {}, nav_eur=10000.0)
                rejection_reasons = annotated.get("risk_reasons", [])
                
                decision = RiskDecisionV1(
                    ref_order_event_id=intent.event_id,
                    allowed=allowed,
                    rejection_reasons=rejection_reasons,
                    trace_id=intent.trace_id,
                    event_id=decision_event_id,
                    ts=ts_str,
                    extra={
                        "risk_engine": "v0.4",
                        "annotated": annotated,
                        "step_idx": self._step_count,
                    }
                )
            
            # Emit RiskDecisionV1 event
            decision_dict = {
                "type": "RiskDecisionV1",
                "payload": decision.to_dict(),
            }
            events.append(decision_dict)
            self._event_count += 1
            
            # 3. Execution via ExchangeAdapter (if allowed)
            if decision.allowed:
                # Create OrderIntentV1 for adapter
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
                
                # Build execution context
                context: ExecutionContext = {
                    "step_id": self._step_count,
                    "time_provider": self.time_provider,
                }
                
                # Submit via ExchangeAdapter
                report_event_id = self._gen_uuid()
                extra_meta = {
                    "current_price": current_price,
                    "close": current_price,
                    "bar_close": current_price,
                    "ts": ts_str,
                }
                
                report = exchange_adapter.submit(
                    intent=intent_v1,
                    decision=decision,
                    context=context,
                    report_event_id=report_event_id,
                    extra_meta=extra_meta,
                )
                
                # Enrich report with observability
                report.extra = report.extra or {}
                report.extra.update({
                    "step_idx": self._step_count,
                    "engine_version": "3M.1",
                    "adapter_mode": True,
                })
                
                # Emit ExecutionReportV1 event
                report_dict = {
                    "type": "ExecutionReportV1",
                    "payload": report.to_dict(),
                }
                events.append(report_dict)
                self._event_count += 1
                self._fill_count += 1
                
                # 4. Apply to PositionStore if available
                if self._state_store and report.status in ("FILLED", "PARTIALLY_FILLED"):
                    self._state_store.apply_fill(
                        symbol=intent.symbol,
                        side=intent.side,
                        qty=report.filled_qty,
                        price=report.avg_price,
                    )
            else:
                self._rejected_count += 1
        
        return events

    def run_adapter_mode(
        self,
        adapter,  # MarketDataAdapter Protocol
        *,
        max_steps: Optional[int] = None,
        warmup: int = 10,
        log_jsonl_path: Optional[Union[str, Path]] = None,
        metrics_collector = None,
        exchange_adapter: Optional[ExchangeAdapter] = None,
        checkpoint = None,  # AG-3M-2-1: Optional Checkpoint for progress tracking
        checkpoint_path: Optional[Path] = None,  # AG-3M-2-1: Path to save checkpoint
        start_idx: int = 0,  # AG-3M-2-1: Resume from this step index
        stop_controller = None,  # AG-3O-2-1: Graceful shutdown
    ) -> Dict[str, Any]:
        """
        Run simulation consuming events directly from MarketDataAdapter.
        
        AG-3L-1-1: Direct adapter integration without public DataFrame bridge.
        AG-3M-1-1: End-to-end execution via ExchangeAdapter (paper/stub).
        AG-3M-2-1: Checkpoint/resume support for crash recovery.
        
        Flow:
        1. Use adapter.peek_next_ts() to know next event timestamp
        2. Call adapter.poll(max_items=1, up_to_ts=current_step_ts)
        3. Guard: assert no event has ts > current_step_ts (no-lookahead)
        4. Build incremental OHLCV slice internally (private helper)
        5. Process: Strategy -> Risk -> Exec (via exchange_adapter) -> PositionStore
        6. Save checkpoint after each step (if checkpoint provided)
        
        Args:
            adapter: MarketDataAdapter instance (must implement poll, peek_next_ts)
            max_steps: Maximum bars to process (None = all after warmup)
            warmup: Warmup period (bars to skip)
            log_jsonl_path: Optional path for JSONL logging
            metrics_collector: Optional MetricsCollector for observability
            exchange_adapter: Optional ExchangeAdapter for execution (paper/stub)
            checkpoint: Optional Checkpoint for progress tracking (AG-3M-2-1)
            checkpoint_path: Path to save checkpoint (AG-3M-2-1)
            start_idx: Resume from this step index (AG-3M-2-1)
            
        Returns:
            Dict with metrics and events
            
        Raises:
            AssertionError: If adapter returns event with ts > current_step_ts (lookahead)
        """
        if stop_controller and stop_controller.is_stop_requested:
            return {"metrics": self._get_metrics(), "published": 0, "status": "stopped_early"}

        all_events = []
        
        # Initialize JSONL logger if path provided
        jsonl_logger = None
        if log_jsonl_path:
            from engine.structured_jsonl_logger import get_jsonl_logger, log_event, close_jsonl_logger
            jsonl_logger = get_jsonl_logger(log_jsonl_path)
        
        # Internal OHLCV accumulator (private - NOT exposed as API)
        # This is the "shim interno" that builds DataFrame incrementally for step()
        _ohlcv_rows = []
        
        # Helper for deterministic metrics clock
        def _metrics_clock():
            return self.time_provider.now_ns() / 1e9
        
        # Track consumed events
        consumed_count = 0
        step_count = 0
        
        # AG-3M-2-1: Resume support
        # If resuming (start_idx > 0), we need to:
        # 1. Skip warmup (already done in previous run)
        # 2. Skip already-processed steps
        # 3. Rebuild _ohlcv_rows to have correct slice for strategy
        is_resuming = start_idx > 0
        
        # Warmup phase: consume without processing (skip if resuming)
        warmup_consumed = 0
        if not is_resuming:
            while warmup_consumed < warmup:
                next_ts = adapter.peek_next_ts()
                if next_ts is None:
                    logger.warning(
                        "Adapter exhausted during warmup (consumed %d of %d required)",
                        warmup_consumed, warmup
                    )
                    break
                
                events = adapter.poll(max_items=1)
                if not events:
                    break
                
                event = events[0]
                _ohlcv_rows.append({
                    "timestamp": pd.Timestamp(event.ts, unit="ms", tz="UTC"),
                    "open": event.open,
                    "high": event.high,
                    "low": event.low,
                    "close": event.close,
                    "volume": event.volume,
                })
                warmup_consumed += 1
                consumed_count += 1
            
            if warmup_consumed < warmup:
                return {"events": [], "metrics": self._get_metrics(), "consumed": consumed_count}
        else:
            # Resuming: skip warmup + already processed steps
            # We need to consume (warmup + start_idx) events to rebuild state
            skip_count = warmup + start_idx
            for _ in range(skip_count):
                next_ts = adapter.peek_next_ts()
                if next_ts is None:
                    break
                events = adapter.poll(max_items=1)
                if not events:
                    break
                event = events[0]
                _ohlcv_rows.append({
                    "timestamp": pd.Timestamp(event.ts, unit="ms", tz="UTC"),
                    "open": event.open,
                    "high": event.high,
                    "low": event.low,
                    "close": event.close,
                    "volume": event.volume,
                })
                consumed_count += 1
            
            logger.info("Resumed adapter-mode: skipped %d events (warmup=%d, processed=%d)",
                       consumed_count, warmup, start_idx)
        
        # Main processing loop
        end_steps = max_steps if max_steps else float('inf')
        
        while step_count < end_steps:
            # AG-3O-2-1: Check for graceful shutdown request
            if stop_controller and stop_controller.is_stop_requested:
                logger.info("Adapter mode: stop requested (%s), exiting...", stop_controller.stop_reason)
                break

            next_ts = adapter.peek_next_ts()
            if next_ts is None:
                # Adapter exhausted
                break
            
            # Current step timestamp is the next event's ts
            current_step_ts = next_ts
            
            # Poll with up_to_ts boundary (no-lookahead enforcement)
            events = adapter.poll(max_items=1, up_to_ts=current_step_ts)
            
            if not events:
                # No more events within boundary
                break
            
            event = events[0]
            
            # NO-LOOKAHEAD GUARD (critical invariant)
            assert event.ts <= current_step_ts, (
                f"Lookahead violation: event.ts={event.ts} > current_step_ts={current_step_ts}"
            )
            
            # Accumulate to internal OHLCV slice
            _ohlcv_rows.append({
                "timestamp": pd.Timestamp(event.ts, unit="ms", tz="UTC"),
                "open": event.open,
                "high": event.high,
                "low": event.low,
                "close": event.close,
                "volume": event.volume,
            })
            consumed_count += 1
            
            # Build DataFrame slice for step()
            ohlcv_slice = pd.DataFrame(_ohlcv_rows)
            
            # Metrics: start strategy stage
            strategy_t0 = _metrics_clock() if metrics_collector else 0.0
            
            bar_idx = len(_ohlcv_rows) - 1
            
            # AG-3M-1-1: When exchange_adapter is provided, do end-to-end wiring
            # Strategy -> Risk -> Exec (via ExchangeAdapter) -> PositionStore
            if exchange_adapter is not None:
                step_events_list = self._step_with_adapter(
                    ohlcv_slice, bar_idx, exchange_adapter, current_step_ts
                )
            else:
                # Original behavior: use step() which uses simulate_execution()
                step_events_list = self.step(ohlcv_slice, bar_idx=bar_idx)
            
            all_events.extend(step_events_list)
            step_count += 1
            
            # Advance simulated time for strategy stage
            if hasattr(self.time_provider, 'advance_ns'):
                self.time_provider.advance_ns(STAGE_LATENCY_NS["strategy"])
            
            strategy_t1 = _metrics_clock() if metrics_collector else 0.0
            
            # Record strategy stage metric
            if metrics_collector:
                metrics_collector.record_stage(
                    stage="strategy",
                    step_id=self._step_count,
                    trace_id=f"adapter_bar_{bar_idx}",
                    t_start=strategy_t0,
                    t_end=strategy_t1,
                    outcome="ok" if step_events_list else "no_signal",
                )
            
            # Log to JSONL
            if jsonl_logger and step_events_list:
                from engine.structured_jsonl_logger import log_event
                for evt in step_events_list:
                    log_event(
                        jsonl_logger,
                        trace_id=evt.get("payload", {}).get("trace_id", "unknown"),
                        event_type=evt.get("type", "unknown"),
                        step_id=self._step_count,
                        action="emit",
                        extra={"bar_idx": bar_idx},
                    )
            
            # AG-3M-2-1: Update and save checkpoint after each step
            if checkpoint and checkpoint_path:
                # step_count is 1-indexed here (incremented above), use as processed index
                checkpoint = checkpoint.update(start_idx + step_count - 1)
                checkpoint.save_atomic(checkpoint_path)
        
        # Close JSONL logger
        if jsonl_logger:
            from engine.structured_jsonl_logger import log_event, close_jsonl_logger
            log_event(
                jsonl_logger,
                trace_id="SYSTEM",
                event_type="AdapterModeDone",
                step_id=self._step_count,
                action="complete",
                extra={"consumed": consumed_count, "steps": step_count},
            )
            close_jsonl_logger(jsonl_logger)
        
        return {
            "events": all_events,
            "metrics": self._get_metrics(),
            "consumed": consumed_count,
            "steps_processed": step_count,
        }

