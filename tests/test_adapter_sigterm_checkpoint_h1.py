"""
tests/test_adapter_sigterm_checkpoint_h1.py

Test SIGTERM in adapter-mode saves checkpoint (AG-H1-3-1).

Validates:
1. run_live_3E.py in adapter-mode exits 0 on SIGTERM
2. checkpoint.json exists and has content after SIGTERM
"""

import os
import sys
import time
import json
import signal
import subprocess
import pytest
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
PROJECT_ROOT = Path(__file__).parent.parent


def wait_for_ready(run_dir: Path, timeout_s: int = 15) -> bool:
    """Wait for run to be ready (run_meta.json created)."""
    start = time.time()
    while time.time() - start < timeout_s:
        if (run_dir / "run_meta.json").exists():
            return True
        time.sleep(0.2)
    return False


def find_fixture_csv() -> Path:
    """Find a suitable fixture CSV for adapter-mode test."""
    # Look for existing fixtures
    fixtures_dir = PROJECT_ROOT / "fixtures"
    if fixtures_dir.exists():
        csvs = list(fixtures_dir.glob("*.csv"))
        if csvs:
            return csvs[0]
    
    # Look in data/ or tests/data/
    for candidate in [
        PROJECT_ROOT / "data" / "ohlcv_sample.csv",
        PROJECT_ROOT / "tests" / "data" / "ohlcv_fixture.csv",
        PROJECT_ROOT / "tests" / "fixtures" / "ohlcv_sample.csv",
    ]:
        if candidate.exists():
            return candidate
    
    return None


class TestAdapterSigtermCheckpoint:
    """Test SIGTERM handling in adapter-mode."""
    
    @pytest.fixture
    def fixture_csv(self, tmp_path) -> Path:
        """Create or find a fixture CSV for testing."""
        existing = find_fixture_csv()
        if existing:
            return existing
        
        # Create minimal fixture CSV
        csv_path = tmp_path / "test_fixture.csv"
        import pandas as pd
        import numpy as np
        
        np.random.seed(42)
        n_bars = 100
        dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
        closes = 1000 * np.cumprod(1 + np.random.randn(n_bars) * 0.01)
        
        df = pd.DataFrame({
            "timestamp": dates,
            "open": closes * 0.999,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": np.random.randint(100, 1000, n_bars),
        })
        df.to_csv(csv_path, index=False)
        return csv_path
    
    @pytest.mark.skipif(IS_WINDOWS, reason="SIGTERM is hard-kill on Windows")
    def test_sigterm_adapter_mode_exits_zero_and_checkpoints(self, tmp_path, fixture_csv):
        """
        Test that SIGTERM in adapter-mode:
        1. Exits with code 0 (graceful shutdown)
        2. Saves checkpoint.json to run_dir
        """
        run_dir = tmp_path / "adapter_sigterm_run"
        run_dir.mkdir()
        
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--data", "fixture",
            "--data-mode", "adapter",
            "--fixture-path", str(fixture_csv),
            "--outdir", str(run_dir),
            "--run-dir", str(run_dir),
            "--max-steps", "500",
            "--seed", "42",
        ]
        
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        try:
            # Wait for startup
            if not wait_for_ready(run_dir):
                proc.kill()
                stdout, stderr = proc.communicate()
                pytest.fail(f"Startup timeout.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            
            # Let it process some steps
            time.sleep(2)
            
            # Send SIGTERM
            proc.terminate()
            
            # Wait for exit
            try:
                return_code = proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                pytest.fail("Process did not exit within timeout after SIGTERM")
            
            stdout, stderr = proc.communicate()
            
            # Assert exit code 0
            assert return_code == 0, (
                f"Expected exit 0 on SIGTERM, got {return_code}\n"
                f"STDOUT: {stdout}\nSTDERR: {stderr}"
            )
            
            # Assert checkpoint exists
            checkpoint_path = run_dir / "checkpoint.json"
            assert checkpoint_path.exists(), (
                f"checkpoint.json not found in {run_dir}\n"
                f"Contents: {list(run_dir.iterdir())}"
            )
            
            # Validate checkpoint content
            with open(checkpoint_path) as f:
                ckpt = json.load(f)
            
            assert "run_id" in ckpt, "checkpoint missing run_id"
            assert "last_processed_idx" in ckpt, "checkpoint missing last_processed_idx"
            # Should have processed at least some steps
            assert ckpt["last_processed_idx"] >= 0, "last_processed_idx should be >= 0"
            
        finally:
            if proc.poll() is None:
                proc.kill()
    
    @pytest.mark.skipif(IS_WINDOWS, reason="SIGINT handling differs on Windows")
    def test_sigint_adapter_mode_exits_zero(self, tmp_path, fixture_csv):
        """
        Test that SIGINT (Ctrl+C) in adapter-mode exits with code 0.
        """
        run_dir = tmp_path / "adapter_sigint_run"
        run_dir.mkdir()
        
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--data", "fixture",
            "--data-mode", "adapter",
            "--fixture-path", str(fixture_csv),
            "--outdir", str(run_dir),
            "--run-dir", str(run_dir),
            "--max-steps", "500",
            "--seed", "42",
        ]
        
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
        )
        
        try:
            if not wait_for_ready(run_dir):
                proc.kill()
                pytest.fail("Startup timeout")
            
            time.sleep(1)
            
            # Send SIGINT
            proc.send_signal(signal.SIGINT)
            
            return_code = proc.wait(timeout=15)
            
            assert return_code == 0, f"Expected exit 0 on SIGINT, got {return_code}"
            assert (run_dir / "checkpoint.json").exists()
            
        finally:
            if proc.poll() is None:
                proc.kill()
