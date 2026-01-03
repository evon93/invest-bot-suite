"""
test_build_dashboard_2I.py

Tests for tools/build_dashboard.py
"""
import pytest
import shutil
import json
import subprocess
import sys
import pandas as pd
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parent.parent / "tools" / "build_dashboard.py"
REPO_ROOT = Path(__file__).resolve().parent.parent

class TestBuildDashboard:

    def test_dashboard_generation(self, tmp_path):
        """
        Verify:
        - Glob expansion finds run dirs.
        - Metrics (active rate, robust metrics) extracted.
        - HTML and JSON artifacts created.
        """
        # Setup Run 1: Standard results.csv with active column and reasons
        run1 = tmp_path / "run1"
        run1.mkdir()
        (run1 / "run_meta.json").write_text('{"mode": "quick"}', encoding="utf-8")
        
        df1 = pd.DataFrame([
            {"is_active": True, "score": 10.0, "param_a": 1, "max_drawdown": -0.1},
            {"is_active": False, "score": 2.0, "param_a": 2, "max_drawdown": -0.2, "rejection_reason": "Low Profit"},
            {"is_active": False, "score": 1.0, "param_a": 3, "max_drawdown": -0.3, "rejection_reason": "Low Profit"},
        ])
        df1.to_csv(run1 / "results.csv", index=False)

        # Setup Run 2: Robust results_agg.csv (no explicit active/reason logic in agg usually, but testing flexibility)
        # Assuming missing active column, dashboard should handle gracefully (active_rate=None or heuristic)
        run2 = tmp_path / "run2"
        run2.mkdir()
        (run2 / "run_meta.json").write_text('{"mode": "robust"}', encoding="utf-8")
        
        df2 = pd.DataFrame([
            {"score_robust": 5.0, "param_x": 10, "max_drawdown": -0.05, "sharpe_ratio": 2.0},
            {"score_robust": 6.0, "param_x": 20, "max_drawdown": -0.10, "sharpe_ratio": 1.5},
        ])
        df2.to_csv(run2 / "results_agg.csv", index=False)

        out_dir = tmp_path / "dashboard_out"

        # Execute
        # Use simple glob pattern matching these dirs
        run_glob = str(tmp_path / "run*")
        
        subprocess.run([sys.executable, str(TOOL_PATH),
                        "--run-dir", run_glob,
                        "--out", str(out_dir)], check=True, cwd=str(REPO_ROOT))

        # Check Artifacts
        summary_json = out_dir / "summary.json"
        index_html = out_dir / "index.html"
        
        assert summary_json.exists()
        assert index_html.exists()

        with open(summary_json, "r") as f:
            data = json.load(f)
            
        assert data["meta"]["n_runs"] == 2
        
        runs = {r["folder_name"]: r for r in data["runs"]}
        
        # Verify Run 1
        r1 = runs.get("run1")
        assert r1 is not None
        assert r1["valid"] is True
        assert r1["n_rows"] == 3
        assert r1["active_rate"] == pytest.approx(1/3) # 1 True out of 3
        # Top reasons: Low Profit count 2
        reasons = dict(r1["top_reasons"])
        assert reasons.get("Low Profit") == 2
        assert r1["metrics"]["worst_dd"] == -0.3

        # Verify Run 2
        r2 = runs.get("run2")
        assert r2 is not None
        assert r2["csv_used"] == "results_agg.csv"
        assert r2["active_rate"] is None # No active col or reasons
        # Robust metric p05_sharpe
        # Sharpe values: 2.0, 1.5. Quantile 0.05 approx 1.525 depending on interpolation, just check existence
        assert "p05_sharpe" in r2["metrics"]

    def test_missing_input_graceful(self, tmp_path):
        """Verify tool handles globs matching nothing or empty dirs gracefully."""
        out_dir = tmp_path / "dash_empty"
        
        # Glob matches nothing
        subprocess.run([sys.executable, str(TOOL_PATH),
                        "--run-dir", str(tmp_path / "non_existent_*"),
                        "--out", str(out_dir)], check=True, cwd=str(REPO_ROOT))
        
        # Should produce empty dashboard
        with open(out_dir / "summary.json", "r") as f:
            data = json.load(f)
        assert data["meta"]["n_runs"] == 0
