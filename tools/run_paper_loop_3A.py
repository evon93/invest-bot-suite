#!/usr/bin/env python3
"""
tools/run_paper_loop_3A.py

Paper Trading Simulator Loop (AG-3A-2-1).
Consumes signals (OrderIntent) from NDJSON, validates against Risk Rules,
and generates Mock Fills or Rejections.

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
from pathlib import Path
from typing import Dict, Any, List

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# from definitions import RiskContext  # Removed: definitions module not found in root
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
            "rejection_reasons": {}
        }
        
        # Risk Context Mock (Empty for now, or minimal)
        # In a real loop, this would track portfolio state.
        # For v0.4, filter_signal might expect 'signal' dict + 'context'.
        self.mock_context = {
            "portfolio": {"nav": 100000.0, "cash": 100000.0, "positions": {}},
            "prices": {} # Updated per signal
        }

    def process_signal(self, order_intent: OrderIntent) -> List[Any]:
        """
        Process a single OrderIntent -> RiskDecision -> ExecutionReport
        """
        events = []
        
        # 1. Adapt OrderIntent to RiskManager signal format (legacy dict)
        # Assuming v0.4 expects a dict with 'symbol', 'side', 'qty', etc.
        signal_dict = {
            "symbol": order_intent.symbol,
            "side": order_intent.side,
            "qty": order_intent.qty,
            "price": order_intent.limit_price or 100.0, # Mock price if missing
            "strategy": order_intent.meta.get("strategy", "unknown"),
            "timestamp": order_intent.ts
        }
        
        # Update mock context prices for this symbol to avoid "missing price" errors
        self.mock_context["prices"][order_intent.symbol] = signal_dict["price"]
        
        # 2. Risk Check
        # Call filter_signal(signal, context=...)
        # Note: v0.4 signature might vary, usually it returns (is_allowed, reasons/modifications)
        # We need to handle the return type defensively.
        try:
            # Inspection of RiskManager v0.4 usually shows filter_signal(signal, additional_args)
            # We'll try passing context as kwargs or second arg if supported.
            # Shim v0.4 usually proxies to real implementation.
            # Let's assume standard protocol: result = rm.filter_signal(signal_dict)
            # Result is often boolean or (bool, reason).
            
            # Since we don't have exact signature due to shim obscuring it, let's try standard call
            # and catch TypeError if needed, or inspect attributes.
            # Most v0.4 implementations in this repo return: ALLOWED (bool) or similar.
            
            # HACK: v0.4 shim often doesn't enforce strict context.
            # We will pass the signal.
            
            # Let's look at what filter_signal returns.
            # If it's the class from risk_manager_v_0_4.py:
            # def filter_signal(self, signal: dict) -> bool: ...
            
            # We pass signal_dict using standard keys.
            # We pass signal_dict using standard keys, plus current_weights
            decision = self.risk_manager.filter_signal(signal_dict, self.mock_context["portfolio"]["positions"])
            
            # Normalize decision
            allowed = False
            reasons = []
            
            if isinstance(decision, bool):
                allowed = decision
                if not allowed:
                    reasons = ["RiskManager rejected (bool)"]
            elif isinstance(decision, tuple):
                 # Support (bool, list)
                 allowed = decision[0]
                 reasons = decision[1] if len(decision) > 1 else []
            else:
                # Unknown return
                allowed = bool(decision)
        
        except Exception as e:
            logger.error(f"Error in risk check: {e}")
            allowed = False
            reasons = [f"Risk Check Error: {str(e)}"]

        # 3. Create RiskDecision Event
        risk_event = RiskDecision(
            ref_order_event_id=order_intent.event_id,
            allowed=allowed,
            rejection_reasons=reasons
        )
        events.append(risk_event)
        
        if allowed:
            self.metrics["n_allowed"] += 1
            
            # 4. Mock Execution (Fill)
            # Simulate latency
            time.sleep(self.latency_ms / 1000.0) 
            
            fill_price = signal_dict["price"]
            # Apply mock slippage (random -1bps to +1bps for smoke)
            slippage = fill_price * random.uniform(-0.0001, 0.0001)
            exec_price = fill_price + slippage
            
            exec_report = ExecutionReport(
                ref_order_event_id=order_intent.event_id,
                ref_risk_event_id=risk_event.event_id,
                status="FILLED",
                filled_qty=order_intent.qty or (order_intent.notional / exec_price),
                avg_price=exec_price,
                slippage=slippage,
                latency_ms=self.latency_ms
            )
            self.metrics["n_fills"] += 1
            events.append(exec_report)
            
        else:
            self.metrics["n_rejected"] += 1
            # Track reasons
            for r in reasons:
                self.metrics["rejection_reasons"][str(r)] = self.metrics["rejection_reasons"].get(str(r), 0) + 1
                
            # Create Rejected Execution Report
            exec_report = ExecutionReport(
                ref_order_event_id=order_intent.event_id,
                ref_risk_event_id=risk_event.event_id,
                status="REJECTED",
                extra={"reasons": reasons}
            )
            events.append(exec_report)

        return events

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
                    # Parse OrderIntent
                    data = json.loads(line)
                    # Support legacy or schema format
                    if "schema_id" in data and data["schema_id"] == "OrderIntent":
                        intent = OrderIntent.from_dict(data)
                    else:
                        # Skip unknown or try to adapt
                        continue
                    
                    self.metrics["n_signals"] += 1
                    
                    # Log Intent first
                    fout.write(intent.to_json() + "\n")
                    
                    # Process
                    generated_events = self.process_signal(intent)
                    
                    # Log generated events
                    for ev in generated_events:
                        fout.write(ev.to_json() + "\n")
                        
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process line: {e}")
        
        # Save Metrics
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
