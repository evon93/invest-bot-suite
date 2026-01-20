#!/usr/bin/env python3
"""
run_calibration_2B.py — Runner de calibración 2B

Ejecuta grid de combinaciones de parámetros de riesgo contra backtest_initial.py.
Maneja errores sin abortar, registra status=ok/error para cada combo.

Uso:
    python tools/run_calibration_2B.py --mode quick --max-combinations 3
    python tools/run_calibration_2B.py --mode full
    python tools/run_calibration_2B.py --mode full --strict-gate
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
from typing import Any, Dict, List, Optional, Tuple

import yaml
import numpy as np
import pandas as pd
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
# Sensitivity Scenario: deterministic prices with drawdowns
# -------------------------------------------------------------------
def generate_sensitivity_prices(
    start_date: str = "2024-01-01",
    periods: int = 252,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generates deterministic price series with vol clustering and drawdowns.
    
    This scenario is designed to make risk parameters discriminate:
    - Month 1-2: uptrend with low vol
    - Month 3: sharp drawdown (15% crash)
    - Month 4-6: recovery with high vol
    - Month 7-9: sideways with medium vol
    - Month 10-12: gradual uptrend
    
    The drawdown phase should trigger DD soft/hard guardrails differently
    depending on thresholds. The vol clustering should make ATR stops
    vary in effectiveness.
    """
    np.random.seed(seed)
    dates = pd.date_range(start_date, periods=periods, freq="D")
    
    assets = {
        "ETF": {"base": 100},
        "CRYPTO_BTC": {"base": 40000},
        "CRYPTO_ETH": {"base": 3000},
        "BONDS": {"base": 95},
    }
    
    prices = pd.DataFrame(index=dates)
    
    for asset, params in assets.items():
        base = params["base"]
        price_series = []
        p = base
        
        for i, date in enumerate(dates):
            day_of_year = i
            
            # Determine regime based on day of year
            if day_of_year < 42:  # ~Month 1-2: calm uptrend
                mu = 0.001
                sigma = 0.005
            elif day_of_year < 63:  # ~Month 3: crash
                mu = -0.008
                sigma = 0.025
            elif day_of_year < 126:  # ~Month 4-6: volatile recovery
                mu = 0.0015
                sigma = 0.02
            elif day_of_year < 189:  # ~Month 7-9: sideways
                mu = 0.0001
                sigma = 0.01
            else:  # ~Month 10-12: calm uptrend
                mu = 0.0008
                sigma = 0.006
            
            # Asset-specific vol multiplier
            if "CRYPTO" in asset:
                sigma *= 2.5
            elif asset == "BONDS":
                sigma *= 0.3
                mu *= 0.5
            
            ret = np.random.normal(mu, sigma)
            p = p * (1 + ret)
            p = max(p, base * 0.3)  # Floor to prevent extinction
            price_series.append(p)
        
        prices[asset] = price_series
    
    return prices


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def parse_seeds(seeds_str: str) -> List[int]:
    """
    Parse comma-separated seed string into list of unique ints.
    
    Examples:
        "42" -> [42]
        "42,123,456" -> [42, 123, 456]
    """
    if not seeds_str or not seeds_str.strip():
        raise ValueError("--seeds cannot be empty")
    
    parts = [s.strip() for s in seeds_str.split(",")]
    seeds = []
    for p in parts:
        if not p:  # Skip empty parts (e.g. trailing comma)
            continue
        try:
            seed = int(p)
        except ValueError:
            raise ValueError(f"Invalid seed value: '{p}'")

        if seed < 0:
            raise ValueError(f"Seed must be non-negative: {seed}")
        seeds.append(seed)
    
    # Check for duplicates
    if len(seeds) != len(set(seeds)):
        raise ValueError(f"Duplicate seeds detected: {seeds}")
    
    return seeds


def compute_ranking_stability(
    results_by_seed: List[Dict[str, Any]],
    seeds: List[int],
    score_col: str = "score",
) -> Dict[str, Any]:
    """
    Compute ranking stability metrics across seeds using Spearman correlation.
    
    Returns:
        Dict with spearman_mean, spearman_min, topk_overlap (K=10)
    """
    if len(seeds) < 2:
        return {"spearman_mean": 1.0, "spearman_min": 1.0, "topk_overlap": 1.0}
    
    # Build DataFrame
    df = pd.DataFrame(results_by_seed)
    if df.empty or score_col not in df.columns:
        return {"spearman_mean": 0.0, "spearman_min": 0.0, "topk_overlap": 0.0}
    
    # Pivot: rows=combo_id, cols=seed, values=score
    pivot = df.pivot_table(index="combo_id", columns="seed", values=score_col, aggfunc="first")
    
    # Compute pairwise Spearman
    correlations = []
    seed_cols = [s for s in seeds if s in pivot.columns]
    for i, s1 in enumerate(seed_cols):
        for s2 in seed_cols[i+1:]:
            r1 = pivot[s1].rank(ascending=False)
            r2 = pivot[s2].rank(ascending=False)
            valid = r1.notna() & r2.notna()
            if valid.sum() < 2:
                continue
            # Use pearson corr on RANKS (equivalent to Spearman) to avoid scipy dependency
            # Guard: if either series has std=0, all values are identical -> perfect correlation
            r1_valid = r1[valid]
            r2_valid = r2[valid]
            if r1_valid.std() == 0 or r2_valid.std() == 0:
                corr = 1.0  # Degenerate case: identical rankings
            else:
                corr = r1_valid.corr(r2_valid, method='pearson')
            if not np.isnan(corr):
                correlations.append(corr)
    
    spearman_mean = float(np.mean(correlations)) if correlations else 0.0
    spearman_min = float(np.min(correlations)) if correlations else 0.0
    
    # TopK overlap (K=10)
    topk = 10
    topk_sets = []
    for s in seed_cols:
        top = pivot[s].dropna().nlargest(topk).index.tolist()
        topk_sets.append(set(top))
    
    if len(topk_sets) < 2:
        topk_overlap = 1.0
    else:
        # Pairwise Jaccard
        overlaps = []
        for i, s1 in enumerate(topk_sets):
            for s2 in topk_sets[i+1:]:
                if len(s1 | s2) > 0:
                    overlaps.append(len(s1 & s2) / len(s1 | s2))
        topk_overlap = float(np.mean(overlaps)) if overlaps else 0.0
    
    return {
        "spearman_mean": round(spearman_mean, 4),
        "spearman_min": round(spearman_min, 4),
        "topk_overlap": round(topk_overlap, 4),
    }


def aggregate_seed_results(
    results_by_seed: List[Dict[str, Any]],
    metric_cols: List[str],
) -> List[Dict[str, Any]]:
    """
    Aggregate results across seeds: mean, median, p05, p95, worst for each metric.
    
    Returns:
        List of dicts, one per combo_id, with aggregated columns.
    """
    df = pd.DataFrame(results_by_seed)
    if df.empty:
        return []
    
    # Group by combo_id
    grouped = df.groupby("combo_id")
    
    agg_rows = []
    for combo_id, grp in grouped:
        row = {"combo_id": combo_id, "n_seeds": len(grp)}
        
        # Copy first instance params
        param_cols = [c for c in grp.columns if c.startswith("stop_loss.") or c.startswith("kelly.") or c.startswith("max_drawdown.")]
        for pc in param_cols:
            row[pc] = grp[pc].iloc[0]
        
        # Aggregate metrics
        for col in metric_cols:
            if col not in grp.columns:
                continue
            vals = grp[col].dropna()
            if len(vals) == 0:
                row[f"{col}_mean"] = np.nan
                row[f"{col}_median"] = np.nan
                row[f"{col}_p05"] = np.nan
                row[f"{col}_p95"] = np.nan
                row[f"{col}_worst"] = np.nan
            else:
                row[f"{col}_mean"] = float(vals.mean())
                row[f"{col}_median"] = float(vals.median())
                row[f"{col}_p05"] = float(np.percentile(vals, 5))
                row[f"{col}_p95"] = float(np.percentile(vals, 95))
                # Worst: min for return-like, max for drawdown
                if "drawdown" in col.lower():
                    row[f"{col}_worst"] = float(vals.min())  # More negative = worse
                else:
                    row[f"{col}_worst"] = float(vals.min())  # Lowest score/return = worst
        
        # Compute robust score
        score_vals = grp["score"].dropna()
        if len(score_vals) > 0:
            row["score_robust"] = float(np.percentile(score_vals, 5))  # p05 as robust
        else:
            row["score_robust"] = 0.0
        
        agg_rows.append(row)
    
    # Sort by score_robust descending
    agg_rows.sort(key=lambda x: x.get("score_robust", 0), reverse=True)
    return agg_rows


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
    scenario: str = "default",
) -> Dict[str, Any]:
    """
    Ejecuta un backtest con las reglas dadas.
    Retorna dict con métricas.
    
    Args:
        scenario: "default" for standard synthetic prices,
                  "sensitivity" for vol-clustering prices with crash phase
    """
    np.random.seed(seed)
    
    baseline = config.get("baseline", {})
    start_date = baseline.get("start_date", "2024-01-01")
    periods = baseline.get("periods", 252)
    initial_capital = baseline.get("initial_capital", 10000)
    
    # Select price generator based on scenario
    if scenario == "sensitivity":
        prices = generate_sensitivity_prices(start_date=start_date, periods=periods, seed=seed)
    else:
        prices = generate_synthetic_prices(start_date=start_date, periods=periods)
    
    rm = RiskManagerV05(rules)
    
    bt = SimpleBacktester(prices, initial_capital=initial_capital)
    df = bt.run(risk_manager=rm)
    
    metrics = calculate_metrics(df)
    metrics["num_trades"] = len(bt.trades)
    
    # --- Métricas de closed_trades (win_rate, PnL) ---
    ct = bt.closed_trades
    closed_count = len(ct)
    wins = [t["realized_pnl"] for t in ct if t["realized_pnl"] > 0]
    losses = [t["realized_pnl"] for t in ct if t["realized_pnl"] < 0]
    
    metrics["closed_trades_count"] = closed_count
    metrics["wins_count"] = len(wins)
    metrics["losses_count"] = len(losses)
    metrics["win_rate"] = len(wins) / closed_count if closed_count > 0 else 0.0
    metrics["gross_pnl"] = sum(t["realized_pnl"] for t in ct)
    metrics["avg_win"] = sum(wins) / len(wins) if wins else 0.0
    metrics["avg_loss"] = sum(losses) / len(losses) if losses else 0.0
    
    # --- Métricas de risk_events (ATR/hard_stop counters) ---
    risk_events = getattr(bt, "risk_events", [])
    if risk_events:
        total_ticks = len(risk_events)
        
        # Extraer estados por tick
        hard_stop_flags = []
        atr_triggered_flags = []
        
        for evt in risk_events:
            rd = evt.get("risk_decision", {})
            reasons = rd.get("reasons", [])
            
            # hard_stop: "dd_hard" en reasons o force_close_positions=True
            is_hard = "dd_hard" in reasons or rd.get("force_close_positions", False)
            hard_stop_flags.append(is_hard)
            
            # atr_triggered: "stop_loss_atr" en reasons o stop_signals no vacío
            is_atr = "stop_loss_atr" in reasons or len(rd.get("stop_signals", [])) > 0
            atr_triggered_flags.append(is_atr)
        
        # Contar transiciones False->True
        hard_stop_trigger_count = sum(
            1 for i in range(1, len(hard_stop_flags))
            if hard_stop_flags[i] and not hard_stop_flags[i-1]
        )
        atr_stop_count = sum(
            1 for i in range(1, len(atr_triggered_flags))
            if atr_triggered_flags[i] and not atr_triggered_flags[i-1]
        )
        
        # pct_time_hard_stop
        ticks_hard = sum(hard_stop_flags)
        pct_time_hard_stop = ticks_hard / total_ticks if total_ticks > 0 else 0.0
        
        metrics["atr_stop_count"] = atr_stop_count
        metrics["hard_stop_trigger_count"] = hard_stop_trigger_count
        metrics["pct_time_hard_stop"] = pct_time_hard_stop
        metrics["missing_risk_events"] = False
    else:
        metrics["atr_stop_count"] = 0
        metrics["hard_stop_trigger_count"] = 0
        metrics["pct_time_hard_stop"] = 0.0
        metrics["missing_risk_events"] = True
    
    # Calmar ratio
    if metrics.get("max_drawdown", 0) != 0:
        metrics["calmar_ratio"] = metrics.get("cagr", 0) / abs(metrics["max_drawdown"])
    else:
        metrics["calmar_ratio"] = 0.0

    # Extract diagnostics from backtester
    diagnostics = getattr(bt, "diagnostics", {})
    metrics["signal_count"] = diagnostics.get("signal_count", 0)
    metrics["signal_rejected_count"] = diagnostics.get("signal_rejected_count", 0)
    metrics["price_missing_count"] = diagnostics.get("price_missing_count", 0)
    metrics["size_zero_count"] = 0  # Placeholder if not tracked in backtester yet
    
    # Extract structured risk rejection reasons
    risk_counter = getattr(bt, "risk_reject_reasons_counter", {})
    # Serialize top reasons as pipe-separated string for CSV
    top_reasons = sorted(risk_counter.items(), key=lambda x: -x[1])[:5]
    metrics["risk_reject_reasons_top"] = "|".join(f"{r}:{c}" for r, c in top_reasons) if top_reasons else ""
    # Keep raw dict for aggregation
    metrics["_risk_reject_reasons_dict"] = dict(risk_counter)

    return metrics


# -------------------------------------------------------------------
# Gate Evaluation
# -------------------------------------------------------------------
def passes_quality_gate(row: Dict[str, Any], qg: Optional[Dict[str, Any]]) -> bool:
    """Evalúa si un resultado activo pasa el quality gate."""
    if not qg:
        return True
    return (
        row.get("num_trades", 0) >= qg.get("min_trades", 1) and
        row.get("sharpe_ratio", 0) >= qg.get("min_sharpe", 0) and
        row.get("cagr", 0) >= qg.get("min_cagr", 0) and
        row.get("max_drawdown", 0) >= qg.get("max_drawdown_absolute", -1.0)
    )


def evaluate_gates(
    results: List[Dict[str, Any]],
    activity_gate: Optional[Dict[str, Any]],
    quality_gate: Optional[Dict[str, Any]],
) -> Tuple[bool, bool, List[str], Dict[str, Any]]:
    """
    Evalúa activity gate y quality gate sobre los resultados.
    
    Returns:
        (gate_passed, insufficient_activity, gate_fail_reasons, stats)
    """
    total_n = len(results)
    if total_n == 0:
        return False, True, ["no_results"], {}
    
    # Clasificar activos/inactivos
    active_results = [r for r in results if r.get("is_active", False)]
    inactive_results = [r for r in results if not r.get("is_active", False)]
    
    active_n = len(active_results)
    inactive_n = len(inactive_results)
    active_rate = active_n / total_n
    inactive_rate = inactive_n / total_n
    
    # Quality pass rate sobre activos
    if active_n > 0:
        active_pass_count = sum(1 for r in active_results if passes_quality_gate(r, quality_gate))
        active_pass_rate = active_pass_count / active_n
    else:
        active_pass_count = 0
        active_pass_rate = 0.0
    
    stats = {
        "active_n": active_n,
        "inactive_n": inactive_n,
        "active_rate": round(active_rate, 4),
        "inactive_rate": round(inactive_rate, 4),
        "active_pass_count": active_pass_count,
        "active_pass_rate": round(active_pass_rate, 4),
    }
    
    gate_fail_reasons = []
    insufficient_activity = False
    
    # Evaluar activity gate - cada threshold independiente
    if activity_gate:
        min_active_n = activity_gate.get("min_active_n")
        min_active_rate = activity_gate.get("min_active_rate")
        max_inactive_rate = activity_gate.get("max_inactive_rate")
        min_active_pass_rate = activity_gate.get("min_active_pass_rate")
        
        # Check cada threshold de actividad si está definido
        if min_active_n is not None and active_n < min_active_n:
            gate_fail_reasons.append("active_n_below_min")
            insufficient_activity = True
        
        if min_active_rate is not None and active_rate < min_active_rate:
            gate_fail_reasons.append("active_rate_below_min")
            insufficient_activity = True
        
        if max_inactive_rate is not None and inactive_rate > max_inactive_rate:
            gate_fail_reasons.append("inactive_rate_above_max")
            insufficient_activity = True
        
        # Check quality pass rate entre activos
        if min_active_pass_rate is not None and active_pass_rate < min_active_pass_rate:
            gate_fail_reasons.append("active_pass_rate_below_min")
    
    gate_passed = len(gate_fail_reasons) == 0
    
    return gate_passed, insufficient_activity, gate_fail_reasons, stats


def aggregate_rejection_reasons(results: List[Dict[str, Any]]) -> Tuple[Dict[str, int], List[str]]:
    """
    Agrega razones de rechazo de todos los resultados inactivos.
    
    Returns:
        (rejection_agg, top_inactive_reasons)
    """
    rejection_keys = [
        "rejection_no_signal",
        "rejection_blocked_risk",
        "rejection_size_zero",
        "rejection_price_missing",
        "rejection_other",
    ]
    
    agg = {k: 0 for k in rejection_keys}
    for r in results:
        if not r.get("is_active", False):
            for k in rejection_keys:
                agg[k] += r.get(k, 0)
    
    # Top reasons ordenadas por conteo
    sorted_reasons = sorted(
        [(k, v) for k, v in agg.items() if v > 0],
        key=lambda x: -x[1]
    )
    top_reasons = [k for k, v in sorted_reasons]
    
    return agg, top_reasons


def aggregate_risk_reject_reasons(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Agrega todos los risk_reject_reasons de todos los combos en un Counter global.
    Retorna dict ordenado por conteo descendente (top 10).
    """
    from collections import Counter
    global_counter: Counter = Counter()
    
    for r in results:
        combo_reasons = r.get("_risk_reject_reasons_dict", {})
        for reason, count in combo_reasons.items():
            global_counter[reason] += count
    
    # Top 10 ordenados
    top = dict(global_counter.most_common(10))
    return top


def classify_inactive_reason(num_trades: int, diag: Dict[str, int]) -> Dict[str, int]:
    """
    Clasifica razón de inactividad (1-hot) basándose en diagnósticos.
    """
    result = {
        "rejection_no_signal": 0,
        "rejection_blocked_risk": 0,
        "rejection_size_zero": 0,
        "rejection_price_missing": 0,
        "rejection_other": 0,
    }
    if num_trades > 0:
        return result
    
    # Jerarquía de razones
    # 1. Price missing (datos sucios/insuficientes)
    if diag.get("price_missing_count", 0) > 0:
        result["rejection_price_missing"] = 1
    # 2. No signal (nunca se intentó rebalancear)
    elif diag.get("signal_count", 0) == 0:
        result["rejection_no_signal"] = 1
    # 3. Blocked by risk (intentos rechazados)
    elif diag.get("signal_rejected_count", 0) > 0:
        result["rejection_blocked_risk"] = 1
    # 4. Size zero (intentos aceptados pero tamaño 0, requiere soporte en BT)
    elif diag.get("size_zero_count", 0) > 0:
        result["rejection_size_zero"] = 1
    # 5. Other (fallback)
    else:
        result["rejection_other"] = 1
    
    return result


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


def compute_rules_hash(rules: Dict[str, Any]) -> str:
    """Hash MD5 de las rules efectivas (subset calibrado) para verificar wiring."""
    # Extraer solo las secciones que se calibran
    calibrated = {
        "kelly": rules.get("kelly", {}),
        "max_drawdown": rules.get("max_drawdown", {}),
        "stop_loss": rules.get("stop_loss", {}),
    }
    s = json.dumps(calibrated, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()[:12]


def compute_score(row: Dict[str, Any], formula: str) -> float:
    """Calcula score según fórmula. Fallback a sharpe_ratio si hay error."""
    try:
        # Crear contexto con todas las métricas disponibles
        ctx = {
            "sharpe_ratio": float(row.get("sharpe_ratio", 0) or 0),
            "cagr": float(row.get("cagr", 0) or 0),
            "max_drawdown": float(row.get("max_drawdown", 0) or 0),
            "calmar_ratio": float(row.get("calmar_ratio", 0) or 0),
            "win_rate": float(row.get("win_rate", 0) or 0),
            "gross_pnl": float(row.get("gross_pnl", 0) or 0),
            "atr_stop_count": int(row.get("atr_stop_count", 0) or 0),
            "hard_stop_trigger_count": int(row.get("hard_stop_trigger_count", 0) or 0),
            "pct_time_hard_stop": float(row.get("pct_time_hard_stop", 0) or 0),
            "abs": abs,
        }
        return float(eval(formula, {"__builtins__": {}}, ctx))
    except Exception:
        return float(row.get("sharpe_ratio", 0) or 0)


def run_calibration(
    mode: str = "quick",
    max_combinations: Optional[int] = None,
    seeds: Optional[List[int]] = None,
    output_dir_override: Optional[str] = None,
    strict_gate: bool = False,
    profile_override: Optional[str] = None,
    config_path_override: Optional[str] = None,
    scenario: str = "default",
) -> int:
    """
    Ejecuta la calibración según el grid definido en el YAML.
    Escribe todos los artefactos en output_dir (CLI override > YAML).
    
    Args:
        seeds: List of random seeds for multi-seed robustness (default: [42])
        scenario: "default" or "sensitivity" for price generation mode
    
    Returns:
        Exit code (0 = success, 1 = gate failed with strict_gate)
    """
    # Default to single seed for backward compat
    if seeds is None:
        seeds = [42]
    run_start = time.time()
    
    # Cargar configs
    effective_config_path = Path(config_path_override) if config_path_override else CONFIG_PATH
    config = load_yaml(effective_config_path)
    base_rules = load_yaml(RULES_PATH)

    # Resolver output_dir: CLI override > YAML > default
    if output_dir_override:
        output_dir = Path(output_dir_override)
    else:
        output_dir_rel = config.get("output", {}).get("dir", DEFAULT_OUTPUT_DIR)
        output_dir = REPO_ROOT / output_dir_rel
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Paths de artefactos dentro de output_dir
    log_file = output_dir / "run_log.txt"
    csv_file = output_dir / "results.csv"  # Legacy compat (same as results_by_seed for single seed)
    results_by_seed_file = output_dir / "results_by_seed.csv"
    results_agg_file = output_dir / "results_agg.csv"
    summary_file = output_dir / "summary.md"
    topk_file = output_dir / "topk.json"
    meta_file = output_dir / "run_meta.json"

    grid = config.get("grid", {})
    yaml_seed = config.get("repro", {}).get("seed", 42)
    yaml_max_combos = config.get("execution", {}).get("max_combinations")
    score_formula = config.get("score", {}).get("formula", "sharpe_ratio")
    top_k = config.get("search", {}).get("top_k", 20)
    
    # Cargar profile según modo y override
    profiles = config.get("profiles", {})
    
    # Determinar profile efectivo:
    # 1. Si profile_override especificado -> usar ese
    # 2. Si mode=="full" sin override -> usar "full_demo" por defecto
    # 3. En otro caso -> usar mode como profile name
    if profile_override:
        effective_profile_name = profile_override
    elif mode == "full":
        effective_profile_name = "full_demo"
    else:
        effective_profile_name = mode
    
    profile = profiles.get(effective_profile_name, {})
    activity_gate = profile.get("activity_gate")
    quality_gate = profile.get("quality_gate")

    # Use first seed as primary (for backward compat logs), all seeds for multi-seed
    primary_seed = seeds[0]
    yaml_seed = config.get("repro", {}).get("seed", 42)

    # Generar combinaciones
    all_combos = flatten_grid(grid)
    total_combos = len(all_combos)

    # Limitar según modo
    if mode == "quick":
        limit = max_combinations or yaml_max_combos or 12
        combos = all_combos[:limit]
    else:
        if max_combinations:
            combos = all_combos[:max_combinations]
        else:
            combos = all_combos

    # Inicializar log
    log_file.write_text(f"Calibration run started at {datetime.now().isoformat()}\n")

    # Inicializar CSV con nuevas columnas
    csv_headers = [
        "seed",  # Multi-seed support
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
        "closed_trades_count",
        "wins_count",
        "losses_count",
        "win_rate",
        "gross_pnl",
        "avg_win",
        "avg_loss",
        "atr_stop_count",
        "hard_stop_trigger_count",
        "pct_time_hard_stop",
        "missing_risk_events",
        "score",
        # === Nuevas columnas 2E ===
        "is_active",
        "rejection_no_signal",
        "rejection_blocked_risk",
        "rejection_size_zero",
        "rejection_price_missing",
        "rejection_other",
        "risk_reject_reasons_top",  # Structured risk reasons (2E-4-2)
        # === Nuevas columnas 2B-3.3-7: effective config verification ===
        "effective_config_hash",
        "effective_kelly_cap_factor",
        "effective_dd_soft_limit_pct",
        "effective_dd_hard_limit_pct",
        "effective_dd_size_multiplier_soft",
        "effective_atr_multiplier",
        "effective_min_stop_pct",
    ]
    # Añadir parámetros al header
    if combos:
        param_keys = sorted(combos[0].keys())
        csv_headers.extend(param_keys)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
        writer.writeheader()

    log(f"Mode: {mode}, Profile: {effective_profile_name}, Total grid: {total_combos}, Running: {len(combos)}, Seeds: {seeds}", log_file)
    log(f"Output dir: {output_dir}", log_file)

    all_results = []  # All rows across all seeds
    total_runs = len(seeds) * len(combos)
    run_idx = 0

    for current_seed in seeds:
        log(f"=== Starting seed {current_seed} ===", log_file)
        np.random.seed(current_seed)  # Global RNG reset per seed
        
        for i, params in enumerate(combos, 1):
            run_idx += 1
            combo_id = generate_combo_id(params)
            log(f"START seed={current_seed} combo_id={combo_id} ({run_idx}/{total_runs}) params={params}", log_file)

            start_time = time.time()
            row: Dict[str, Any] = {
                "seed": current_seed,
                "combo_id": combo_id,
                "status": "ok",
                "error_type": "",
                "error_msg": "",
                "traceback_short": "",
                "duration_s": 0.0,
                "score": 0.0,
                # Nuevas columnas con defaults
                "is_active": False,
                "rejection_no_signal": 0,
                "rejection_blocked_risk": 0,
                "rejection_size_zero": 0,
                "rejection_price_missing": 0,
                "rejection_other": 0,
            }
            row.update(params)

            try:
                # Aplicar overlay
                rules = apply_overlay(base_rules, params)
                rules.setdefault("risk_manager", {})["mode"] = config.get("execution", {}).get("mode", "active")

                # === 2B-3.3-7: Capture effective config values for wiring verification ===
                row["effective_config_hash"] = compute_rules_hash(rules)
                row["effective_kelly_cap_factor"] = rules.get("kelly", {}).get("cap_factor", None)
                row["effective_dd_soft_limit_pct"] = rules.get("max_drawdown", {}).get("soft_limit_pct", None)
                row["effective_dd_hard_limit_pct"] = rules.get("max_drawdown", {}).get("hard_limit_pct", None)
                row["effective_dd_size_multiplier_soft"] = rules.get("max_drawdown", {}).get("size_multiplier_soft", None)
                row["effective_atr_multiplier"] = rules.get("stop_loss", {}).get("atr_multiplier", None)
                row["effective_min_stop_pct"] = rules.get("stop_loss", {}).get("min_stop_pct", None)

                # Ejecutar backtest
                metrics = run_single_backtest(rules, current_seed, config, scenario=scenario)
                row.update(metrics)
                row["score"] = compute_score(row, score_formula)
                
                # Determinar is_active y diagnóstico de inactividad
                num_trades = row.get("num_trades", 0)
                row["is_active"] = num_trades > 0
                
                # Clasificar razón de inactividad usando diagnósticos reales
                diag_data = {
                    "signal_count": row.get("signal_count", 0),
                    "signal_rejected_count": row.get("signal_rejected_count", 0),
                    "price_missing_count": row.get("price_missing_count", 0),
                    "size_zero_count": row.get("size_zero_count", 0),
                }
                rejection_flags = classify_inactive_reason(num_trades, diag_data)
                row.update(rejection_flags)

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

            all_results.append(row)

    # Use all_results for backward compat with existing logic
    results = all_results

    # Stats básicos
    ok_count = sum(1 for r in results if r["status"] == "ok")
    error_count = len(results) - ok_count
    run_duration = round(time.time() - run_start, 2)
    
    log(f"DONE: {ok_count} ok, {error_count} errors, total {len(results)}, duration {run_duration}s", log_file)

    # ----- Evaluar gates (solo para full mode con gates configurados) -----
    gate_passed, insufficient_activity, gate_fail_reasons, gate_stats = evaluate_gates(
        results, activity_gate, quality_gate
    )
    rejection_agg, top_inactive_reasons = aggregate_rejection_reasons(results)
    
    # Determinar suggested_exit_code
    suggested_exit_code = 0 if gate_passed else 1
    
    # Imprimir línea de resumen de gate (solo full mode)
    if mode == "full":
        gate_status = "PASS" if gate_passed else "FAIL"
        reasons_str = ",".join(gate_fail_reasons) if gate_fail_reasons else "none"
        gate_summary = (
            f"GATE {mode}: {gate_status} | "
            f"active_n={gate_stats.get('active_n', 0)} "
            f"active_rate={gate_stats.get('active_rate', 0):.2%} "
            f"active_pass_rate={gate_stats.get('active_pass_rate', 0):.2%} "
            f"reasons=[{reasons_str}]"
        )
        print(gate_summary)
        log(gate_summary, log_file)

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
                "is_active": c.get("is_active", False),
                "params": {k: c[k] for k in c if "." in k},
            }
            for i, c in enumerate(topk_candidates)
        ],
    }
    with open(topk_file, "w", encoding="utf-8") as f:
        json.dump(topk_data, f, indent=2)

    # ----- Generate run_meta.json -----
    # Compute ranking stability if multi-seed
    stability_metrics = compute_ranking_stability(results, seeds, score_col="score")
    
    meta_data = {
        "config_hash": compute_config_hash(config),
        "git_head": get_git_head(),
        "seeds": seeds,
        "n_seeds": len(seeds),
        "mode": mode,
        "gate_profile": effective_profile_name,
        "total_grid": total_combos,
        "num_combos": len(combos),
        "running": len(combos) * len(seeds),
        "ok": ok_count,
        "errors": error_count,
        "duration_s": run_duration,
        "timestamp": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        # === Nuevos campos 2E ===
        "active_n": gate_stats.get("active_n", 0),
        "inactive_n": gate_stats.get("inactive_n", 0),
        "active_rate": gate_stats.get("active_rate", 0.0),
        "inactive_rate": gate_stats.get("inactive_rate", 0.0),
        "active_pass_rate": gate_stats.get("active_pass_rate", 0.0),
        "gate_passed": gate_passed,
        "insufficient_activity": insufficient_activity,
        "gate_fail_reasons": gate_fail_reasons,
        "suggested_exit_code": suggested_exit_code,
        "rejection_reasons_agg": rejection_agg,
        "top_inactive_reasons": top_inactive_reasons,
        "risk_reject_reasons_topk": aggregate_risk_reject_reasons(results),
        # === Multi-seed stability metrics (2G) ===
        "spearman_mean": stability_metrics["spearman_mean"],
        "spearman_min": stability_metrics["spearman_min"],
        "topk_overlap": stability_metrics["topk_overlap"],
    }
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2)
    
    # ----- Generate results_by_seed.csv (copy of results.csv for multi-seed) -----
    import shutil
    shutil.copy(csv_file, results_by_seed_file)
    
    # ----- Generate results_agg.csv (aggregated across seeds) -----
    metric_cols = ["score", "sharpe_ratio", "cagr", "max_drawdown", "calmar_ratio", "win_rate", "num_trades"]
    agg_results = aggregate_seed_results(results, metric_cols)
    if agg_results:
        agg_df = pd.DataFrame(agg_results)
        agg_df.to_csv(results_agg_file, index=False, encoding="utf-8")

    # ----- Generate summary.md -----
    summary_lines = [
        "# Calibration 2B Run Summary",
        "",
        f"**Timestamp**: {datetime.now().isoformat()}",
        f"**Mode**: {mode}",
        f"**Seeds**: {seeds}",
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
        "## Activity Analysis",
        "",
        f"- Active scenarios: {gate_stats.get('active_n', 0)} ({gate_stats.get('active_rate', 0):.2%})",
        f"- Inactive scenarios: {gate_stats.get('inactive_n', 0)} ({gate_stats.get('inactive_rate', 0):.2%})",
        f"- Active pass rate: {gate_stats.get('active_pass_rate', 0):.2%}",
        f"- **Gate passed**: {'YES' if gate_passed else 'NO'}",
    ]
    
    if gate_fail_reasons:
        summary_lines.append(f"- Gate fail reasons: {', '.join(gate_fail_reasons)}")
    
    summary_lines.extend([
        "",
        "## Score Formula",
        "",
        f"```",
        f"{score_formula}",
        f"```",
        "",
        "## Top-K Candidates",
        "",
        "| Rank | Combo ID | Score | Sharpe | CAGR | MaxDD | Active |",
        "|------|----------|-------|--------|------|-------|--------|",
    ])
    for c in topk_candidates[:10]:  # Show top 10 in summary
        active_str = "✓" if c.get("is_active") else "✗"
        summary_lines.append(
            f"| {topk_candidates.index(c) + 1} | {c['combo_id']} | {c.get('score', 0):.4f} | "
            f"{c.get('sharpe_ratio', 0):.4f} | {c.get('cagr', 0):.4f} | {c.get('max_drawdown', 0):.4f} | {active_str} |"
        )
    
    summary_lines.extend([
        "",
        "## Artifacts",
        "",
        f"- `results.csv` — Full results table",
        f"- `run_log.txt` — Execution log",
        f"- `topk.json` — Top-{top_k} candidates with scores",
        f"- `run_meta.json` — Run metadata (hash, git, seed, timing, gates)",
        f"- `summary.md` — This file",
        "",
        "## Reproducibility",
        "",
        f"```bash",
        f"python tools/run_calibration_2B.py --mode {mode} --max-combinations {len(combos)} --seeds {','.join(map(str, seeds))}",
        f"```",
    ])
    
    summary_file.write_text("\n".join(summary_lines), encoding="utf-8")

    log(f"Artifacts written to: {output_dir}", log_file)
    
    # Determinar exit code
    if strict_gate and mode == "full" and not gate_passed:
        return 1
    return 0


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------
def normalize_args(argv: Optional[List[str]] = None) -> List[str]:
    """
    Pre-procesa argv para manejar el alias --mode full_demo.
    
    Convierte: --mode full_demo -> --mode full --profile full_demo
    (solo si el usuario no especificó --profile explícitamente)
    """
    if argv is None:
        argv = sys.argv[1:]
    
    argv = list(argv)  # Copia para no mutar original
    
    # Detectar --mode full_demo
    if "--mode" not in argv:
        return argv
    
    mode_idx = argv.index("--mode")
    if mode_idx + 1 >= len(argv) or argv[mode_idx + 1] != "full_demo":
        return argv
    
    # Es --mode full_demo, verificar conflicto con --profile
    has_explicit_profile = "--profile" in argv
    
    if has_explicit_profile:
        profile_idx = argv.index("--profile")
        if profile_idx + 1 < len(argv):
            explicit_profile = argv[profile_idx + 1]
            if explicit_profile != "full_demo":
                raise ValueError(
                    f"Conflicto: --mode full_demo implica --profile full_demo, "
                    f"pero se especificó --profile {explicit_profile}"
                )
    
    # Normalizar: full_demo -> full
    argv[mode_idx + 1] = "full"
    
    # Añadir --profile full_demo si no está explícito
    if not has_explicit_profile:
        argv.extend(["--profile", "full_demo"])
    
    return argv


def main():
    epilog = """
Examples:
  # Modo rápido (default)
  python tools/run_calibration_2B.py --mode quick

  # Modo completo con profile full_demo (recomendado para entorno sintético)
  python tools/run_calibration_2B.py --mode full --profile full_demo

  # Alias: equivale al anterior
  python tools/run_calibration_2B.py --mode full_demo

  # Modo completo con gates estrictos (producción)
  python tools/run_calibration_2B.py --mode full --profile full --strict-gate
"""
    parser = argparse.ArgumentParser(
        description="Run 2B risk calibration grid",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full", "full_demo"],
        default="quick",
        help="quick: limited combos, full: all combos, full_demo: alias for full+profile full_demo",
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
        default=None,
        help="Single random seed (legacy, use --seeds for multi-seed)",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="42",
        help="Comma-separated seeds for multi-seed robustness (default: '42')",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Override output directory (default: use YAML output.dir)",
    )
    parser.add_argument(
        "--strict-gate",
        action="store_true",
        default=False,
        help="Exit with code 1 if gate fails in full mode (default: false)",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Gate profile to use (quick, full_demo, full). Default: auto (full->full_demo)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to config YAML (default: configs/risk_calibration_2B.yaml)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=["default", "sensitivity"],
        default="default",
        help="Price generation scenario: default (uniform GBM) or sensitivity (vol-clustering with crash)",
    )

    # Normalizar argv para manejar alias full_demo
    try:
        normalized_argv = normalize_args()
    except ValueError as e:
        parser.error(str(e))
    
    args = parser.parse_args(normalized_argv)
    
    # Resolve seeds: --seed takes precedence for backward compat
    if args.seed is not None:
        seeds = [args.seed]
    else:
        try:
            seeds = parse_seeds(args.seeds)
        except ValueError as e:
            parser.error(str(e))

    exit_code = run_calibration(
        mode=args.mode,
        max_combinations=args.max_combinations,
        seeds=seeds,
        output_dir_override=args.output_dir,
        strict_gate=args.strict_gate,
        profile_override=args.profile,
        config_path_override=args.config,
        scenario=args.scenario,
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
