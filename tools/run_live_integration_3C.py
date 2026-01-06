"""
tools/run_live_integration_3C.py

Live-like integration runner for Phase 3C.

Uses the deterministic LoopStepper to simulate trading.
Outputs events.ndjson and run_meta.json.
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure project root is in path
sys.path.append(str(Path(__file__).parent.parent))

from data_adapters.ohlcv_loader import load_ohlcv
from engine.loop_stepper import LoopStepper


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Runner3C")


def run_simulation(
    data_path: Path,
    out_dir: Path,
    *,
    seed: int = 42,
    max_bars: Optional[int] = None,
    sleep_ms: int = 0,
    risk_version: str = "v0.4",
    state_db: Optional[Path] = None,
    ticker: str = "BTC-USD",
    risk_rules: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run live-like simulation.
    
    Args:
        data_path: Path to OHLCV data
        out_dir: Output directory
        seed: Random seed for determinism
        max_bars: Maximum bars to process
        sleep_ms: Sleep between steps (0 = no sleep)
        risk_version: Risk manager version
        state_db: Path to SQLite state database
        ticker: Symbol for orders
        risk_rules: Path to risk rules YAML
        
    Returns:
        Dict with summary info
    """
    logger.info("Starting 3C Simulation (seed=%d, risk=%s)", seed, risk_version)
    
    # 1. Load data
    logger.info("Loading data from %s", data_path)
    ohlcv_df = load_ohlcv(data_path)
    logger.info("Loaded %d rows", len(ohlcv_df))
    
    # 2. Prepare output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "events.ndjson"
    meta_path = out_dir / "run_meta.json"
    
    # 3. Determine state_db path
    state_db_path = state_db if state_db else (out_dir / "state.db")
    
    # 4. Initialize stepper
    rules = str(risk_rules) if risk_rules and risk_rules.exists() else None
    stepper = LoopStepper(
        risk_rules=rules,
        risk_version=risk_version,
        ticker=ticker,
        seed=seed,
        state_db=state_db_path,
    )
    
    # 5. Run simulation
    result = stepper.run(
        ohlcv_df,
        max_steps=max_bars,
        sleep_ms=sleep_ms,
    )
    
    # 6. Write events to NDJSON
    events = result.get("events", [])
    logger.info("Writing %d events to %s", len(events), events_path)
    with open(events_path, "w", encoding="utf-8") as f:
        for evt in events:
            # Deterministic JSON dump
            line = json.dumps(evt, sort_keys=True, separators=(',', ':'))
            f.write(line + "\n")
    
    # 7. Write run metadata
    positions = stepper.get_positions()
    metrics = result.get("metrics", {})
    
    run_meta = {
        "seed": seed,
        "risk_version": risk_version,
        "max_bars": max_bars,
        "state_db": str(state_db_path),
        "ticker": ticker,
        "data_rows": len(ohlcv_df),
        "events_count": len(events),
        "metrics": metrics,
        "final_positions": len(positions),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # TODO: Add engine_version and git_head if available
    }
    
    with open(meta_path, "w", encoding="utf-8") as f:
        # Deterministic JSON dump for meta (pretty print but sorted)
        # Note: indent=2 might vary line endings on some platforms, but usually fine.
        # Strict determinism would prefer compact, but meta is for humans. 
        # Let's use sort_keys=True at least.
        json.dump(run_meta, f, indent=2, sort_keys=True)
    
    logger.info("Run complete. Metrics: %s", metrics)
    
    # 8. Cleanup
    stepper.close()
    
    return {
        "events_path": str(events_path),
        "meta_path": str(meta_path),
        "metrics": metrics,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run Live Integration 3C (deterministic loop stepper)"
    )
    parser.add_argument("--data", required=True, type=Path, help="Path to OHLCV data")
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--max-bars", type=int, default=None, help="Max bars to process")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Sleep between steps (ms)")
    parser.add_argument("--ticker", default="BTC-USD", help="Ticker symbol")
    parser.add_argument(
        "--risk-version",
        choices=["v0.4", "v0.6"],
        default="v0.4",
        help="Risk manager version (default: v0.4)"
    )
    parser.add_argument("--state-db", type=Path, default=None, help="SQLite state DB path")
    parser.add_argument("--risk-rules", type=Path, default=None, help="Risk rules YAML path")
    parser.add_argument(
        "--strict-risk-config",
        type=int,
        choices=[0, 1],
        default=0,
        help="Fail-fast validation of critical keys (default: 0 for 3C compat)"
    )
    
    args = parser.parse_args()
    
    result = run_simulation(
        data_path=args.data,
        out_dir=args.out,
        seed=args.seed,
        max_bars=args.max_bars,
        sleep_ms=args.sleep_ms,
        risk_version=args.risk_version,
        state_db=args.state_db,
        ticker=args.ticker,
        risk_rules=args.risk_rules,
    )
    
    print(f"Simulation complete. Events: {result['events_path']}")


if __name__ == "__main__":
    main()
