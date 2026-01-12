#!/usr/bin/env python3
"""
tools/run_strategy_validation_3J.py

Offline validation harness for Strategy v0.8 (AG-3J-3-1).

Features:
- Deterministic execution (seed 42 by default)
- No external services required
- Generates reproducible artifacts in run_dir

Outputs:
- signals.ndjson: OrderIntent events from strategy
- metrics_summary.json: Basic metrics from signals
- run_meta.json: Execution metadata

Usage:
    python tools/run_strategy_validation_3J.py --outdir report/out_3J3_validation
    python tools/run_strategy_validation_3J.py --strategy v0_8 --seed 42 --outdir out/
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from strategy_engine.strategy_registry import get_strategy_fn, STRATEGY_VERSIONS


def generate_ohlcv_fixture(n_bars: int = 100, seed: int = 42) -> pd.DataFrame:
    """
    Generate deterministic OHLCV fixture data.
    
    Creates a price series with clear trends for crossover detection.
    """
    rng = np.random.default_rng(seed)
    
    # Base price with trend changes
    base = 100.0
    prices = [base]
    
    # Create patterns: flat -> up -> down -> up
    for i in range(1, n_bars):
        if i < 20:
            # Flat with noise
            change = rng.uniform(-0.5, 0.5)
        elif i < 40:
            # Uptrend
            change = rng.uniform(0.0, 1.5)
        elif i < 60:
            # Downtrend
            change = rng.uniform(-1.5, 0.0)
        elif i < 80:
            # Uptrend again
            change = rng.uniform(0.0, 1.5)
        else:
            # Consolidation
            change = rng.uniform(-0.3, 0.3)
        
        prices.append(prices[-1] + change)
    
    # Generate OHLCV
    timestamps = pd.date_range("2025-01-01", periods=n_bars, freq="h", tz="UTC")
    
    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": [p - rng.uniform(0, 0.5) for p in prices],
        "high": [p + rng.uniform(0.5, 1.0) for p in prices],
        "low": [p - rng.uniform(0.5, 1.0) for p in prices],
        "close": prices,
        "volume": [rng.uniform(1000, 5000) for _ in range(n_bars)],
    })
    
    return df


def write_ndjson(path: Path, events: List[Dict[str, Any]]) -> None:
    """Write events to NDJSON file."""
    with open(path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")


def calculate_metrics(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate basic metrics from signals."""
    if not signals:
        return {
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
        }
    
    buy_count = sum(1 for s in signals if s.get("side") == "BUY")
    sell_count = sum(1 for s in signals if s.get("side") == "SELL")
    
    return {
        "total_signals": len(signals),
        "buy_signals": buy_count,
        "sell_signals": sell_count,
        "first_signal_ts": signals[0].get("ts") if signals else None,
        "last_signal_ts": signals[-1].get("ts") if signals else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline Strategy Validation Harness (AG-3J-3-1)"
    )
    
    parser.add_argument(
        "--strategy",
        choices=STRATEGY_VERSIONS,
        default="v0_8",
        help="Strategy version to validate (default: v0_8)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for fixture generation (default: 42)"
    )
    parser.add_argument(
        "--n-bars",
        type=int,
        default=100,
        help="Number of OHLCV bars to generate (default: 100)"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional input CSV file (if not provided, generates fixture)"
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("report/out_3J3_validation"),
        help="Output directory for artifacts"
    )
    parser.add_argument(
        "--asof-ts",
        type=str,
        default=None,
        help="Optional asof timestamp (ISO format). Default: last timestamp of data"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="BTC-USD",
        help="Ticker symbol (default: BTC-USD)"
    )
    parser.add_argument(
        "--fast-period",
        type=int,
        default=5,
        help="Fast period for EMA (default: 5)"
    )
    parser.add_argument(
        "--slow-period",
        type=int,
        default=13,
        help="Slow period for EMA (default: 13)"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    args.outdir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load or generate OHLCV data
    if args.input and args.input.exists():
        print(f"Loading OHLCV from: {args.input}")
        df = pd.read_csv(args.input, parse_dates=["timestamp"])
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        print(f"Generating OHLCV fixture: {args.n_bars} bars, seed={args.seed}")
        df = generate_ohlcv_fixture(n_bars=args.n_bars, seed=args.seed)
    
    # 2. Determine asof_ts
    if args.asof_ts:
        asof_ts = pd.Timestamp(args.asof_ts)
        if asof_ts.tz is None:
            asof_ts = asof_ts.tz_localize("UTC")
    else:
        asof_ts = df["timestamp"].iloc[-1]
    
    print(f"Strategy: {args.strategy}")
    print(f"asof_ts: {asof_ts}")
    print(f"Ticker: {args.ticker}")
    print(f"Periods: fast={args.fast_period}, slow={args.slow_period}")
    
    # 3. Get strategy function
    strategy_fn = get_strategy_fn(args.strategy)
    params = {
        "fast_period": args.fast_period,
        "slow_period": args.slow_period,
    }
    
    # 4. Run strategy incrementally over data (like backtester would)
    warmup = args.slow_period
    all_signals = []
    
    for i in range(warmup, len(df)):
        slice_df = df.iloc[:i+1]
        bar_ts = slice_df["timestamp"].iloc[-1]
        
        # Only process up to asof_ts
        if bar_ts > asof_ts:
            break
        
        intents = strategy_fn(slice_df, params, args.ticker, bar_ts)
        
        for intent in intents:
            signal_dict = {
                "event_type": "OrderIntent",
                "symbol": intent.symbol,
                "side": intent.side,
                "qty": intent.qty,
                "order_type": intent.order_type,
                "ts": intent.ts,
                "bar_idx": i,
            }
            all_signals.append(signal_dict)
    
    print(f"Generated {len(all_signals)} signals")
    
    # 5. Write artifacts
    signals_path = args.outdir / "signals.ndjson"
    write_ndjson(signals_path, all_signals)
    print(f"  -> {signals_path}")
    
    metrics = calculate_metrics(all_signals)
    metrics_path = args.outdir / "metrics_summary.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
    print(f"  -> {metrics_path}")
    
    # 6. Write run_meta
    run_meta = {
        "strategy": args.strategy,
        "seed": args.seed,
        "n_bars": len(df),
        "fast_period": args.fast_period,
        "slow_period": args.slow_period,
        "ticker": args.ticker,
        "asof_ts": asof_ts.isoformat(),
        "input_file": str(args.input) if args.input else None,
        "total_signals": len(all_signals),
        "warmup": warmup,
    }
    meta_path = args.outdir / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2, sort_keys=True)
    print(f"  -> {meta_path}")
    
    print("\nValidation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
