"""
Generate sample JSONL for 3D.4 verification.

Run this script to produce: report/3D4_logs_sample.jsonl
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper


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
    log_path = Path("report/3D4_logs_sample.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    
    # Clear existing file
    if log_path.exists():
        log_path.unlink()
    
    bus = InMemoryBus()
    stepper = LoopStepper(seed=42)  # No SQLite for this sample
    
    ohlcv = make_ohlcv_df(n_bars=25)
    
    result = stepper.run_bus_mode(
        ohlcv, bus,
        max_steps=10,
        warmup=10,
        log_jsonl_path=log_path,
    )
    
    print(f"Published: {result['published']}")
    print(f"Drain iterations: {result['drain_iterations']}")
    print(f"Log file: {log_path}")
    
    # Show sample
    if log_path.exists():
        print("\n--- Sample lines ---")
        with open(log_path) as f:
            for i, line in enumerate(f):
                print(line.strip())
                if i >= 5:
                    print("...")
                    break


if __name__ == "__main__":
    main()
