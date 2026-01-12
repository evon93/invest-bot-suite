"""
tests/test_run_live_3E_smoke_3J4.py

Smoke tests for run_live_3E with Strategy v0.8 (AG-3J-4-1).

Validates:
- CLI runs with --strategy v0_8 without error
- Artifacts are generated (events.ndjson, run_meta.json, etc.)
- Exit code is 0
"""

import pytest
import subprocess
import json
import sys
from pathlib import Path

# Project root for subprocess calls
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPT_PATH = PROJECT_ROOT / "tools" / "run_live_3E.py"


def run_live_3e(*extra_args):
    """Helper to run run_live_3E.py."""
    cmd = [sys.executable, str(SCRIPT_PATH)] + list(extra_args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=60,  # Max 60 seconds
    )


class TestRunLive3ESmoke:
    """Smoke tests for run_live_3E.py with Strategy v0.8."""

    def test_smoke_v0_8_runs_successfully(self, tmp_path: Path):
        """Smoke test with --strategy v0_8 should exit 0."""
        outdir = tmp_path / "smoke_v08"
        
        result = run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--max-steps", "30",
            "--clock", "simulated",
            "--exchange", "paper",
        )
        
        assert result.returncode == 0, f"Smoke failed: {result.stderr}"

    def test_smoke_generates_events_ndjson(self, tmp_path: Path):
        """Smoke should generate events.ndjson."""
        outdir = tmp_path / "smoke_v08"
        
        run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--max-steps", "30",
        )
        
        events_path = outdir / "events.ndjson"
        assert events_path.exists(), "events.ndjson not created"
        assert events_path.stat().st_size > 0, "events.ndjson is empty"

    def test_smoke_generates_run_meta(self, tmp_path: Path):
        """Smoke should generate run_meta.json."""
        outdir = tmp_path / "smoke_v08"
        
        run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--max-steps", "30",
        )
        
        meta_path = outdir / "run_meta.json"
        assert meta_path.exists(), "run_meta.json not created"
        
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["strategy"] == "v0_8"
        assert meta["seed"] == 42

    def test_smoke_generates_results_csv(self, tmp_path: Path):
        """Smoke should generate results.csv."""
        outdir = tmp_path / "smoke_v08"
        
        run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--max-steps", "30",
        )
        
        results_path = outdir / "results.csv"
        assert results_path.exists(), "results.csv not created"

    def test_smoke_v0_7_also_works(self, tmp_path: Path):
        """Smoke with v0_7 should also work for comparison."""
        outdir = tmp_path / "smoke_v07"
        
        result = run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_7",
            "--seed", "42",
            "--max-steps", "30",
        )
        
        assert result.returncode == 0, f"v0_7 smoke failed: {result.stderr}"
        
        meta_path = outdir / "run_meta.json"
        with open(meta_path, "r") as f:
            meta = json.load(f)
        
        assert meta["strategy"] == "v0_7"

    def test_smoke_runtime_under_15_seconds(self, tmp_path: Path):
        """Smoke test should complete in under 15 seconds."""
        import time
        
        outdir = tmp_path / "smoke_timing"
        
        start = time.perf_counter()
        result = run_live_3e(
            "--outdir", str(outdir),
            "--strategy", "v0_8",
            "--seed", "42",
            "--max-steps", "50",
        )
        elapsed = time.perf_counter() - start
        
        assert result.returncode == 0
        assert elapsed < 15, f"Smoke took {elapsed:.1f}s, expected < 15s"
