"""
tools/run_live_3E.py

Unified runner for Phase 3E live/simulated execution.
Orchestrates LoopStepper, TimeProvider, and ExchangeAdapter.

Features:
- Deterministic simulation by default (--clock simulated --exchange paper --seed 42)
- Real-time support (--clock real)
- Stub network simulation (--exchange stub)
- Standard artifacts (events.ndjson, run_meta.json, results.csv)

Usage:
  python tools/run_live_3E.py --outdir report/out_3E_smoke --clock simulated --exchange paper
"""

import argparse
import sys
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper
from engine.run_metrics_3D5 import collect_metrics_from_jsonl
from engine.time_provider import SimulatedTimeProvider, RealTimeProvider
from engine.exchange_adapter import PaperExchangeAdapter, StubNetworkExchangeAdapter, SimulatedRealtimeAdapter
from engine.runtime_config import RuntimeConfig
from engine.checkpoint import Checkpoint
from engine.idempotency import FileIdempotencyStore
from risk_rules_loader import load_risk_rules

# Configure basic logging
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger("run_live_3E")


def get_git_info() -> Dict[str, str]:
    """Get basic git info safely."""
    info = {"commit": "unknown", "branch": "unknown"}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        info["commit"] = commit
        info["branch"] = branch
    except Exception:
        pass
    return info


def make_ohlcv_df(n_bars: int = 50, seed: int = 42) -> pd.DataFrame:
    """Create deterministic OHLCV DataFrame."""
    np.random.seed(seed)
    # Use fixed start date for determinism, LoopStepper uses TimeProvider for logical time
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    
    initial_price = 1000.0
    returns = np.random.randn(n_bars) * 0.01
    closes = initial_price * np.cumprod(1 + returns)
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": closes * (1 - np.random.rand(n_bars) * 0.005),
        "high": closes * (1 + np.random.rand(n_bars) * 0.005),
        "low": closes * (1 - np.random.rand(n_bars) * 0.005),
        "close": closes,
        "volume": np.random.randint(100, 1000, n_bars),
    })
    return df


def main():
    parser = argparse.ArgumentParser(description="Unified Live Runner 3E")
    
    # Standard args
    parser.add_argument("--outdir", default="report/out_3E_smoke", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--max-steps", type=int, default=50, help="Max bars to process")
    
    # 3E Features
    parser.add_argument("--clock", choices=["simulated", "real"], default="simulated", help="Time provider mode")
    parser.add_argument("--exchange", choices=["paper", "stub", "realish"], default="paper", help="Exchange adapter mode")
    parser.add_argument("--latency-steps", type=int, default=1, help="Latency steps for stub exchange")
    
    # 3F.4: Crash recovery
    parser.add_argument("--run-dir", type=str, help="Run directory for checkpoint/idempotency (creates new run)")
    parser.add_argument("--resume", type=str, help="Resume from existing run directory (mutually exclusive with --run-dir)")
    
    args = parser.parse_args()
    
    # Validate mutually exclusive args
    if args.run_dir and args.resume:
        parser.error("--run-dir and --resume are mutually exclusive")
    
    # Validate runtime config for non-paper modes (fail-fast)
    cfg = RuntimeConfig.from_env()
    cfg.validate_for(args.clock, args.exchange)
    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Paths
    trace_path = outdir / "events.ndjson" # Standardizing on .ndjson per request (or .jsonl logic)
    # Note: LoopStepper typically logs to .jsonl or .ndjson. Using .ndjson for file extension as requested.
    metrics_path = outdir / "run_metrics.json"
    meta_path = outdir / "run_meta.json"
    results_csv_path = outdir / "results.csv"
    db_path = outdir / "state.db"
    
    # 1. Setup TimeProvider
    if args.clock == "real":
        time_provider = RealTimeProvider()
        # For real clock, we shouldn't force seed determinism on time, but we use seed for data gen
    else:
        time_provider = SimulatedTimeProvider(seed=args.seed)
        
    # 2. Setup ExchangeAdapter
    if args.exchange == "realish":
        exchange_adapter = SimulatedRealtimeAdapter()
    elif args.exchange == "stub":
        exchange_adapter = StubNetworkExchangeAdapter(latency_steps=args.latency_steps)
    else:
        exchange_adapter = PaperExchangeAdapter()
        
    # Write metadata
    meta = {
        "clock": args.clock,
        "exchange": args.exchange,
        "seed": args.seed,
        "latency_steps": args.latency_steps if args.exchange == "stub" else 0,
        "max_steps": args.max_steps,
        "timestamp_start": str(pd.Timestamp.now(tz="UTC")),
    }
    meta.update(get_git_info())
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, sort_keys=True, indent=2)

    # Clean up previous state
    if db_path.exists():
        db_path.unlink()
    if trace_path.exists():
        trace_path.unlink()
    
    # 3F.4: Setup run directory and crash recovery
    run_dir: Optional[Path] = None
    checkpoint: Optional[Checkpoint] = None
    idem_store: Optional[FileIdempotencyStore] = None
    start_idx = 0
    
    if args.resume:
        run_dir = Path(args.resume)
        checkpoint_path = run_dir / "checkpoint.json"
        if not checkpoint_path.exists():
            print(f"ERROR: No checkpoint found at {checkpoint_path}")
            sys.exit(1)
        checkpoint = Checkpoint.load(checkpoint_path)
        start_idx = checkpoint.last_processed_idx + 1
        print(f"Resuming from run_id={checkpoint.run_id}, start_idx={start_idx}")
        idem_store = FileIdempotencyStore(run_dir / "idempotency_keys.jsonl")
    elif args.run_dir:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        run_id = f"run_{args.seed}_{args.max_steps}"
        checkpoint = Checkpoint.create_new(run_id)
        checkpoint.save_atomic(run_dir / "checkpoint.json")
        idem_store = FileIdempotencyStore(run_dir / "idempotency_keys.jsonl")
        print(f"Created run directory: {run_dir}")
        
    # 3. Initialize LoopStepper
    bus = InMemoryBus()
    stepper = LoopStepper(
        state_db=db_path,
        seed=args.seed,
        time_provider=time_provider,
        # Risk rules defaults for now or could expose arg
    )
    
    # Generate Data
    ohlcv = make_ohlcv_df(n_bars=args.max_steps + 10, seed=args.seed)
    
    print(f"Starting run_live_3E with clock={args.clock}, exchange={args.exchange}...")
    
    try:
        result = stepper.run_bus_mode(
            ohlcv, 
            bus,
            max_steps=args.max_steps,
            warmup=5,
            log_jsonl_path=trace_path,
            exchange_adapter=exchange_adapter,
            idempotency_store=idem_store,
        )
    finally:
        stepper.close()
        # Close idempotency store if used
        if idem_store:
            idem_store.close()
        
    print(f"Simulation done. Published: {result.get('published', 0)}")
    
    # 4. Collect Metrics
    if trace_path.exists():
        metrics = collect_metrics_from_jsonl(trace_path)
        
        # Write metrics json
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, sort_keys=True, indent=2)
            
        # Write results.csv (Summary of run)
        # Standard format usually includes metrics flattened
        flat_results = {
            "run_id": meta.get("commit", "unknown")[:7],
            "clock": args.clock,
            "exchange": args.exchange,
            "total_steps": metrics.get("steps_processed", 0),
            "fills": metrics.get("fills_count", 0),
            "pnl": metrics.get("pnl_realized", 0.0), # Assuming metrics has specific fields or we dump all
        }
        # Dump flattened metrics to CSV as 'results.csv'
        # The collect_metrics_from_jsonl returns a dict. We'll flatten it.
        
        # Also, user requested "results.csv headers esperados (los que ya use el repo)".
        # Existing runner (calibration) outputs a row per run.
        # This is a single run runner, so one row.
        
        df_res = pd.DataFrame([metrics]) # Use all metrics columns
        df_res.to_csv(results_csv_path, index=False)
            
        print(f"Artifacts generated in {outdir}")
    else:
        logger.error("No trace file generated!")
        sys.exit(1)

if __name__ == "__main__":
    main()
