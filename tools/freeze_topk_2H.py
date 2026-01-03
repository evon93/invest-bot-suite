#!/usr/bin/env python3
"""
tools/freeze_topk_2H.py

Deterministically selects and freezes the best configuration from multi-seed calibration results (results_agg.csv).
Outputs audit trail and configurations for reproducibility.

Output files:
- configs/best_params_2H.json
- report/topk_freeze_2H.json
"""
import argparse
import hashlib
import json
import subprocess
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Metric columns to exclude when detecting parameters
EXCLUDE_COLS = [
    "score", "score_robust", "seed", "n_seeds", "run_id", "timestamp", 
    "data_source", "realdata_path", "row_hash"
]
METRIC_PREFIXES = ["total_return", "cagr", "max_drawdown", "sharpe", "calmar", 
                  "num_trades", "p05_", "p95_", "median_", "mean_", "worst_", 
                  "spearman_", "topk_", "win_rate"]

def get_git_head() -> str:
    """Gets current git HEAD hash, or 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def compute_file_sha256(filepath: Path) -> str:
    """Computes SHA256 of file content."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def detect_score_column(df: pd.DataFrame) -> str:
    """Detects primary score column (score_robust > score)."""
    if "score_robust" in df.columns:
        return "score_robust"
    elif "score" in df.columns:
        return "score"
    raise ValueError("Input CSV must contain 'score_robust' or 'score' column.")

def detect_param_columns(df: pd.DataFrame) -> List[str]:
    """Heuristic to detect parameter columns."""
    cols = df.columns.tolist()
    # 1. Prefer columns starting with param_
    param_cols = [c for c in cols if c.startswith("param_")]
    if param_cols:
        return param_cols
    
    # 2. Heuristic: Exclude known non-param columns
    candidates = []
    for c in cols:
        lower_c = c.lower()
        if lower_c in EXCLUDE_COLS:
            continue
        if any(lower_c.startswith(p) for p in METRIC_PREFIXES):
            continue
        # Check if it looks like a metric or metadata
        if "id" in lower_c and lower_c not in ["combo_id", "param_id"]: # param_id is tie-breaker but also ID
             if lower_c != "combo_id": # Exclude other IDs unless specifically handled
                 pass 
        candidates.append(c)
    
    return sorted(candidates)

def create_row_hash(row: pd.Series, param_cols: List[str]) -> str:
    """Creates a stable hash for a row based on parameters."""
    # Convert params to string representation sorted by key
    s = json.dumps({k: str(row[k]) for k in param_cols}, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def clean_value(val: Any) -> Any:
    """Converts numpy types to standard python types for JSON serialization."""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.float64, np.float32, float)):
        return float(val) if not np.isnan(val) else None
    return val

def freeze_topk(
    results_agg_path: str, 
    out_config_path: str, 
    out_report_path: str, 
    topk: int
):
    path_in = Path(results_agg_path)
    if not path_in.exists():
        raise FileNotFoundError(f"Input file not found: {results_agg_path}")

    # Load data
    df = pd.read_csv(path_in)
    if df.empty:
        raise ValueError("Input CSV is empty")

    # Audit metadata
    input_sha256 = compute_file_sha256(path_in)
    git_head = get_git_head()
    
    # Score column
    score_col = detect_score_column(df)
    
    # Tie-breaker
    sort_cols = [score_col]
    ascending = [False] # Score desc
    
    if "combo_id" in df.columns:
        sort_cols.append("combo_id")
        ascending.append(True) # ID asc
    elif "param_id" in df.columns:
        sort_cols.append("param_id")
        ascending.append(True)
    else:
        # Fallback: stable row hash
        param_cols_for_hash = detect_param_columns(df)
        df["row_hash"] = df.apply(lambda r: create_row_hash(r, param_cols_for_hash), axis=1)
        sort_cols.append("row_hash")
        ascending.append(True)

    # Sort
    df_sorted = df.sort_values(by=sort_cols, ascending=ascending)
    top_df = df_sorted.head(topk)

    # Param columns for extraction
    param_cols = detect_param_columns(df)
    
    # Prepare Output Data
    topk_list = []
    for rank, (idx, row) in enumerate(top_df.iterrows(), 1):
        params = {k: clean_value(row[k]) for k in param_cols}
        item = {
            "rank": rank,
            "combo_id": row.get("combo_id"),
            "score_column": score_col,
            "score_value": clean_value(row[score_col]),
            "params": params
        }
        topk_list.append(item)

    # Best (Top 1)
    best_item = topk_list[0] if topk_list else None
    
    meta = {
        "source_results_agg_path": str(results_agg_path),
        "source_results_agg_sha256": input_sha256,
        "git_commit": git_head,
        "topk_requested": topk,
        "generated_by": "tools/freeze_topk_2H.py"
    }

    # 1. Config Object
    config_obj = {
        "selected": best_item,
        "meta": meta
    }
    
    # 2. Report Object
    report_obj = {
        "meta": meta,
        "topk_candidates": topk_list
    }

    # Write files (deterministically)
    Path(out_config_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_config_path, "w", encoding="utf-8") as f:
        json.dump(config_obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n") # End with newline

    Path(out_report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_report_path, "w", encoding="utf-8") as f:
        json.dump(report_obj, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")

    print(f"Frozen top config to: {out_config_path}")
    print(f"Frozen top-{topk} report to: {out_report_path}")


def main():
    parser = argparse.ArgumentParser(description="Freeze robust TopK config")
    parser.add_argument("--results-agg", required=True, help="Path to results_agg.csv")
    parser.add_argument("--topk", type=int, default=20, help="Number of top configs to report")
    parser.add_argument("--out-config", default="configs/best_params_2H.json", help="Output JSON for best config")
    parser.add_argument("--out-report", default="report/topk_freeze_2H.json", help="Output JSON for topK report")

    args = parser.parse_args()
    
    try:
        freeze_topk(args.results_agg, args.out_config, args.out_report, args.topk)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
