"""
test_realdata_smoke_2F.py — Optional smoke test with real OHLCV data

Requires INVESTBOT_REALDATA_PATH environment variable to be set.
Skips gracefully if not present, ensuring CI stays green.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.realdata
class TestRealDataSmoke:
    """Smoke tests using real OHLCV data (optional)."""

    @pytest.fixture
    def realdata_path(self):
        """Get realdata path from env, skip if not set."""
        path = os.environ.get("INVESTBOT_REALDATA_PATH")
        if not path:
            pytest.skip("INVESTBOT_REALDATA_PATH not set")
        if not Path(path).exists():
            pytest.skip(f"INVESTBOT_REALDATA_PATH file not found: {path}")
        return path

    def test_smoke_runner_no_crash(self, realdata_path, tmp_path):
        """Runner executes without crash and produces outputs."""
        outdir = tmp_path / "smoke_out"
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "run_realdata_smoke_2F.py"),
                "--path", realdata_path,
                "--outdir", str(outdir),
                "--max-rows", "2000",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        if result.returncode != 0:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        # Check outputs exist
        assert (outdir / "results.json").exists()
        assert (outdir / "run_meta.json").exists()

    def test_metrics_not_nan(self, realdata_path, tmp_path):
        """Metrics should not be NaN."""
        import math
        
        outdir = tmp_path / "smoke_metrics"
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "run_realdata_smoke_2F.py"),
                "--path", realdata_path,
                "--outdir", str(outdir),
                "--max-rows", "2000",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        assert result.returncode == 0
        
        with open(outdir / "results.json", "r", encoding="utf-8") as f:
            results = json.load(f)
        
        metrics = results["metrics"]
        assert not math.isnan(metrics["total_return"]), "total_return is NaN"
        assert not math.isnan(metrics["max_drawdown"]), "max_drawdown is NaN"

    def test_run_meta_has_data_source(self, realdata_path, tmp_path):
        """run_meta.json should contain data_source='realdata'."""
        outdir = tmp_path / "smoke_meta"
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "run_realdata_smoke_2F.py"),
                "--path", realdata_path,
                "--outdir", str(outdir),
                "--max-rows", "2000",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        
        assert result.returncode == 0
        
        with open(outdir / "run_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        assert meta.get("data_source") == "realdata"
        assert "realdata_path" in meta
        assert "n_rows" in meta


@pytest.mark.realdata
class TestRealDataSkipBehavior:
    """Verify skip behavior when env var not set."""

    def test_skip_when_no_env_var(self):
        """This test should skip if INVESTBOT_REALDATA_PATH is not set."""
        path = os.environ.get("INVESTBOT_REALDATA_PATH")
        if not path:
            pytest.skip("Expected: INVESTBOT_REALDATA_PATH not set")
        # If we get here, the env var is set, so we pass
        assert True
