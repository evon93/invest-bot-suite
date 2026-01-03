#!/usr/bin/env python3
"""
tools/build_dashboard.py

Generates a static HTML dashboard + JSON summary from multiple calibration runs.
Accepts glob patterns for run directories.

Outputs:
- report/dashboard/index.html
- report/dashboard/summary.json

Features:
- Robust parsing (best-effort).
- Auto-discovery of active rates and rejection reasons.
- Aggregation of robust metrics.
- Deterministic output (reproducible HTML/JSON).
"""

import argparse
import glob
import json
import math
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
import datetime

# --- Constants & Heuristics ---

METRIC_COLS_ROBUST = {
    "worst_dd": lambda df: df["max_drawdown"].min() if "max_drawdown" in df.columns else None,
    # p05_sharpe: handled dynamically if col exists
}

REASON_CANDIDATES = [
    "inactive_reason", "rejection_reason", "inactive_reasons", 
    "risk_rejection_reason", "risk_rejection_reasons"
]

def parse_run_dir(run_dir: str, topn: int) -> Dict[str, Any]:
    """Parses a single run directory and extracts metrics."""
    path = Path(run_dir)
    res = {
        "run_dir": str(path),
        "folder_name": path.name,
        "valid": False,
        "errors": [],
        "csv_used": None,
        "n_rows": 0,
        "active_rate": None,
        "metrics": {},
        "top_reasons": [],
        "top_configs": [],
        "run_meta": {}
    }

    if not path.is_dir():
        res["errors"].append(f"Directory not found: {run_dir}")
        return res

    # 1. Load run_meta.json
    meta_path = path / "run_meta.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                res["run_meta"] = json.load(f)
        except Exception as e:
            res["errors"].append(f"Failed to parse run_meta.json: {e}")

    # 2. Find CSV
    csv_path = None
    if (path / "results_agg.csv").exists():
        csv_path = path / "results_agg.csv"
        res["csv_used"] = "results_agg.csv"
    elif (path / "results.csv").exists():
        csv_path = path / "results.csv"
        res["csv_used"] = "results.csv"
    
    if not csv_path:
        res["errors"].append("No results.csv or results_agg.csv found.")
        return res

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        res["errors"].append(f"Failed to read CSV: {e}")
        return res

    res["valid"] = True
    res["n_rows"] = len(df)
    if len(df) == 0:
        return res

    # 3. Active Rate Heuristic
    if "is_active" in df.columns:
        res["active_rate"] = float(df["is_active"].mean())
    elif "active" in df.columns:
        res["active_rate"] = float(df["active"].mean())
    else:
        # Infer from reasons: if reasons exist, active means reason is empty/NaN
        found_reason = False
        for col in REASON_CANDIDATES:
            if col in df.columns:
                # Treat empty string or NaN as "active" (no rejection)
                # But check if ALL valid rows have reasons? usually 'None' means active.
                # Heuristic: active = isna or empty string
                is_active = df[col].isna() | (df[col].astype(str).str.strip() == "") | (df[col].astype(str) == "nan")
                res["active_rate"] = float(is_active.mean())
                found_reason = True
                break
        
    # 4. Top Reasons
    reasons = []
    for col in REASON_CANDIDATES:
        if col in df.columns:
            # Normalize and collect
            raw_vals = df[col].dropna().astype(str).tolist()
            for val in raw_vals:
                val = val.strip()
                if not val or val.lower() == "nan":
                    continue
                # Attempt clear list parsing if it looks like one
                if val.startswith("[") and val.endswith("]"):
                    try:
                        # simple parsing override using string trimming to avoid eval/json overhead if messy
                        inner = val[1:-1]
                        parts = [p.strip().strip("'").strip('"') for p in inner.split(",")]
                        reasons.extend(parts)
                    except:
                        reasons.append(val)
                else:
                    reasons.append(val)
            break # Use first valid reason column found
            
    if reasons:
        counts = Counter(reasons).most_common(5)
        res["top_reasons"] = counts # List of (reason, count)

    # 5. Robust Metrics
    m = {}
    if "max_drawdown" in df.columns:
        m["worst_dd"] = clean_float(df["max_drawdown"].min())
    if "sharpe_ratio" in df.columns:
        m["p05_sharpe"] = clean_float(df["sharpe_ratio"].quantile(0.05))
    if "calmar_ratio" in df.columns:
        m["p05_calmar"] = clean_float(df["calmar_ratio"].quantile(0.05))
    
    # robust specific columns
    for col in df.columns:
        if col.endswith("_worst"):
            m[col] = clean_float(df[col].mean()) # Average worst? Or min? 
            # Actually dashboard usually wants to show 'worst' of the run. 
            # For aggregated files, 'worst' col is already min per seed. 
            # Let's take global min of 'worst' cols.
            m[f"global_{col}"] = clean_float(df[col].min())
    
    res["metrics"] = m

    # 6. Top N Configs
    score_col = "score"
    if "score_robust" in df.columns:
        score_col = "score_robust"
    
    if score_col in df.columns:
        df_sorted = df.sort_values(by=score_col, ascending=False).head(topn)
        
        # Identify params (naive: param_*)
        param_cols = [c for c in df.columns if c.startswith("param_")]
        cols_to_keep = [score_col, "combo_id", "param_id"] + param_cols
        # Add basic metric columns if they exist for context
        for metric in ["net_profit", "total_return", "sharpe_ratio", "max_drawdown", "num_trades"]:
             if metric in df.columns:
                 cols_to_keep.append(metric)
                 
        # Filter existing only
        cols_to_keep = [c for c in cols_to_keep if c in df.columns]
        
        top_list = []
        for idx, row in df_sorted.iterrows():
            item = {k: clean_val(row[k]) for k in cols_to_keep}
            top_list.append(item)
        res["top_configs"] = top_list

    return res

def clean_float(val):
    if val is None: return None
    if isinstance(val, (float, np.floating)):
        if np.isnan(val) or np.isinf(val):
            return None
    return float(val)

def clean_val(val):
    if isinstance(val, (np.integer, int)):
        return int(val)
    return clean_float(val) if isinstance(val, (float, np.floating)) else str(val)

def generate_html(summary_json: Dict, out_file: Path):
    """Generates simple static HTML dashboard."""
    
    runs = summary_json["runs"]
    meta = summary_json["meta"]
    
    html = []
    html.append(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Calibration Run Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 20px; background: #f4f6f8; color: #333; }}
            .container {{ max_width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            h1, h2, h3 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; color: #2c3e50; }}
            .summary-meta {{ margin-bottom: 20px; font-size: 0.9em; color: #666; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 0.9em; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #eee; }}
            th {{ background-color: #f8f9fa; font-weight: 600; color: #555; }}
            tr:hover {{ background-color: #f1f1f1; }}
            .error {{ color: #e74c3c; font-weight: bold; }}
            .metric-box {{ display: inline-block; padding: 10px; background: #f8f9fa; border-radius: 4px; margin-right: 10px; margin-bottom: 10px; min-width: 120px; }}
            .metric-val {{ font-size: 1.2em; font-weight: bold; display: block; }}
            .metric-label {{ font-size: 0.8em; color: #777; }}
            .run-section {{ margin-top: 40px; border-top: 4px solid #eee; padding-top: 20px; }}
            .valid-false {{ border-left: 5px solid #e74c3c; padding-left: 10px; }}
            .valid-true {{ border-left: 5px solid #2ecc71; padding-left: 10px; }}
            details {{ margin-bottom: 10px; }}
            .reasons-list {{ font-size: 0.85em; color: #555; }}
            .top-config-table {{ font-size: 0.85em; overflow-x: auto; display: block; }}
        </style>
    </head>
    <body>
    <div class="container">
        <h1>Calibration Dashboard</h1>
        <div class="summary-meta">
            Runs: {meta.get('n_runs')} | Generated: {meta.get('generated_at', 'N/A')}
        </div>

        <h2>Overview</h2>
        <table>
            <thead>
                <tr>
                    <th>Run Folder</th>
                    <th>Rows</th>
                    <th>Active %</th>
                    <th>Worst DD</th>
                    <th>P05 Sharpe</th>
                    <th>Valid</th>
                </tr>
            </thead>
            <tbody>
    """)

    for r in runs:
        active_str = f"{r['active_rate']*100:.1f}%" if r['active_rate'] is not None else "N/A"
        worst_dd = r['metrics'].get('worst_dd')
        worst_dd_str = f"{worst_dd:.2%}" if worst_dd is not None else "N/A"
        p05_sharpe = r['metrics'].get('p05_sharpe')
        p05_sharpe_str = f"{p05_sharpe:.2f}" if p05_sharpe is not None else "N/A"
        folder_link = f"<a href='#run-{r['folder_name']}'>{r['folder_name']}</a>"
        
        html.append(f"""
            <tr>
                <td>{folder_link}</td>
                <td>{r['n_rows']}</td>
                <td>{active_str}</td>
                <td>{worst_dd_str}</td>
                <td>{p05_sharpe_str}</td>
                <td>{ '✅' if r['valid'] else '❌' }</td>
            </tr>
        """)

    html.append("""
            </tbody>
        </table>
    """)

    for r in runs:
        html.append(f"<div id='run-{r['folder_name']}' class='run-section valid-{str(r['valid']).lower()}'>")
        html.append(f"<h2>Run: {r['folder_name']}</h2>")
        html.append(f"<p>Path: <code>{r['run_dir']}</code></p>")
        
        if not r['valid']:
            html.append("<div class='error'>Errors:</div><ul>")
            for e in r['errors']:
                html.append(f"<li>{e}</li>")
            html.append("</ul></div>")
            continue

        # Metrics Grid
        html.append("<h3>Key Metrics</h3><div>")
        metrics_to_show = {**r['metrics'], "Active Rate": r['active_rate']}
        for k, v in metrics_to_show.items():
            if v is not None:
                val_fmt = f"{v:.4f}" if isinstance(v, float) else str(v)
                html.append(f"<div class='metric-box'><span class='metric-val'>{val_fmt}</span><span class='metric-label'>{k}</span></div>")
        html.append("</div>")

        # Top Reasons
        if r['top_reasons']:
            html.append("<h3>Top Rejection Reasons</h3><ul class='reasons-list'>")
            for reason, count in r['top_reasons']:
                html.append(f"<li><b>{count}</b>: {reason}</li>")
            html.append("</ul>")

        # Top Configs
        if r['top_configs']:
            html.append("<h3>Top Configurations</h3>")
            html.append("<details><summary>Show Top Configs Table</summary><table class='top-config-table'><thead><tr>")
            
            # Header from first item keys
            keys = list(r['top_configs'][0].keys())
            for k in keys:
                html.append(f"<th>{k}</th>")
            html.append("</tr></thead><tbody>")
            
            for config in r['top_configs']:
                html.append("<tr>")
                for k in keys:
                    val = config.get(k)
                    val_str = f"{val:.4f}" if isinstance(val, float) else str(val)
                    html.append(f"<td>{val_str}</td>")
                html.append("</tr>")
            
            html.append("</tbody></table></details>")
        
        html.append("</div>") # End run section

    html.append("""
    </div>
    </body>
    </html>
    """)
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

def main():
    parser = argparse.ArgumentParser(description="Static Dashboard Builder")
    parser.add_argument("--run-dir", action="append", required=True, help="Run directory path or glob (can repeat)")
    parser.add_argument("--out", default="report/dashboard", help="Output directory")
    parser.add_argument("--topn", type=int, default=10, help="Top N configs per run to show")
    parser.add_argument("--include-timestamp", action="store_true", help="Include generation timestamp in meta")

    args = parser.parse_args()
    
    # Expand globs
    run_paths = set()
    for pattern in args.run_dir:
        for p in glob.glob(pattern):
            if os.path.isdir(p):
                run_paths.add(str(Path(p).resolve()))
    
    sorted_paths = sorted(run_paths) # Deterministic order
    
    runs_data = []
    for p in sorted_paths:
        runs_data.append(parse_run_dir(p, args.topn))
    
    summary = {
        "meta": {
            "n_runs": len(runs_data),
            "topn": args.topn,
        },
        "runs": runs_data
    }
    
    if args.include_timestamp:
        summary["meta"]["generated_at"] = datetime.datetime.now().isoformat()

    # Write Outputs
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = out_dir / "summary.json"
    html_path = out_dir / "index.html"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True, ensure_ascii=False)
        
    generate_html(summary, html_path)
    
    print(f"Dashboard generated at: {out_dir}")
    print(f"  JSON: {json_path}")
    print(f"  HTML: {html_path}")

if __name__ == "__main__":
    main()
