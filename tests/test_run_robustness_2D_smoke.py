"""
tests/test_run_robustness_2D_smoke.py

Smoke tests for the robustness 2D runner.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Add project root to path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# =============================================================================
# Smoke Test: Quick mode with 2 scenarios
# =============================================================================

def test_runner_smoke_quick_mode():
    """
    Smoke test: Run robustness 2D in quick mode with max 2 scenarios.
    Verify outputs are created and results.csv has at least 1 row.
    Should complete in <10s.
    """
    from tools.run_robustness_2D import run_robustness
    
    config_path = ROOT / "configs" / "robustness_2D.yaml"
    
    # Use temp directory for output
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        # Run with max 2 scenarios
        meta = run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir,
            max_scenarios_override=2,
        )
        
        # Check meta
        assert meta is not None
        assert meta["scenarios_total"] >= 1
        assert meta["scenarios_total"] <= 2
        assert "pass_rate" in meta
        
        # Check files exist
        results_csv = outdir / "results.csv"
        summary_md = outdir / "summary.md"
        run_meta_json = outdir / "run_meta.json"
        
        assert results_csv.exists(), "results.csv not created"
        assert summary_md.exists(), "summary.md not created"
        assert run_meta_json.exists(), "run_meta.json not created"
        
        # Check results.csv has at least 1 data row
        lines = results_csv.read_text().strip().split("\n")
        assert len(lines) >= 2, "results.csv should have header + at least 1 row"
        
        # Check run_meta.json is valid JSON
        meta_data = json.loads(run_meta_json.read_text())
        assert "mode" in meta_data
        assert meta_data["mode"] == "quick"
        assert "scenarios_total" in meta_data


def test_runner_outputs_match_spec():
    """
    Verify output files match the spec layout.
    """
    from tools.run_robustness_2D import run_robustness
    
    config_path = ROOT / "configs" / "robustness_2D.yaml"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir,
            max_scenarios_override=1,
        )
        
        # Spec requires: results.csv, summary.md, run_meta.json, errors.jsonl
        assert (outdir / "results.csv").exists()
        assert (outdir / "summary.md").exists()
        assert (outdir / "run_meta.json").exists()
        assert (outdir / "errors.jsonl").exists()


def test_runner_results_csv_columns():
    """
    Verify results.csv has expected columns per spec.
    """
    from tools.run_robustness_2D import run_robustness
    import csv
    
    config_path = ROOT / "configs" / "robustness_2D.yaml"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir,
            max_scenarios_override=1,
        )
        
        # Read CSV headers
        results_csv = outdir / "results.csv"
        with open(results_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
        
        # Required columns per spec
        required_columns = [
            "scenario_id",
            "mode",
            "seed",
            "sharpe_ratio",
            "cagr",
            "max_drawdown",
            "score",
            "gate_pass",
            "duration_seconds",
        ]
        
        for col in required_columns:
            assert col in headers, f"Missing required column: {col}"


def test_runner_deterministic_scenario_ids():
    """
    Verify scenario IDs are deterministic (same config = same IDs).
    """
    from tools.run_robustness_2D import run_robustness
    import csv
    
    config_path = ROOT / "configs" / "robustness_2D.yaml"
    
    # Run twice
    ids_run1 = []
    ids_run2 = []
    
    with tempfile.TemporaryDirectory() as tmpdir1:
        outdir1 = Path(tmpdir1)
        run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir1,
            max_scenarios_override=2,
        )
        with open(outdir1 / "results.csv", "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ids_run1.append(row["scenario_id"])
    
    with tempfile.TemporaryDirectory() as tmpdir2:
        outdir2 = Path(tmpdir2)
        run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir2,
            max_scenarios_override=2,
        )
        with open(outdir2 / "results.csv", "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ids_run2.append(row["scenario_id"])
    
    # Same order, same IDs
    assert ids_run1 == ids_run2, "Scenario IDs should be deterministic"


def test_runner_gate_check():
    """
    Verify gate checking works (some scenarios may fail gates).
    """
    from tools.run_robustness_2D import run_robustness
    import csv
    
    config_path = ROOT / "configs" / "robustness_2D.yaml"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        outdir = Path(tmpdir)
        
        meta = run_robustness(
            config_path=config_path,
            mode="quick",
            outdir_override=outdir,
            max_scenarios_override=3,
        )
        
        # Read results
        with open(outdir / "results.csv", "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        
        # All rows should have gate_pass field
        for row in rows:
            assert "gate_pass" in row
            assert row["gate_pass"] in ("True", "False", True, False)
        
        # Meta should report passed/failed counts
        assert meta["scenarios_passed"] + meta["scenarios_failed"] + meta["scenarios_error"] == meta["scenarios_total"]
