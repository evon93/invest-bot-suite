"""
tests/test_strategy_validation_runner_3J3.py

Tests for offline strategy validation harness (AG-3J-3-1).

Validates:
- Script runs without error
- All 3 artifacts are generated (signals.ndjson, metrics_summary.json, run_meta.json)
- Artifacts are not empty
- Artifacts have expected structure
"""

import pytest
import subprocess
import json
import sys
from pathlib import Path

# Project root for subprocess calls
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPT_PATH = PROJECT_ROOT / "tools" / "run_strategy_validation_3J.py"


def run_script(*extra_args):
    """Helper to run the validation script."""
    cmd = [sys.executable, str(SCRIPT_PATH)] + list(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )


class TestStrategyValidationRunner:
    """Tests for run_strategy_validation_3J.py script."""

    def test_runner_generates_artifacts(self, tmp_path: Path):
        """Script should generate all 3 required artifacts."""
        outdir = tmp_path / "validation_run"
        
        result = run_script(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--n-bars", "50",
        )
        
        # Check script succeeded
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        
        # Check all artifacts exist
        signals_path = outdir / "signals.ndjson"
        metrics_path = outdir / "metrics_summary.json"
        meta_path = outdir / "run_meta.json"
        
        assert signals_path.exists(), "signals.ndjson not created"
        assert metrics_path.exists(), "metrics_summary.json not created"
        assert meta_path.exists(), "run_meta.json not created"

    def test_run_meta_has_expected_fields(self, tmp_path: Path):
        """run_meta.json should have expected fields."""
        outdir = tmp_path / "validation_run"
        
        run_script("--outdir", str(outdir), "--strategy", "v0_8", "--seed", "42")
        
        meta_path = outdir / "run_meta.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        expected_fields = [
            "strategy", "seed", "n_bars", "fast_period", 
            "slow_period", "ticker", "asof_ts", "total_signals"
        ]
        
        for field in expected_fields:
            assert field in meta, f"Missing field: {field}"
        
        assert meta["strategy"] == "v0_8"
        assert meta["seed"] == 42

    def test_metrics_summary_structure(self, tmp_path: Path):
        """metrics_summary.json should have expected structure."""
        outdir = tmp_path / "validation_run"
        
        run_script("--outdir", str(outdir))
        
        metrics_path = outdir / "metrics_summary.json"
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        
        assert "total_signals" in metrics
        assert "buy_signals" in metrics
        assert "sell_signals" in metrics
        assert isinstance(metrics["total_signals"], int)

    def test_signals_ndjson_format(self, tmp_path: Path):
        """signals.ndjson should be valid NDJSON."""
        outdir = tmp_path / "validation_run"
        
        run_script("--outdir", str(outdir), "--n-bars", "100")
        
        signals_path = outdir / "signals.ndjson"
        
        # Read and validate NDJSON
        signals = []
        with open(signals_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    event = json.loads(line)
                    signals.append(event)
        
        # Check structure if signals exist
        if signals:
            first = signals[0]
            assert "event_type" in first
            assert "symbol" in first
            assert "side" in first
            assert first["side"] in ("BUY", "SELL")

    def test_determinism_same_seed_same_output(self, tmp_path: Path):
        """Same seed should produce identical results."""
        outdir1 = tmp_path / "run1"
        outdir2 = tmp_path / "run2"
        
        run_script("--outdir", str(outdir1), "--seed", "42", "--n-bars", "50")
        run_script("--outdir", str(outdir2), "--seed", "42", "--n-bars", "50")
        
        # Compare metrics
        with open(outdir1 / "metrics_summary.json") as f:
            metrics1 = json.load(f)
        with open(outdir2 / "metrics_summary.json") as f:
            metrics2 = json.load(f)
        
        assert metrics1 == metrics2, "Same seed should produce identical metrics"

    def test_v0_7_strategy_also_works(self, tmp_path: Path):
        """Script should also work with v0_7 strategy."""
        outdir = tmp_path / "v07_run"
        
        result = run_script("--outdir", str(outdir), "--strategy", "v0_7")
        
        assert result.returncode == 0, f"v0_7 run failed: {result.stderr}"
        
        meta_path = outdir / "run_meta.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["strategy"] == "v0_7"
