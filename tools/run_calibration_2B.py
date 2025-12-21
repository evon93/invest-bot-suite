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

LOG_FILE = REPORT_DIR / "calibration_run_log_2B.txt"
CSV_FILE = REPORT_DIR / "calibration_results_2B.csv"


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


def log(msg: str, logfile: Path = LOG_FILE):
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
def run_calibration(
    mode: str = "quick",
    max_combinations: Optional[int] = None,
    seed: int = 42,
):
    """
    Ejecuta la calibración según el grid definido en el YAML.
    """
    # Cargar configs
    config = load_yaml(CONFIG_PATH)
    base_rules = load_yaml(RULES_PATH)

    grid = config.get("grid", {})
    yaml_seed = config.get("repro", {}).get("seed", 42)
    yaml_max_combos = config.get("execution", {}).get("max_combinations")

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

    # Asegurar directorio report
    REPORT_DIR.mkdir(exist_ok=True)

    # Limpiar log anterior
    LOG_FILE.write_text(f"Calibration run started at {datetime.now().isoformat()}\n")

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
    ]
    # Añadir parámetros al header
    if combos:
        param_keys = sorted(combos[0].keys())
        csv_headers.extend(param_keys)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
        writer.writeheader()

    log(f"Mode: {mode}, Total grid: {total_combos}, Running: {len(combos)}, Seed: {effective_seed}")

    results = []

    for i, params in enumerate(combos, 1):
        combo_id = generate_combo_id(params)
        log(f"START combo_id={combo_id} ({i}/{len(combos)}) params={params}")

        start_time = time.time()
        row: Dict[str, Any] = {
            "combo_id": combo_id,
            "status": "ok",
            "error_type": "",
            "error_msg": "",
            "traceback_short": "",
            "duration_s": 0.0,
        }
        row.update(params)

        try:
            # Aplicar overlay
            rules = apply_overlay(base_rules, params)
            rules.setdefault("risk_manager", {})["mode"] = config.get("execution", {}).get("mode", "active")

            # Ejecutar backtest
            metrics = run_single_backtest(rules, effective_seed, config)
            row.update(metrics)

        except Exception as e:
            row["status"] = "error"
            row["error_type"] = type(e).__name__
            row["error_msg"] = str(e)
            tb = traceback.format_exc()
            row["traceback_short"] = tb[-1500:] if len(tb) > 1500 else tb

        row["duration_s"] = round(time.time() - start_time, 2)

        log(f"END combo_id={combo_id} status={row['status']} duration_s={row['duration_s']}")

        # Append to CSV
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
            writer.writerow(row)

        results.append(row)

    # Summary
    ok_count = sum(1 for r in results if r["status"] == "ok")
    error_count = len(results) - ok_count
    log(f"DONE: {ok_count} ok, {error_count} errors, total {len(results)}")

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
