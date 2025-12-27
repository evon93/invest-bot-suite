#!/usr/bin/env python3
"""
tools/run_robustness_2D.py — Robustness 2D Runner

Executes parameter robustness testing as defined in configs/robustness_2D.yaml.
Applies param perturbations to candidate config and runs backtests.

Usage:
    python tools/run_robustness_2D.py --mode quick
    python tools/run_robustness_2D.py --mode full --outdir report/robustness_2D_custom
    python tools/run_robustness_2D.py --mode quick --max-scenarios 5
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import subprocess
import sys
import time
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import numpy as np

# Añadir repo root al path para imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backtest_initial import SimpleBacktester, calculate_metrics, generate_synthetic_prices
from risk_manager_v0_5 import RiskManagerV05
from tools.validate_robustness_2D_config import validate_config

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
DEFAULT_CONFIG = REPO_ROOT / "configs" / "robustness_2D.yaml"
RULES_PATH = REPO_ROOT / "risk_rules.yaml"
BEST_PARAMS_PATH = REPO_ROOT / "configs" / "best_params_2C.json"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_git_head() -> str:
    """Get git HEAD hash or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except Exception:
        pass
    return "unknown"


def compute_hash(data: Any, length: int = 8) -> str:
    """Compute SHA256 hash of JSON-serialized data."""
    s = json.dumps(data, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()[:length]


def generate_scenario_id(mode: str, seed: int, param_config: Dict, data_config: Dict) -> str:
    """Generate deterministic scenario ID per spec."""
    param_hash = compute_hash(param_config)
    data_hash = compute_hash(data_config)
    return f"{mode}_{seed}_{param_hash}_{data_hash}"


def apply_flat_params(base: Dict[str, Any], flat_params: Dict[str, Any]) -> Dict[str, Any]:
    """Apply flat params (section.key format) to base dict."""
    result = deepcopy(base)
    for flat_key, value in flat_params.items():
        parts = flat_key.split(".")
        if len(parts) == 2:
            section, key = parts
            if section not in result:
                result[section] = {}
            result[section][key] = value
    return result


def generate_param_perturbations(sweep: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate all parameter perturbation combinations from sweep config."""
    param_defs = sweep.get("param_perturbations", {})
    
    if not param_defs:
        return [{}]  # No perturbations = single scenario with base params
    
    # Build dimension lists
    dimensions = []
    for param_name, config in param_defs.items():
        ptype = config.get("type", "range")
        
        if ptype == "range":
            min_val = config.get("min", 0)
            max_val = config.get("max", 1)
            step = config.get("step", 0.1)
            # Generate range values
            values = []
            v = min_val
            while v <= max_val + 1e-9:  # epsilon for float comparison
                values.append(round(v, 6))
                v += step
            dimensions.append((param_name, values))
        
        elif ptype == "list":
            values = config.get("values", [])
            dimensions.append((param_name, values))
    
    if not dimensions:
        return [{}]
    
    # Generate cartesian product
    keys = [d[0] for d in dimensions]
    value_lists = [d[1] for d in dimensions]
    
    combos = []
    for values in itertools.product(*value_lists):
        combo = dict(zip(keys, values))
        combos.append(combo)
    
    return combos


def generate_data_perturbations(sweep: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate data perturbation configs from sweep."""
    data_defs = sweep.get("data_perturbations", {})
    
    if not data_defs:
        return [{"window_shift": 0, "subsample_ratio": 1.0}]
    
    # Window shifts
    window_shifts = [0]
    ws_config = data_defs.get("window_shifts", {})
    if ws_config.get("type") == "range":
        min_v = ws_config.get("min", 0)
        max_v = ws_config.get("max", 0)
        step = ws_config.get("step", 1)
        window_shifts = list(range(min_v, max_v + 1, step))
    
    # Subsample ratios
    subsample_ratios = [1.0]
    sr_config = data_defs.get("subsample_ratios", {})
    if sr_config.get("type") == "list":
        subsample_ratios = sr_config.get("values", [1.0])
    
    # Combine
    combos = []
    for ws in window_shifts:
        for sr in subsample_ratios:
            combos.append({"window_shift": ws, "subsample_ratio": sr})
    
    return combos


def check_gates(metrics: Dict[str, Any], gates: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Check if metrics pass all gates. Returns (passed, list of failed gates)."""
    failures = []
    
    # max_drawdown_absolute (drawdown is negative, gate is negative threshold)
    dd = metrics.get("max_drawdown", 0)
    dd_gate = gates.get("max_drawdown_absolute", -1.0)
    if dd < dd_gate:  # e.g., -0.20 < -0.15 = fail
        failures.append(f"max_drawdown {dd:.4f} < {dd_gate}")
    
    # min_sharpe
    sharpe = metrics.get("sharpe_ratio", 0)
    min_sharpe = gates.get("min_sharpe", 0)
    if sharpe < min_sharpe:
        failures.append(f"sharpe {sharpe:.4f} < {min_sharpe}")
    
    # min_cagr
    cagr = metrics.get("cagr", 0)
    min_cagr = gates.get("min_cagr", 0)
    if cagr < min_cagr:
        failures.append(f"cagr {cagr:.4f} < {min_cagr}")
    
    # max_pct_time_hard_stop
    pct_hard = metrics.get("pct_time_hard_stop", 0)
    max_hard = gates.get("max_pct_time_hard_stop", 1.0)
    if pct_hard > max_hard:
        failures.append(f"pct_time_hard_stop {pct_hard:.4f} > {max_hard}")
    
    return (len(failures) == 0, failures)


def compute_score(metrics: Dict[str, Any], weights: Dict[str, Any]) -> float:
    """Compute composite score using weights from config."""
    score = 0.0
    score += weights.get("sharpe_ratio", 1.0) * metrics.get("sharpe_ratio", 0)
    score += weights.get("cagr", 0.5) * metrics.get("cagr", 0)
    score += weights.get("win_rate", 0.3) * metrics.get("win_rate", 0)
    score -= weights.get("max_drawdown_penalty", 1.5) * abs(metrics.get("max_drawdown", 0))
    score -= weights.get("hard_stop_penalty", 0.5) * metrics.get("pct_time_hard_stop", 0)
    return score


def run_single_backtest(
    rules: Dict[str, Any],
    seed: int,
    baseline_cfg: Dict[str, Any],
    data_perturbation: Dict[str, Any],
) -> Dict[str, Any]:
    """Run single backtest with given rules and return metrics."""
    np.random.seed(seed)
    
    start_date = baseline_cfg.get("dataset", {}).get("start_date", "2024-01-01")
    # Apply window shift
    # For simplicity, we just vary the seed slightly based on window_shift
    effective_seed = seed + data_perturbation.get("window_shift", 0)
    np.random.seed(effective_seed)
    
    periods = 252  # 1 year default
    initial_capital = 10000
    
    prices = generate_synthetic_prices(start_date=start_date, periods=periods)
    
    # Apply subsample
    subsample = data_perturbation.get("subsample_ratio", 1.0)
    if subsample < 1.0:
        n = int(len(prices) * subsample)
        if n > 10:
            prices = prices.iloc[:n]
    
    rm = RiskManagerV05(rules)
    bt = SimpleBacktester(prices, initial_capital=initial_capital)
    df = bt.run(risk_manager=rm)
    
    metrics = calculate_metrics(df)
    metrics["num_trades"] = len(bt.trades)
    
    # Closed trades metrics
    ct = bt.closed_trades
    closed_count = len(ct)
    wins = [t["realized_pnl"] for t in ct if t["realized_pnl"] > 0]
    
    metrics["closed_trades_count"] = closed_count
    metrics["win_rate"] = len(wins) / closed_count if closed_count > 0 else 0.0
    
    # Risk events
    risk_events = getattr(bt, "risk_events", [])
    if risk_events:
        total_ticks = len(risk_events)
        hard_stop_flags = []
        for evt in risk_events:
            rd = evt.get("risk_decision", {})
            reasons = rd.get("reasons", [])
            is_hard = "dd_hard" in reasons or rd.get("force_close_positions", False)
            hard_stop_flags.append(is_hard)
        
        ticks_hard = sum(hard_stop_flags)
        metrics["pct_time_hard_stop"] = ticks_hard / total_ticks if total_ticks > 0 else 0.0
    else:
        metrics["pct_time_hard_stop"] = 0.0
    
    # Calmar ratio
    if metrics.get("max_drawdown", 0) != 0:
        metrics["calmar_ratio"] = metrics.get("cagr", 0) / abs(metrics["max_drawdown"])
    else:
        metrics["calmar_ratio"] = 0.0
    
    return metrics


# -------------------------------------------------------------------
# Main Runner
# -------------------------------------------------------------------
def run_robustness(
    config_path: Path,
    mode: str = "quick",
    outdir_override: Optional[Path] = None,
    max_scenarios_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run robustness 2D testing.
    
    Returns dict with summary stats.
    """
    run_start = time.time()
    
    # Validate config first
    errors, warnings = validate_config(config_path)
    if errors:
        raise ValueError(f"Config validation failed: {errors}")
    
    # Load configs
    config = load_yaml(config_path)
    base_rules = load_yaml(RULES_PATH)
    best_params = load_json(BEST_PARAMS_PATH)
    
    # Apply best_params to get candidate rules (in memory only)
    candidate_rules = deepcopy(base_rules)
    if "params" in best_params:
        candidate_rules = apply_flat_params(
            candidate_rules,
            best_params.get("params_dotted", {})
        )
    
    # Resolve output dir
    if outdir_override:
        outdir = outdir_override
    else:
        outdir_str = config.get("output", {}).get("directory", "report/robustness_2D")
        outdir = REPO_ROOT / outdir_str
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Mode config
    mode_cfg = config.get("engine", {}).get("modes", {}).get(mode, {})
    max_scenarios = max_scenarios_override or mode_cfg.get("max_scenarios", 20)
    seed_count = mode_cfg.get("seed_count", 1)
    param_sample = mode_cfg.get("param_perturbations_sample", 1.0)
    data_sample = mode_cfg.get("data_perturbations_sample", 1.0)
    
    # Seeds
    repro = config.get("engine", {}).get("reproducibility", {})
    default_seed = repro.get("default_seed", 42)
    seed_list = repro.get("seed_list", [42])[:seed_count]
    
    # Generate scenarios
    sweep = config.get("sweep", {})
    param_perturbations = generate_param_perturbations(sweep)
    data_perturbations = generate_data_perturbations(sweep)
    
    # Sample if needed
    if param_sample < 1.0:
        n = max(1, int(len(param_perturbations) * param_sample))
        param_perturbations = param_perturbations[:n]
    
    if data_sample < 1.0:
        n = max(1, int(len(data_perturbations) * data_sample))
        data_perturbations = data_perturbations[:n]
    
    # Build scenario list
    scenarios = []
    for seed in seed_list:
        for pp in param_perturbations:
            for dp in data_perturbations:
                scenario = {
                    "seed": seed,
                    "param_perturbation": pp,
                    "data_perturbation": dp,
                    "scenario_id": generate_scenario_id(mode, seed, pp, dp),
                }
                scenarios.append(scenario)
                if len(scenarios) >= max_scenarios:
                    break
            if len(scenarios) >= max_scenarios:
                break
        if len(scenarios) >= max_scenarios:
            break
    
    # Gates and scoring config
    gates = config.get("risk_constraints", {}).get("gates", {})
    weights = config.get("scoring", {}).get("weights", {})
    
    # Output files
    results_file = outdir / "results.csv"
    summary_file = outdir / "summary.md"
    meta_file = outdir / "run_meta.json"
    errors_file = outdir / "errors.jsonl"
    
    # CSV headers
    csv_headers = [
        "scenario_id",
        "scenario_label",
        "mode",
        "seed",
        "params_json",
        "sharpe_ratio",
        "cagr",
        "max_drawdown",
        "calmar_ratio",
        "win_rate",
        "pct_time_hard_stop",
        "score",
        "gate_pass",
        "warnings",
        "duration_seconds",
        "error",
    ]
    
    with open(results_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
    
    # Clear errors file
    errors_file.write_text("")
    
    results = []
    passed_count = 0
    failed_count = 0
    error_count = 0
    
    print(f"Running {len(scenarios)} scenarios in mode '{mode}'...")
    
    for i, scenario in enumerate(scenarios, 1):
        start_time = time.time()
        scenario_id = scenario["scenario_id"]
        
        row = {
            "scenario_id": scenario_id,
            "scenario_label": f"{mode}_s{scenario['seed']}_{i}",
            "mode": mode,
            "seed": scenario["seed"],
            "params_json": json.dumps(scenario["param_perturbation"]),
            "error": "",
            "warnings": "",
        }
        
        try:
            # Apply param perturbation to candidate
            rules = apply_flat_params(candidate_rules, scenario["param_perturbation"])
            rules.setdefault("risk_manager", {})["mode"] = "active"
            
            # Run backtest
            metrics = run_single_backtest(
                rules,
                scenario["seed"],
                config.get("baseline", {}),
                scenario["data_perturbation"],
            )
            
            # Add metrics to row
            row["sharpe_ratio"] = metrics.get("sharpe_ratio", 0)
            row["cagr"] = metrics.get("cagr", 0)
            row["max_drawdown"] = metrics.get("max_drawdown", 0)
            row["calmar_ratio"] = metrics.get("calmar_ratio", 0)
            row["win_rate"] = metrics.get("win_rate", 0)
            row["pct_time_hard_stop"] = metrics.get("pct_time_hard_stop", 0)
            
            # Score
            row["score"] = compute_score(metrics, weights)
            
            # Gates
            passed, failures = check_gates(metrics, gates)
            row["gate_pass"] = passed
            row["warnings"] = "; ".join(failures) if failures else ""
            
            if passed:
                passed_count += 1
            else:
                failed_count += 1
        
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {str(e)}"
            row["gate_pass"] = False
            error_count += 1
            
            # Log to errors.jsonl
            error_entry = {
                "scenario_id": scenario_id,
                "error_type": type(e).__name__,
                "error_msg": str(e),
                "traceback": traceback.format_exc()[-500:],
                "timestamp": datetime.now().isoformat(),
            }
            with open(errors_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_entry) + "\n")
        
        row["duration_seconds"] = round(time.time() - start_time, 3)
        
        # Append to CSV
        with open(results_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers)
            writer.writerow(row)
        
        results.append(row)
        
        if i % 10 == 0 or i == len(scenarios):
            print(f"  Progress: {i}/{len(scenarios)}")
    
    run_duration = round(time.time() - run_start, 2)
    
    # Generate run_meta.json
    meta = {
        "start_time": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat(),
        "mode": mode,
        "git_head": get_git_head(),
        "python_version": sys.version.split()[0],
        "config_hash": compute_hash(config, 16),
        "scenarios_total": len(scenarios),
        "scenarios_passed": passed_count,
        "scenarios_failed": failed_count,
        "scenarios_error": error_count,
        "pass_rate": passed_count / len(scenarios) if scenarios else 0,
        "duration_seconds": run_duration,
        "default_seed": default_seed,
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    
    # Generate summary.md
    summary_lines = [
        "# Robustness 2D Run Summary",
        "",
        f"**Timestamp**: {datetime.now().isoformat()}",
        f"**Mode**: {mode}",
        f"**Git HEAD**: {get_git_head()}",
        f"**Duration**: {run_duration}s",
        "",
        "## Results",
        "",
        f"- Scenarios run: {len(scenarios)}",
        f"- Passed gates: {passed_count}",
        f"- Failed gates: {failed_count}",
        f"- Errors: {error_count}",
        f"- **Pass rate**: {meta['pass_rate']:.1%}",
        "",
        "## Top Scenarios by Score",
        "",
        "| Rank | Scenario ID | Score | Sharpe | CAGR | MaxDD | Pass |",
        "|------|-------------|-------|--------|------|-------|------|",
    ]
    
    # Sort by score
    sorted_results = sorted(
        [r for r in results if not r.get("error")],
        key=lambda x: x.get("score", 0),
        reverse=True,
    )
    
    for i, r in enumerate(sorted_results[:10], 1):
        summary_lines.append(
            f"| {i} | {r['scenario_id'][:20]} | {r.get('score', 0):.4f} | "
            f"{r.get('sharpe_ratio', 0):.4f} | {r.get('cagr', 0):.4f} | "
            f"{r.get('max_drawdown', 0):.4f} | {'✓' if r.get('gate_pass') else '✗'} |"
        )
    
    summary_lines.extend([
        "",
        "## Artifacts",
        "",
        "- `results.csv` — All scenario results",
        "- `run_meta.json` — Run metadata",
        "- `summary.md` — This file",
        "- `errors.jsonl` — Error log (if any)",
    ])
    
    summary_file.write_text("\n".join(summary_lines), encoding="utf-8")
    
    print(f"\nDone! {passed_count}/{len(scenarios)} passed ({meta['pass_rate']:.1%})")
    print(f"Artifacts: {outdir}")
    
    return meta


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run Robustness 2D testing")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/robustness_2D.yaml",
        help="Path to config YAML (default: configs/robustness_2D.yaml)",
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Run mode (default: quick)",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=None,
        help="Override output directory",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Max scenarios override (safety limit)",
    )
    
    args = parser.parse_args()
    
    config_path = REPO_ROOT / args.config
    outdir = Path(args.outdir) if args.outdir else None
    
    try:
        run_robustness(
            config_path=config_path,
            mode=args.mode,
            outdir_override=outdir,
            max_scenarios_override=args.max_scenarios,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
