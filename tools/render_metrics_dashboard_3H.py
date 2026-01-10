#!/usr/bin/env python3
"""
tools/render_metrics_dashboard_3H.py

File-first HTML dashboard for metrics visualization.
No external dependencies - uses only Python stdlib.

Generates a self-contained HTML file with:
- Overview: totals and outcomes
- Stage table: counts and latency percentiles
- Latest events: tail of metrics.ndjson (including rotated files)

Part of ticket AG-3H-3-1.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import html


def load_summary(run_dir: Path) -> Dict[str, Any]:
    """Load metrics_summary.json from run directory."""
    summary_path = run_dir / "metrics_summary.json"
    if not summary_path.exists():
        return {}
    
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def tail_ndjson_files(run_dir: Path, max_lines: int = 100) -> List[Dict[str, Any]]:
    """
    Tail NDJSON files in order: metrics.ndjson.N (oldest) -> metrics.ndjson (newest).
    
    Returns at most max_lines events from the end.
    """
    events: List[Dict[str, Any]] = []
    
    # Find all metrics.ndjson files
    main_file = run_dir / "metrics.ndjson"
    rotated_files = sorted(
        run_dir.glob("metrics.ndjson.[0-9]*"),
        key=lambda p: int(p.suffix.lstrip("."))
    )
    
    # Read in chronological order: rotated first (oldest), then main (newest)
    all_files = list(rotated_files) + ([main_file] if main_file.exists() else [])
    
    for f in all_files:
        if not f.exists():
            continue
        try:
            with open(f, "r", encoding="utf-8") as fp:
                for line in fp:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass  # Skip malformed lines
        except Exception:
            pass  # Skip unreadable files
    
    # Return tail (most recent)
    return events[-max_lines:] if len(events) > max_lines else events


def render_html(
    summary: Dict[str, Any],
    events: List[Dict[str, Any]],
    run_dir: Path,
) -> str:
    """Render HTML dashboard from summary and events."""
    
    # Extract data
    processed = summary.get("processed", 0)
    allowed = summary.get("allowed", 0)
    rejected = summary.get("rejected", 0)
    filled = summary.get("filled", 0)
    errors = summary.get("errors", 0)
    retries = summary.get("retries", 0)
    dupes_filtered = summary.get("dupes_filtered", 0)
    
    latency_p50 = summary.get("latency_p50_ms", "N/A")
    latency_p95 = summary.get("latency_p95_ms", "N/A")
    latency_count = summary.get("latency_count", 0)
    
    stages = summary.get("stages_by_name", {})
    outcomes = summary.get("outcomes_by_stage", {})
    stage_events_count = summary.get("stage_events_count", 0)
    
    errors_by_reason = summary.get("errors_by_reason", {})
    rejects_by_reason = summary.get("rejects_by_reason", {})
    
    # Build HTML
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"UTF-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
        f"  <title>Metrics Dashboard - {html.escape(str(run_dir.name))}</title>",
        "  <style>",
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }",
        "    .container { max-width: 1200px; margin: 0 auto; }",
        "    h1 { color: #333; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }",
        "    h2 { color: #555; margin-top: 30px; }",
        "    .card { background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "    .stats { display: flex; flex-wrap: wrap; gap: 20px; }",
        "    .stat { text-align: center; min-width: 100px; }",
        "    .stat-value { font-size: 2em; font-weight: bold; color: #4a90d9; }",
        "    .stat-label { color: #666; font-size: 0.9em; }",
        "    table { width: 100%; border-collapse: collapse; margin: 10px 0; }",
        "    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #ddd; }",
        "    th { background: #f8f9fa; font-weight: 600; color: #333; }",
        "    tr:hover { background: #f5f5f5; }",
        "    .ok { color: #28a745; }",
        "    .error { color: #dc3545; }",
        "    .rejected { color: #ffc107; }",
        "    .events-table { font-size: 0.85em; }",
        "    .events-table td { font-family: monospace; }",
        "    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }",
        "    .badge-ok { background: #d4edda; color: #155724; }",
        "    .badge-error { background: #f8d7da; color: #721c24; }",
        "    .badge-rejected { background: #fff3cd; color: #856404; }",
        "    .empty { color: #999; font-style: italic; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <div class=\"container\">",
        f"    <h1>Metrics Dashboard</h1>",
        f"    <p>Run: <strong>{html.escape(str(run_dir))}</strong></p>",
        "",
        "    <!-- Overview Section -->",
        "    <div class=\"card\">",
        "      <h2>Overview</h2>",
        "      <div class=\"stats\">",
        f"        <div class=\"stat\"><div class=\"stat-value\">{processed}</div><div class=\"stat-label\">Processed</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value ok\">{filled}</div><div class=\"stat-label\">Filled</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value\">{allowed}</div><div class=\"stat-label\">Allowed</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value rejected\">{rejected}</div><div class=\"stat-label\">Rejected</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value error\">{errors}</div><div class=\"stat-label\">Errors</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value\">{retries}</div><div class=\"stat-label\">Retries</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value\">{dupes_filtered}</div><div class=\"stat-label\">Dupes</div></div>",
        "      </div>",
        "    </div>",
        "",
        "    <!-- Latency Section -->",
        "    <div class=\"card\">",
        "      <h2>Latency</h2>",
        "      <div class=\"stats\">",
        f"        <div class=\"stat\"><div class=\"stat-value\">{latency_p50}</div><div class=\"stat-label\">P50 (ms)</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value\">{latency_p95}</div><div class=\"stat-label\">P95 (ms)</div></div>",
        f"        <div class=\"stat\"><div class=\"stat-value\">{latency_count}</div><div class=\"stat-label\">Samples</div></div>",
        "      </div>",
        "    </div>",
        "",
        "    <!-- Stages Section -->",
        "    <div class=\"card\">",
        "      <h2>Stages</h2>",
        f"      <p>Total stage events: <strong>{stage_events_count}</strong></p>",
        "      <table>",
        "        <thead>",
        "          <tr><th>Stage</th><th>Count</th><th>P50 (ms)</th><th>P95 (ms)</th><th>Outcomes</th></tr>",
        "        </thead>",
        "        <tbody>",
    ]
    
    if stages:
        for stage_name in sorted(stages.keys()):
            stage_data = stages[stage_name]
            count = stage_data.get("count", 0)
            p50 = stage_data.get("p50_ms", "N/A")
            p95 = stage_data.get("p95_ms", "N/A")
            
            # Get outcomes for this stage
            stage_outcomes = outcomes.get(stage_name, {})
            outcomes_str = ", ".join(f"{k}: {v}" for k, v in sorted(stage_outcomes.items()))
            if not outcomes_str:
                outcomes_str = "-"
            
            html_parts.append(
                f"          <tr><td><strong>{html.escape(stage_name)}</strong></td>"
                f"<td>{count}</td><td>{p50}</td><td>{p95}</td>"
                f"<td>{html.escape(outcomes_str)}</td></tr>"
            )
    else:
        html_parts.append("          <tr><td colspan=\"5\" class=\"empty\">No stage data available</td></tr>")
    
    html_parts.extend([
        "        </tbody>",
        "      </table>",
        "    </div>",
        "",
        "    <!-- Errors/Rejects Section -->",
    ])
    
    if errors_by_reason or rejects_by_reason:
        html_parts.extend([
            "    <div class=\"card\">",
            "      <h2>Errors & Rejections</h2>",
        ])
        
        if errors_by_reason:
            html_parts.append("      <h3>Errors by Reason</h3><table><tbody>")
            for reason, count in sorted(errors_by_reason.items()):
                html_parts.append(f"        <tr><td>{html.escape(reason)}</td><td class=\"error\">{count}</td></tr>")
            html_parts.append("      </tbody></table>")
        
        if rejects_by_reason:
            html_parts.append("      <h3>Rejections by Reason</h3><table><tbody>")
            for reason, count in sorted(rejects_by_reason.items()):
                html_parts.append(f"        <tr><td>{html.escape(reason)}</td><td class=\"rejected\">{count}</td></tr>")
            html_parts.append("      </tbody></table>")
        
        html_parts.append("    </div>")
    
    # Events section
    html_parts.extend([
        "",
        "    <!-- Recent Events Section -->",
        "    <div class=\"card\">",
        f"      <h2>Recent Events ({len(events)} shown)</h2>",
    ])
    
    if events:
        html_parts.extend([
            "      <table class=\"events-table\">",
            "        <thead>",
            "          <tr><th>Stage</th><th>Step ID</th><th>Trace ID</th><th>Outcome</th><th>Δt (ms)</th></tr>",
            "        </thead>",
            "        <tbody>",
        ])
        
        for event in events[-50:]:  # Show last 50 in table
            stage = event.get("stage", "?")
            step_id = event.get("step_id", "?")
            trace_id = event.get("trace_id", "?")
            outcome = event.get("outcome", "?")
            dt = event.get("dt", 0)
            dt_ms = round(dt * 1000, 3) if isinstance(dt, (int, float)) else "?"
            
            outcome_class = "ok" if outcome == "ok" else ("error" if outcome == "error" else "rejected")
            badge_class = f"badge-{outcome_class}"
            
            # Truncate long trace_ids
            trace_short = trace_id[:20] + "..." if len(str(trace_id)) > 20 else trace_id
            
            html_parts.append(
                f"          <tr><td>{html.escape(str(stage))}</td>"
                f"<td>{step_id}</td>"
                f"<td title=\"{html.escape(str(trace_id))}\">{html.escape(str(trace_short))}</td>"
                f"<td><span class=\"badge {badge_class}\">{html.escape(str(outcome))}</span></td>"
                f"<td>{dt_ms}</td></tr>"
            )
        
        html_parts.extend([
            "        </tbody>",
            "      </table>",
        ])
    else:
        html_parts.append("      <p class=\"empty\">No events available</p>")
    
    html_parts.extend([
        "    </div>",
        "",
        "  </div>",
        "</body>",
        "</html>",
    ])
    
    return "\n".join(html_parts)


def main():
    parser = argparse.ArgumentParser(
        description="Render HTML dashboard from metrics files"
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Run directory containing metrics_summary.json and metrics.ndjson"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML file (default: run-dir/dashboard.html)"
    )
    parser.add_argument(
        "--tail-lines",
        type=int,
        default=2000,
        help="Max lines to read from NDJSON files (default: 2000)"
    )
    
    args = parser.parse_args()
    
    run_dir = args.run_dir
    if not run_dir.exists():
        print(f"Error: Run directory does not exist: {run_dir}")
        return 1
    
    out_path = args.out or (run_dir / "dashboard.html")
    
    # Load data
    print(f"Loading metrics from {run_dir}...")
    summary = load_summary(run_dir)
    events = tail_ndjson_files(run_dir, max_lines=args.tail_lines)
    
    print(f"  Summary loaded: {len(summary)} keys")
    print(f"  Events loaded: {len(events)} (max {args.tail_lines})")
    
    # Render HTML
    html_content = render_html(summary, events, run_dir)
    
    # Write output
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Dashboard written to: {out_path}")
    return 0


if __name__ == "__main__":
    exit(main())
