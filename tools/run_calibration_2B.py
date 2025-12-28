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
    seed: int = 42,
    output_dir_override: Optional[str] = None,
    strict_gate: bool = False,
    profile_override: Optional[str] = None,
) -> int:
    """
    Ejecuta la calibración según el grid definido en el YAML.
    Escribe todos los artefactos en output_dir (CLI override > YAML).
    
    Returns:
        Exit code (0 = success, 1 = gate failed with strict_gate)
    """
    run_start = time.time()
    
    # Cargar configs
    config = load_yaml(CONFIG_PATH)
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
    csv_file = output_dir / "results.csv"
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
        if max_combinations:
            combos = all_combos[:max_combinations]
        else:
            combos = all_combos

    # Inicializar log
    log_file.write_text(f"Calibration run started at {datetime.now().isoformat()}\n")

    # Inicializar CSV con nuevas columnas
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
    ]
    # Añadir parámetros al header
    if combos:
        param_keys = sorted(combos[0].keys())
        csv_headers.extend(param_keys)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers, extrasaction="ignore")
        writer.writeheader()

    log(f"Mode: {mode}, Profile: {effective_profile_name}, Total grid: {total_combos}, Running: {len(combos)}, Seed: {effective_seed}", log_file)
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

            # Ejecutar backtest
            metrics = run_single_backtest(rules, effective_seed, config)
            row.update(metrics)
            row["score"] = compute_score(row, score_formula)
            
            # Determinar is_active y diagnóstico de inactividad
            num_trades = row.get("num_trades", 0)
            row["is_active"] = num_trades > 0
            
            # Diagnóstico fallback: si 0 trades sin causa detectable, rejection_other=1
            if num_trades == 0:
                row["rejection_other"] = 1

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
    meta_data = {
        "config_hash": compute_config_hash(config),
        "git_head": get_git_head(),
        "seed": effective_seed,
        "mode": mode,
        "gate_profile": effective_profile_name,
        "total_grid": total_combos,
        "num_combos": len(combos),
        "running": len(combos),
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
        f"python tools/run_calibration_2B.py --mode {mode} --max-combinations {len(combos)} --seed {effective_seed}",
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

    args = parser.parse_args()

    exit_code = run_calibration(
        mode=args.mode,
        max_combinations=args.max_combinations,
        seed=args.seed,
        output_dir_override=args.output_dir,
        strict_gate=args.strict_gate,
        profile_override=args.profile,
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
