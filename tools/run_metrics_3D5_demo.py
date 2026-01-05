"""
tools/run_metrics_3D5_demo.py

Demonstration of deterministic run metrics collection (3D.5).
Executes a bus mode simulation with logging, then collects metrics from logs.

Output:
- report/out_3D5_metrics/trace.jsonl
- report/out_3D5_metrics/run_metrics.json
- report/out_3D5_metrics/state.db
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper
from engine.run_metrics_3D5 import collect_metrics_from_jsonl


def make_ohlcv_df(n_bars: int = 20, seed: int = 42) -> pd.DataFrame:
    """Create deterministic OHLCV DataFrame."""
    np.random.seed(seed)
    
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    closes = 100.0 + np.cumsum(np.random.randn(n_bars) * 2)
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes - 0.5,
        "high": closes + 1.0,
        "low": closes - 1.0,
        "close": closes,
        "volume": np.random.randint(1000, 10000, n_bars),
    })


def main():
    # Setup paths
    out_dir = Path("report/out_3D5_metrics")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = out_dir / "state.db"
    log_path = out_dir / "trace.jsonl"
    metrics_path = out_dir / "run_metrics.json"
    
    # Clean previous run
    if db_path.exists():
        db_path.unlink()
    if log_path.exists():
        log_path.unlink()
        
    print(f"Running simulation...")
    print(f"DB: {db_path}")
    print(f"Log: {log_path}")
    
    # 1. Run Simulation with Logging
    bus = InMemoryBus()
    stepper = LoopStepper(
        state_db=db_path,
        seed=42,
    )
    
    ohlcv = make_ohlcv_df(n_bars=30)
    
    result = stepper.run_bus_mode(
        ohlcv, bus,
        max_steps=20,
        warmup=10,
        log_jsonl_path=log_path,
    )
    stepper.close()
    
    print(f"Simulation done. Published: {result['published']}")
    
    # 2. Collect Metrics from Log
    print("Collecting metrics from JSONL...")
    metrics = collect_metrics_from_jsonl(log_path)
    
    # 3. Save Metrics JSON (Deterministic)
    print(f"Saving metrics to {metrics_path}")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, sort_keys=True, indent=2)
        
    # Print metrics
    print("\n--- Run Metrics ---")
    print(json.dumps(metrics, sort_keys=True, indent=2))
    
    # Simple validation
    if metrics["num_fills"] > 0:
        print("\nSUCCESS: Fills recorded.")
    else:
        print("\nWARNING: No fills recorded.")


if __name__ == "__main__":
    main()
