#!/usr/bin/env python3
"""
tools/run_paper_loop_3A.py

Paper Trading Simulator Loop (AG-3A-2-1 + AG-3A-3-1 + AG-3A-3-2).
Consumes signals (OrderIntent) from NDJSON, validates against Risk Rules,
and generates Mock Fills or Rejections with observability metrics.

Usage:
  python tools/run_paper_loop_3A.py --signals examples/signals_3A.ndjson \
    --risk-config configs/risk_rules_prod.yaml \
    --outdir report/runs/3A_paper_smoke
"""

import argparse
import json
import logging
import sys
import time
import random
import math
from pathlib import Path
from typing import Dict, Any, List, Union

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Note: In v0.4, RiskManager expects specific arguments. 
# We'll use the Factory to get the manager.
from risk_manager_factory import get_risk_manager
from contracts.event_messages import (
    OrderIntent, RiskDecision, ExecutionReport, ExecutionContext
)

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PaperLoop")

class PaperLoop:
    def __init__(self, risk_config_path: str, seed: int = 42, latency_ms: float = 50.0):
        self.risk_config_path = Path(risk_config_path)
        if not self.risk_config_path.exists():
            raise FileNotFoundError(f"Config not found: {risk_config_path}")
        
        # Load Risk Manager
        logger.info(f"Loading RiskManager from {risk_config_path}")
        self.risk_manager = get_risk_manager(rules=self.risk_config_path)
        
        # Simulation State
        random.seed(seed)
        self.latency_ms = latency_ms
        self.metrics = {
            "n_signals": 0,
            "n_allowed": 0,
            "n_rejected": 0,
            "n_fills": 0,
            "rejection_reasons": {}, 
            "rejected_by_reason": {}, # Alias
            "max_gross_exposure_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "active_rate": 0.0,
            "latency_ms_mean": 0.0,
            "latency_ms_p95": 0.0
        }
        
        # Internal state for metrics
        self._latencies_ms = []
        self._nav_series = []
        self._samples_count = 0
        self._active_samples_count = 0
        
        # Risk Context Mock
        self.mock_context = {
            "portfolio": {
                "nav": 100000.0, 
                "cash": 100000.0, 
                "positions": {} # symbol -> qty
            },
            "prices": {} # symbol -> price
        }
        
        self.initial_nav = 100000.0

    def _normalize_reasons(self, reasons: Union[List, Dict, str, Any]) -> List[str]:
        """
        Normalize rejection reasons to a stable list of strings.
        Truncates long strings to avoid exploding metrics cardinality.
        """
        normalized = []
        try:
            if isinstance(reasons, list):
                for r in reasons:
                    normalized.append(str(r)[:100])
            elif isinstance(reasons, dict):
                # If dict, keys are usually the identifiers
                for k in reasons.keys():
                    normalized.append(str(k)[:100])
            elif isinstance(reasons, str):
                normalized.append(reasons[:100])
            else:
                normalized.append(str(reasons)[:100])
        except Exception:
            normalized.append("unknown_parse_error")
            
        return [n for n in normalized if n]

    def _update_portfolio_valuation(self):
        """Re-calculate NAV and exposure based on current prices and positions."""
        cash = self.mock_context["portfolio"]["cash"]
        positions = self.mock_context["portfolio"]["positions"]
        prices = self.mock_context["prices"]
        
        pos_value = 0.0
        gross_pos_value = 0.0
        
        for sym, qty in positions.items():
            price = prices.get(sym, 0.0)
            val = qty * price
            pos_value += val
            gross_pos_value += abs(val)
            
        nav = cash + pos_value
        self.mock_context["portfolio"]["nav"] = nav
        
        # Exposure Metric
        gross_exposure_pct = 0.0
        if nav > 0:
            gross_exposure_pct = gross_pos_value / nav
            
        self.metrics["max_gross_exposure_pct"] = max(
            self.metrics["max_gross_exposure_pct"], gross_exposure_pct
        )
        
        # Drawdown Metric
        peak_nav = max(self.initial_nav, *self._nav_series) if self._nav_series else self.initial_nav
        peak_nav = max(peak_nav, nav)
        
        dd_pct = 0.0
        if peak_nav > 0:
            dd_pct = (nav / peak_nav) - 1.0
            
        self.metrics["max_drawdown_pct"] = min(
            self.metrics["max_drawdown_pct"], dd_pct
        )
        
        # Active Rate (Sample)
        self._samples_count += 1
        if gross_exposure_pct > 0.0001: # Epsilon
            self._active_samples_count += 1
            
        self._nav_series.append(nav)

    def process_signal(self, order_intent: OrderIntent) -> List[Any]:
        """
        Process a single OrderIntent -> RiskDecision -> ExecutionReport
        """
        events = []
        
        # 1. Update Market Data
        current_price = order_intent.limit_price
        if current_price is None or current_price <= 0:
            current_price = order_intent.meta.get("price", 100.0)
        
        self.mock_context["prices"][order_intent.symbol] = current_price
        
        self._update_portfolio_valuation()
        
        # 2. Risk Check
        signal_dict = {
            "symbol": order_intent.symbol,
            "side": order_intent.side,
            "qty": order_intent.qty, 
            "price": current_price,
            "strategy": order_intent.meta.get("strategy", "unknown"),
            "timestamp": order_intent.ts
        }
        
        try:
            positions = self.mock_context["portfolio"]["positions"]
            decision = self.risk_manager.filter_signal(signal_dict, positions)
            
            allowed = False
            reasons = []
            
            if isinstance(decision, bool):
                allowed = decision
                if not allowed:
                    reasons = ["RiskManager rejected (bool)"]
            elif isinstance(decision, tuple):
                 allowed = decision[0]
                 reasons = decision[1] if len(decision) > 1 else []
            else:
                allowed = bool(decision)
        
        except Exception as e:
            logger.error(f"Error in risk check: {e}")
            allowed = False
            reasons = [f"Risk Check Error: {str(e)}"]

        # Normalize reasons
        if not allowed:
            reasons = self._normalize_reasons(reasons)

        # 3. Create RiskDecision Event
        risk_event = RiskDecision(
            ref_order_event_id=order_intent.event_id,
            allowed=allowed,
            rejection_reasons=reasons, 
            trace_id=order_intent.trace_id
        )
        events.append(risk_event)
        
        if allowed:
            self.metrics["n_allowed"] += 1
            
            if self.latency_ms > 0:
                time.sleep(self.latency_ms / 1000.0)
            
            self._latencies_ms.append(self.latency_ms)
            
            fill_price = current_price
            slippage = fill_price * random.uniform(-0.0001, 0.0001)
            exec_price = fill_price + slippage
            
            fill_qty = order_intent.qty
            if fill_qty is None and order_intent.notional:
                fill_qty = order_intent.notional / exec_price
            
            if fill_qty is None: fill_qty = 0.0
            
            cost = fill_qty * exec_price
            if order_intent.side == "BUY":
                self.mock_context["portfolio"]["cash"] -= cost
                self.mock_context["portfolio"]["positions"][order_intent.symbol] = \
                    self.mock_context["portfolio"]["positions"].get(order_intent.symbol, 0.0) + fill_qty
            else:
                self.mock_context["portfolio"]["cash"] += cost
                self.mock_context["portfolio"]["positions"][order_intent.symbol] = \
                    self.mock_context["portfolio"]["positions"].get(order_intent.symbol, 0.0) - fill_qty

            exec_report = ExecutionReport(
                ref_order_event_id=order_intent.event_id,
                ref_risk_event_id=risk_event.event_id,
                status="FILLED",
                filled_qty=fill_qty,
                avg_price=exec_price,
                slippage=slippage,
                latency_ms=self.latency_ms,
                trace_id=order_intent.trace_id
            )
            self.metrics["n_fills"] += 1
            events.append(exec_report)
            
        else:
            self.metrics["n_rejected"] += 1
            # Track reasons (using normalized)
            for r in reasons:
                self.metrics["rejection_reasons"][r] = self.metrics["rejection_reasons"].get(r, 0) + 1
                
            # Create Rejected Execution Report
            exec_report = ExecutionReport(
                ref_order_event_id=order_intent.event_id,
                ref_risk_event_id=risk_event.event_id,
                status="REJECTED",
                extra={"reasons": reasons},
                trace_id=order_intent.trace_id
            )
            events.append(exec_report)
            self._latencies_ms.append(0.0)

        self._update_portfolio_valuation()

        return events
        
    def _finalize_metrics(self):
        """Calculate aggregate metrics."""
        # Active Rate
        if self._samples_count > 0:
            self.metrics["active_rate"] = self._active_samples_count / self._samples_count
            
        # Latency Stats
        if self._latencies_ms:
            total_lat = sum(self._latencies_ms)
            count_lat = len(self._latencies_ms)
            self.metrics["latency_ms_mean"] = total_lat / count_lat
            
            # Robust P95 without statistics module
            sorted_lat = sorted(self._latencies_ms)
            idx = int(count_lat * 0.95)
            # Ensure index is within bounds (0-indexed)
            if idx >= count_lat: idx = count_lat - 1
            self.metrics["latency_ms_p95"] = sorted_lat[idx]
            
        # Alias rejected_by_reason
        self.metrics["rejected_by_reason"] = self.metrics["rejection_reasons"].copy()

    def run(self, signals_path: str, out_dir: str, max_events: int = 50):
        # Prepare output
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        events_file = out_path / "events.ndjson"
        
        logger.info(f"Processing signals from {signals_path}...")
        
        count = 0
        with open(signals_path, "r") as fin, open(events_file, "w") as fout:
            for line in fin:
                if count >= max_events:
                    break
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    if "schema_id" in data and data["schema_id"] == "OrderIntent":
                        intent = OrderIntent.from_dict(data)
                    else:
                        continue
                    
                    self.metrics["n_signals"] += 1
                    fout.write(intent.to_json() + "\n")
                    
                    generated_events = self.process_signal(intent)
                    
                    for ev in generated_events:
                        fout.write(ev.to_json() + "\n")
                        
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process line: {e}")
        
        self._finalize_metrics()
        
        metrics_file = out_path / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)
            
        logger.info(f"Run complete. Metrics: {self.metrics}")

def main():
    parser = argparse.ArgumentParser(description="Paper Trading Loop 3A")
    parser.add_argument("--signals", required=True, help="Path to signals NDJSON")
    parser.add_argument("--risk-config", required=True, help="Path to Risk Config YAML")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--max-events", type=int, default=50, help="Max signals to process")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--latency-ms", type=float, default=50.0, help="Mock latency ms")
    
    args = parser.parse_args()
    
    try:
        loop = PaperLoop(args.risk_config, args.seed, args.latency_ms)
        loop.run(args.signals, args.outdir, args.max_events)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
