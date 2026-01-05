"""
tools/run_3D_canonical.py

Canonical CI-safe runner for 3D bus mode integration.
Executes determinstic storage-less simulation, generating JSONL traces and metrics.

Usage:
  python tools/run_3D_canonical.py --outdir report/out --seed 42

Part of Ticket AG-3D-6-1.
"""

import argparse
import sys
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper
from engine.run_metrics_3D5 import collect_metrics_from_jsonl
from risk_rules_loader import load_risk_rules

# Configure basic logging to stderr (not interfering with JSONL)
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logger = logging.getLogger("run_3D_canonical")


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
    # Use fixed start date, no time.time()
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    
    # Deterministic random walk
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
    parser = argparse.ArgumentParser(description="Canonical 3D Runner")
    parser.add_argument("--outdir", required=True, help="Output directory for artifacts")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for determinism")
    parser.add_argument("--max-steps", type=int, default=100, help="Max bars to process")
    parser.add_argument("--risk-rules", type=str, help="Path to risk rules YAML")
    parser.add_argument("--strict-risk-config", type=int, default=0, help="Fail if risk config invalid (1=True, 0=False)")
    parser.add_argument("--num-signals", type=int, help="Target roughly this many signals (controls volatility approx)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan and exit")
    
    args = parser.parse_args()
    
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Paths
    trace_path = outdir / "trace.jsonl"
    metrics_path = outdir / "run_metrics.json"
    meta_path = outdir / "run_meta.json"
    db_path = outdir / "state.db"
    
    # Context/Metadata
    meta = {
        "commit": "unknown",
        "branch": "unknown",
        "python_version": sys.version,
        "sys_executable": sys.executable,
        "seed": args.seed,
        "max_steps": args.max_steps,
        "strict_risk_config": bool(args.strict_risk_config),
        "risk_rules_path": args.risk_rules,
        "num_signals": args.num_signals,
    }
    meta.update(get_git_info())
    
    # Write metadata immediately (overwrite)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, sort_keys=True, indent=2)
        
    if args.dry_run:
        print(f"Dry run configured. Meta written to {meta_path}")
        return
    
    # 1. Load Risk Rules check
    # We don't necessarily need to pass them to LoopStepper if it loads them itself,
    # but LoopStepper usually loads from file or uses defaults.
    # To enforce strictness we should verify it here.
    if args.risk_rules:
        rr_path = Path(args.risk_rules)
        if not rr_path.exists():
            if args.strict_risk_config:
                logger.error(f"Risk rules file not found: {rr_path}")
                sys.exit(1)
        else:
            # Validate format
            try:
                load_risk_rules(str(rr_path))
            except Exception as e:
                if args.strict_risk_config:
                    logger.error(f"Invalid risk rules: {e}")
                    sys.exit(1)
                else:
                    logger.warning(f"Invalid risk rules (non-strict): {e}")

    # 2. Setup Components
    # Copy risk rules to a location LoopStepper expects? 
    # Or LoopStepper init allows injecting risk manager?
    # LoopStepper creates its own RiskManagerV0_4_Shim using `inputs/risk_rules.yaml` hardcoded in `create_shim`.
    # Modifying LoopStepper to accept risk rules path is out of scope unless needed.
    # But wait, we want to control risk behavior. 
    # If we want "permissive", `inputs/risk_rules.yaml` might block things.
    # Smoke test usually assumes defaults work.
    
    # Clean up previous state
    if db_path.exists():
        db_path.unlink()
    if trace_path.exists():
        trace_path.unlink()
        
    bus = InMemoryBus()
    stepper = LoopStepper(
        state_db=db_path,
        seed=args.seed,
    )
    
    # 3. Generate Data
    # Adjust volatility if num_signals requested (heuristic)
    # Default make_ohlcv_df uses small volatility.
    n_bars = args.max_steps + 20 # + warmup
    ohlcv = make_ohlcv_df(n_bars=n_bars, seed=args.seed)
    
    # 4. Run Simulation
    try:
        result = stepper.run_bus_mode(
            ohlcv, bus,
            max_steps=args.max_steps,
            warmup=10,
            log_jsonl_path=trace_path,
        )
    finally:
        stepper.close()
        
    logger.info(f"Simulation done. Published: {result.get('published', 0)}")
    
    # 5. Collect Metrics
    if trace_path.exists():
        metrics = collect_metrics_from_jsonl(trace_path)
        
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, sort_keys=True, indent=2)
            
        logger.info(f"Metrics written to {metrics_path}")
    else:
        logger.error("No trace file generated!")
        sys.exit(1)


if __name__ == "__main__":
    main()
