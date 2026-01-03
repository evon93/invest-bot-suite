"""
run_realdata_smoke_2F.py — Minimal OHLCV smoke test runner

Loads real OHLCV data and computes buy-and-hold metrics for validation.
Designed for optional CI integration via INVESTBOT_REALDATA_PATH env var.

Usage:
    python tools/run_realdata_smoke_2F.py --path data.csv --outdir report/out
    
    # Or with env var:
    set INVESTBOT_REALDATA_PATH=data/btc_daily.csv
    python tools/run_realdata_smoke_2F.py --outdir report/out
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.load_ohlcv import load_ohlcv


def compute_buy_hold_metrics(df: pd.DataFrame) -> dict:
    """
    Compute simple buy-and-hold metrics from OHLCV data.
    
    Returns:
        Dict with: total_return, cagr, max_drawdown, sharpe
    """
    if len(df) < 2:
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
        }
    
    prices = df["close"].values
    
    # Total return
    total_return = (prices[-1] / prices[0]) - 1.0 if prices[0] > 0 else 0.0
    
    # CAGR (annualized)
    dates = df["date"]
    start_date = dates.iloc[0]
    end_date = dates.iloc[-1]
    years = (end_date - start_date).days / 365.25
    
    if years > 0 and prices[0] > 0:
        cagr = (prices[-1] / prices[0]) ** (1 / years) - 1.0
    else:
        cagr = 0.0
    
    # Max drawdown
    cummax = np.maximum.accumulate(prices)
    drawdowns = (prices - cummax) / np.where(cummax > 0, cummax, 1)
    max_drawdown = float(np.min(drawdowns))
    
    # Sharpe (daily returns annualized)
    if len(prices) > 1:
        daily_returns = np.diff(prices) / prices[:-1]
        daily_returns = daily_returns[np.isfinite(daily_returns)]
        if len(daily_returns) > 0 and np.std(daily_returns) > 0:
            sharpe = float(np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252))
        else:
            sharpe = 0.0
    else:
        sharpe = 0.0
    
    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "max_drawdown": float(max_drawdown),
        "sharpe": float(sharpe),
    }


def run_smoke(
    path: str | Path,
    outdir: str | Path,
    max_rows: int = 2000,
) -> dict:
    """
    Run minimal smoke test on OHLCV data.
    
    Args:
        path: Path to OHLCV file
        outdir: Output directory for results
        max_rows: Maximum rows to use (tail)
    
    Returns:
        Dict with results and metadata
    """
    path = Path(path)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    df = load_ohlcv(path)
    
    # Trim to max_rows (use tail for most recent data)
    if len(df) > max_rows:
        df = df.tail(max_rows).reset_index(drop=True)
    
    # Compute metrics
    metrics = compute_buy_hold_metrics(df)
    
    # Build results
    results = {
        "metrics": metrics,
        "n_rows": len(df),
        "start_date": str(df["date"].iloc[0]) if len(df) > 0 else None,
        "end_date": str(df["date"].iloc[-1]) if len(df) > 0 else None,
    }
    
    # Build run metadata
    run_meta = {
        "data_source": "realdata",
        "realdata_path": str(path.resolve()),
        "n_rows": len(df),
        "max_rows_limit": max_rows,
        "start_date": results["start_date"],
        "end_date": results["end_date"],
        "run_timestamp": datetime.now().isoformat(),
    }
    
    # Write outputs
    results_path = outdir / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    meta_path = outdir / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2)
    
    return {"results": results, "run_meta": run_meta}


def main():
    parser = argparse.ArgumentParser(
        description="Run minimal OHLCV smoke test"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=os.environ.get("INVESTBOT_REALDATA_PATH"),
        help="Path to OHLCV file (default: $INVESTBOT_REALDATA_PATH)",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        required=True,
        help="Output directory for results",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=2000,
        help="Maximum rows to use (default: 2000)",
    )
    
    args = parser.parse_args()
    
    if not args.path:
        print("ERROR: --path required or set INVESTBOT_REALDATA_PATH", file=sys.stderr)
        sys.exit(1)
    
    try:
        output = run_smoke(args.path, args.outdir, args.max_rows)
        print(f"Smoke test passed: {output['results']['n_rows']} rows")
        print(f"  total_return: {output['results']['metrics']['total_return']:.4f}")
        print(f"  max_drawdown: {output['results']['metrics']['max_drawdown']:.4f}")
        print(f"Results written to: {args.outdir}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
