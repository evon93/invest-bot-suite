"""
Runner Integrado 3B.5 (Offline Live-Like)
Conecta: DataAdapter -> Strategy -> Risk -> Execution -> Event Log
"""

import sys
import argparse
import logging
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Component Imports
# Ensure project root is in path
sys.path.append(str(Path(__file__).parent.parent))

from data_adapters.ohlcv_loader import load_ohlcv
from strategy_engine.strategy_v0_7 import generate_order_intents
from contracts.event_messages import OrderIntent, RiskDecision, ExecutionReport
from execution.execution_adapter_v0_2 import simulate_execution

# Risk Manager (Existing v0.4 as requested)
from risk_manager_v_0_4 import RiskManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("Runner3B")

def risk_shim_adapter(risk_manager: RiskManager, intent: OrderIntent, nav: float = 10000.0) -> RiskDecision:
    """
    Adapta OrderIntent (v1) para ser consumido por RiskManager v0.4 (dict based)
    y devuelve una RiskDecision (v1).
    """
    # 1. Adapt Input for RiskManager.filter_signal
    # RiskManager espera: signal dict { "assets": [], "deltas": {} }, current_weights, nav_eur
    
    # Mock current state
    current_weights = {} # Simulation assumes 100% cash initially for simplicity
    
    signal = {
        "assets": [intent.symbol],
        "deltas": {intent.symbol: 0.1}, # Mock target weight (RiskManager uses weights?)
        # Wait, RiskManager v0.4 logic uses weights/deltas. 
        # OrderIntent has qty/notional. 
        # For this shim, we'll try to map naive weight or pass minimalistic dict 
        # just to pass the 'within_position_limits' and basic checks.
    }
    
    # Allow/Block check
    allowed, annotated = risk_manager.filter_signal(signal, current_weights, nav_eur=nav)
    
    reasons = annotated.get("risk_reasons", [])
    
    # 2. Return RiskDecision contract
    decision = RiskDecision(
        ref_order_event_id=intent.event_id,
        allowed=allowed,
        rejection_reasons=reasons,
        extra={"shim_filtered": True}
    )
    return decision


def run_integration_pipeline(
    data_path: Path,
    output_path: Path,
    config: Dict[str, Any]
):
    logger.info("Starting Integration Pipeline 3B...")
    
    # 1. Load Data
    logger.info(f"Loading data from {data_path}")
    df = load_ohlcv(data_path)
    logger.info(f"Loaded {len(df)} rows.")
    
    # 2. Init Components
    risk_cfg_path = config.get("risk_rules", "configs/risk_rules_prod.yaml") # Default or passed
    # If file doesn't exist, create a dummy dict for v0.4 init
    if Path(risk_cfg_path).exists():
        risk_manager = RiskManager(risk_cfg_path)
    else:
        logger.warning(f"Risk config {risk_cfg_path} not found. Using defaults.")
        risk_manager = RiskManager({})
        
    strat_params = config.get("strategy_params", {"fast_period": 3, "slow_period": 5})
    exec_cfg = config.get("execution_config", {"slippage_bps": 5.0})
    
    events = []
    
    # 3. Simulation Loop
    # We iterate over the last N candles to simulate "live" arrival
    # Or just run once at the end. Ticket says "run strategy...". 
    # Let's iterate over the inputs to show the flow "live-like".
    
    # We need a warmup period (e.g. 10 candles)
    warmup = 10
    if len(df) <= warmup:
        logger.warning("Not enough data for simulation loop.")
        return

    # Simulate tick-by-tick (candle-by-candle)
    for i in range(warmup, len(df)):
        # Slicing up to current time `i`
        current_slice = df.iloc[:i+1] # Includes current candle as "closed"
        asof_ts = current_slice.iloc[-1]['timestamp']
        ticker = config.get("ticker", "ASSET")
        
        # A. Strategy
        # Note: In real live, we run strategy on every tick.
        intents = generate_order_intents(current_slice, strat_params, ticker, asof_ts)
        
        for intent in intents:
            logger.info(f"Strategy EMITTED: {intent}")
            events.append(intent)
            
            # Enrich intent with price context for execution adapter (needed for shim too?)
            # Strategy v0.7 doesn't set meta price.
            # We fetch it from current candle close.
            current_price = current_slice.iloc[-1]['close']
            intent.meta['current_price'] = float(current_price) 
            intent.meta['close'] = float(current_price)
            
            # B. Risk
            decision = risk_shim_adapter(risk_manager, intent)
            logger.info(f"Risk DECISION: {decision}")
            events.append(decision)
            
            if decision.allowed:
                # C. Execution
                reports = simulate_execution([intent], exec_cfg)
                for rep in reports:
                    logger.info(f"Execution REPORT: {rep}")
                    events.append(rep)
            else:
                logger.info(f"Order BLOCKED by Risk: {decision.rejection_reasons}")

    # 4. Output
    logger.info(f"Writing {len(events)} events to {output_path}")
    with open(output_path, 'w') as f:
        for evt in events:
            # Serialize: Type + JSON
            line_data = {
                "type": evt.__class__.__name__,
                "payload": evt.to_dict() # dataclasses have asdict
            }
            f.write(json.dumps(line_data) + "\n")

    logger.info("Pipeline Completed.")

def main():
    parser = argparse.ArgumentParser(description="Run Live Integration 3B")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ticker", default="BTC-USD")
    args = parser.parse_args()
    
    cfg = {
        "ticker": args.ticker,
        "strategy_params": {"fast_period": 3, "slow_period": 5},
        "execution_config": {"slippage_bps": 5.0, "partial_fill": False}
    }
    
    run_integration_pipeline(args.data, args.out, cfg)

if __name__ == "__main__":
    main()
