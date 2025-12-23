#!/usr/bin/env python3
"""
run_calibration_2B.py — Runner de calibración 2B

Ejecuta grid de combinaciones de parámetros de riesgo contra backtest_initial.py.
Maneja errores sin abortar, registra status=ok/error para cada combo.

Uso:
    python tools/run_calibration_2B.py --mode quick --max-combinations 3
    python tools/run_calibration_2B.py --mode full
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import sys
import time
import traceback
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import numpy as np
import subprocess

# Añadir repo root al path para imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backtest_initial import SimpleBacktester, calculate_metrics, generate_synthetic_prices
from risk_manager_v0_5 import RiskManagerV05

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
CONFIG_PATH = REPO_ROOT / "configs" / "risk_calibration_2B.yaml"
RULES_PATH = REPO_ROOT / "risk_rules.yaml"
REPORT_DIR = REPO_ROOT / "report"
DEFAULT_OUTPUT_DIR = "report/calibration_2B"


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def generate_combo_id(params: Dict[str, Any]) -> str:
    """Genera un ID estable para la combinación de parámetros."""
    s = json.dumps(params, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()[:12]


def flatten_grid(grid: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convierte el grid anidado en lista de combinaciones planas.
    Ej: grid.stop_loss.atr_multiplier -> stop_loss.atr_multiplier
    """
    flat_keys = []
    flat_values = []

    for section, params in grid.items():
        if isinstance(params, dict):
            for key, values in params.items():
                if isinstance(values, list):
                    flat_keys.append(f"{section}.{key}")
                    flat_values.append(values)

    combos = []
    for combo in itertools.product(*flat_values):
        d = {}
        for k, v in zip(flat_keys, combo):
            d[k] = v
        combos.append(d)

    return combos


def apply_overlay(base: Dict[str, Any], flat_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplica parámetros planos (section.key) sobre el dict base.
    """
    result = deepcopy(base)
    for flat_key, value in flat_params.items():
        parts = flat_key.split(".")
        if len(parts) == 2:
            section, key = parts
            if section not in result:
                result[section] = {}
            result[section][key] = value
    return result


def log(msg: str, logfile: Path):
    """Escribe mensaje a log y stdout."""
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    print(line)
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_single_backtest(
    rules: Dict[str, Any],
    seed: int,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ejecuta un backtest con las reglas dadas.
    Retorna dict con métricas.
    """
    np.random.seed(seed)
    
    baseline = config.get("baseline", {})
    start_date = baseline.get("start_date", "2024-01-01")
    periods = baseline.get("periods", 252)
    initial_capital = baseline.get("initial_capital", 10000)
    
    prices = generate_synthetic_prices(start_date=start_date, periods=periods)
    rm = RiskManagerV05(rules)
    
    bt = SimpleBacktester(prices, initial_capital=initial_capital)
    df = bt.run(risk_manager=rm)
    
    metrics = calculate_metrics(df)
    metrics["num_trades"] = len(bt.trades)
    
    # Calmar ratio
    if metrics.get("max_drawdown", 0) != 0:
        metrics["calmar_ratio"] = metrics.get("cagr", 0) / abs(metrics["max_drawdown"])
    else:
        metrics["calmar_ratio"] = 0.0
    
    return metrics


# -------------------------------------------------------------------
# Main Runner
# -------------------------------------------------------------------
def get_git_head() -> str:
    """Obtiene el hash del HEAD de git, o 'unknown' si falla."""
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


def compute_config_hash(config: Dict[str, Any]) -> str:
    """Hash MD5 del config para trazabilidad."""
    s = json.dumps(config, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()[:16]


def compute_score(row: Dict[str, Any], formula: str) -> float:
    """Calcula score según fórmula. Fallback a sharpe_ratio si hay error."""
    try:
        # Crear contexto con las métricas
        ctx = {
            "sharpe_ratio": float(row.get("sharpe_ratio", 0) or 0),
            "cagr": float(row.get("cagr", 0) or 0),
            "max_drawdown": float(row.get("max_drawdown", 0) or 0),
            "calmar_ratio": float(row.get("calmar_ratio", 0) or 0),
            "abs": abs,
        }
        return float(eval(formula, {"__builtins__": {}}, ctx))
    except Exception:
        return float(row.get("sharpe_ratio", 0) or 0)


def run_calibration(
    mode: str = "quick",
    max_combinations: Optional[int] = None,
    seed: int = 42,
):
    """
    Ejecuta la calibración según el grid definido en el YAML.
    Escribe todos los artefactos en output_dir (definido en YAML).
    """
    run_start = time.time()
    
    # Cargar configs
    config = load_yaml(CONFIG_PATH)
    base_rules = load_yaml(RULES_PATH)

    # Resolver output_dir desde YAML con fallback
    output_dir_rel = config.get("output", {}).get("dir", DEFAULT_OUTPUT_DIR)
    output_dir = REPO_ROOT / output_dir_rel
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Paths de artefactos dentro de output_dir
    log_file = output_dir / "run_log.txt"
    csv_file = output_dir / "results.csv"
    summary_file = output_dir / "summary.md"
    topk_file = output_dir / "topk.json"
    meta_file = output_dir / "run_meta.json"

    grid = config.get("grid", {})
    yaml_seed = config.get("repro", {}).get("seed", 42)
    yaml_max_combos = config.get("execution", {}).get("max_combinations")
    score_formula = config.get("score", {}).get("formula", "sharpe_ratio")
    top_k = config.get("search", {}).get("top_k", 20)

    # Usar seed del YAML si no se pasó explícitamente diferente
    effective_seed = seed if seed != 42 else yaml_seed

    # Generar combinaciones
    all_combos = flatten_grid(grid)
    total_combos = len(all_combos)

    # Limitar según modo
    if mode == "quick":
        limit = max_combinations or yaml_max_combos or 12
        combos = all_combos[:limit]
    else:
        combos = all_combos

    # Inicializar log
    log_file.write_text(f"Calibration run started at {datetime.now().isoformat()}\n")

    # Inicializar CSV
    csv_headers = [
        "combo_id",
        "status",
        "error_type",
        "error_msg",
        "traceback_short",
        "duration_s",
        "cagr",
        "total_return",
        "max_drawdown",
        "sharpe_ratio",
        "volatility",
        "num_trades",
        "calmar_ratio",
        "score",
    ]
    # Añadir parámetros al header
    if combos:
        param_keys = sorted(combos[0].keys())
        csv_headers.extend(param_keys)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
        writer.writeheader()

    log(f"Mode: {mode}, Total grid: {total_combos}, Running: {len(combos)}, Seed: {effective_seed}", log_file)
    log(f"Output dir: {output_dir}", log_file)

    results = []

    for i, params in enumerate(combos, 1):
        combo_id = generate_combo_id(params)
        log(f"START combo_id={combo_id} ({i}/{len(combos)}) params={params}", log_file)

        start_time = time.time()
        row: Dict[str, Any] = {
            "combo_id": combo_id,
            "status": "ok",
            "error_type": "",
            "error_msg": "",
            "traceback_short": "",
            "duration_s": 0.0,
            "score": 0.0,
        }
        row.update(params)

        try:
            # Aplicar overlay
            rules = apply_overlay(base_rules, params)
            rules.setdefault("risk_manager", {})["mode"] = config.get("execution", {}).get("mode", "active")

            # Ejecutar backtest
            metrics = run_single_backtest(rules, effective_seed, config)
            row.update(metrics)
            row["score"] = compute_score(row, score_formula)

        except Exception as e:
            row["status"] = "error"
            row["error_type"] = type(e).__name__
            row["error_msg"] = str(e)
            tb = traceback.format_exc()
            row["traceback_short"] = tb[-1500:] if len(tb) > 1500 else tb

        row["duration_s"] = round(time.time() - start_time, 2)

        log(f"END combo_id={combo_id} status={row['status']} duration_s={row['duration_s']}", log_file)

        # Append to CSV
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
            writer.writerow(row)

        results.append(row)

    # Stats
    ok_count = sum(1 for r in results if r["status"] == "ok")
    error_count = len(results) - ok_count
    run_duration = round(time.time() - run_start, 2)
    
    log(f"DONE: {ok_count} ok, {error_count} errors, total {len(results)}, duration {run_duration}s", log_file)

    # ----- Generate topk.json -----
    ok_results = [r for r in results if r["status"] == "ok"]
    sorted_results = sorted(ok_results, key=lambda x: x.get("score", 0), reverse=True)
    topk_candidates = sorted_results[:top_k]
    
    topk_data = {
        "score_formula": score_formula,
        "top_k": top_k,
        "candidates": [
            {
                "rank": i + 1,
                "combo_id": c["combo_id"],
                "score": c.get("score", 0),
                "sharpe_ratio": c.get("sharpe_ratio", 0),
                "cagr": c.get("cagr", 0),
                "max_drawdown": c.get("max_drawdown", 0),
                "calmar_ratio": c.get("calmar_ratio", 0),
                "params": {k: c[k] for k in c if "." in k},
            }
            for i, c in enumerate(topk_candidates)
        ],
    }
    with open(topk_file, "w", encoding="utf-8") as f:
        json.dump(topk_data, f, indent=2)

    # ----- Generate run_meta.json -----
    meta_data = {
        "config_hash": compute_config_hash(config),
        "git_head": get_git_head(),
        "seed": effective_seed,
        "mode": mode,
        "total_grid": total_combos,
        "running": len(combos),
        "ok": ok_count,
        "errors": error_count,
        "duration_s": run_duration,
        "timestamp": datetime.now().isoformat(),
        "output_dir": str(output_dir_rel),
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)

    # ----- Generate summary.md -----
    summary_lines = [
        "# Calibration 2B Run Summary",
        "",
        f"**Timestamp**: {datetime.now().isoformat()}",
        f"**Mode**: {mode}",
        f"**Seed**: {effective_seed}",
        f"**Git HEAD**: {get_git_head()}",
        "",
        "## Results",
        "",
        f"- Total grid size: {total_combos}",
        f"- Combinations run: {len(combos)}",
        f"- OK: {ok_count}",
        f"- Errors: {error_count}",
        f"- Duration: {run_duration}s",
        "",
        "## Score Formula",
        "",
        f"```",
        f"{score_formula}",
        f"```",
        "",
        "## Top-K Candidates",
        "",
        "| Rank | Combo ID | Score | Sharpe | CAGR | MaxDD |",
        "|------|----------|-------|--------|------|-------|",
    ]
    for c in topk_candidates[:10]:  # Show top 10 in summary
        summary_lines.append(
            f"| {topk_candidates.index(c) + 1} | {c['combo_id']} | {c.get('score', 0):.4f} | "
            f"{c.get('sharpe_ratio', 0):.4f} | {c.get('cagr', 0):.4f} | {c.get('max_drawdown', 0):.4f} |"
        )
    
    summary_lines.extend([
        "",
        "## Artifacts",
        "",
        f"- `results.csv` — Full results table",
        f"- `run_log.txt` — Execution log",
        f"- `topk.json` — Top-{top_k} candidates with scores",
        f"- `run_meta.json` — Run metadata (hash, git, seed, timing)",
        f"- `summary.md` — This file",
        "",
        "## Reproducibility",
        "",
        f"```bash",
        f"python tools/run_calibration_2B.py --mode {mode} --max-combinations {len(combos)} --seed {effective_seed}",
        f"```",
    ])
    
    summary_file.write_text("\n".join(summary_lines), encoding="utf-8")

    log(f"Artifacts written to: {output_dir}", log_file)
    
    return results


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run 2B risk calibration grid")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="quick: limited combos, full: all combos (default: quick)",
    )
    parser.add_argument(
        "--max-combinations",
        type=int,
        default=None,
        help="Max combinations for quick mode (overrides YAML)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    run_calibration(
        mode=args.mode,
        max_combinations=args.max_combinations,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
