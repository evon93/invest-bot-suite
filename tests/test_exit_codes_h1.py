"""
tests/test_exit_codes_h1.py

Test exit code semantics (AG-H1-2-1):
- Exit code 0: Controlled shutdown (SIGINT/SIGTERM)
- Exit code != 0: Real failures (invalid config, exceptions)

Subprocess-based tests for run_live_3E.py.
"""

import sys
import os
import time
import signal
import subprocess
import pytest
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


class TestExitCodeFailures:
    """Test that real failures exit with non-zero code."""
    
    def test_missing_fixture_path_exits_nonzero(self):
        """
        Test that --data fixture without --fixture-path exits with error.
        Expected: exit code 2 (argparse error)
        """
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--data", "fixture",
            # Missing --fixture-path should trigger parser.error()
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Should fail - argparse error
        assert result.returncode != 0, (
            f"Expected non-zero exit for missing fixture-path, got {result.returncode}\n"
            f"STDERR: {result.stderr}"
        )
    
    def test_nonexistent_fixture_exits_nonzero(self, tmp_path):
        """
        Test that --fixture-path with nonexistent file exits with error.
        Expected: exit code != 0 (FileNotFoundError)
        """
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--data", "fixture",
            "--fixture-path", "/nonexistent/path/data.csv",
            "--outdir", str(tmp_path),
            "--max-steps", "1",
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # Should fail - file not found
        assert result.returncode != 0, (
            f"Expected non-zero exit for nonexistent fixture, got {result.returncode}\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )



class TestExitCodeControlledShutdown:
    """Test that controlled shutdown exits with code 0."""
    
    @pytest.mark.skipif(IS_WINDOWS, reason="SIGINT handling differs on Windows")
    def test_sigint_exits_zero(self, tmp_path):
        """
        Test that SIGINT (Ctrl+C) causes graceful shutdown with exit 0.
        Reuses pattern from test_graceful_shutdown_signal_3O2.py.
        """
        run_dir = tmp_path / "run_sigint_h1"
        run_dir.mkdir()
        
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--outdir", str(run_dir),
            "--run-dir", str(run_dir),
            "--preset", "paper_ci_100bars",
            "--max-steps", "1000",
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
            # Wait for startup (run_meta.json created)
            start = time.time()
            while time.time() - start < 15:
                if (run_dir / "run_meta.json").exists():
                    break
                time.sleep(0.2)
            else:
                proc.kill()
                stdout, stderr = proc.communicate()
                pytest.fail(f"Startup timeout.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            
            # Let it run a bit
            time.sleep(1)
            
            # Send SIGINT
            proc.send_signal(signal.SIGINT)
            
            # Wait for exit
            return_code = proc.wait(timeout=15)
            
            # Verify controlled shutdown = exit 0
            assert return_code == 0, f"Expected exit 0 on SIGINT, got {return_code}"
            
        finally:
            if proc.poll() is None:
                proc.kill()
    
    @pytest.mark.skipif(IS_WINDOWS, reason="SIGTERM is hard-kill on Windows")
    def test_sigterm_exits_zero(self, tmp_path):
        """
        Test that SIGTERM causes graceful shutdown with exit 0.
        """
        run_dir = tmp_path / "run_sigterm_h1"
        run_dir.mkdir()
        
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--outdir", str(run_dir),
            "--run-dir", str(run_dir),
            "--preset", "paper_ci_100bars",
            "--max-steps", "1000",
            "--seed", "42",
        ]
        
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
        )
        
        try:
            # Wait for startup
            start = time.time()
            while time.time() - start < 15:
                if (run_dir / "run_meta.json").exists():
                    break
                time.sleep(0.2)
            else:
                proc.kill()
                pytest.fail("Startup timeout")
            
            time.sleep(1)
            
            # Send SIGTERM
            proc.terminate()
            
            return_code = proc.wait(timeout=15)
            
            assert return_code == 0, f"Expected exit 0 on SIGTERM, got {return_code}"
            
        finally:
            if proc.poll() is None:
                proc.kill()


class TestExitCodeNormalCompletion:
    """Test that normal completion exits with code 0."""
    
    def test_normal_run_exits_zero(self, tmp_path):
        """
        Test that a normal short run exits with code 0.
        """
        run_dir = tmp_path / "run_normal_h1"
        run_dir.mkdir()
        
        cmd = [
            sys.executable,
            "tools/run_live_3E.py",
            "--outdir", str(run_dir),
            "--max-steps", "5",
            "--seed", "42",
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        assert result.returncode == 0, (
            f"Expected exit 0 on normal completion, got {result.returncode}\n"
            f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )
        
        # Verify artifacts created
        assert (run_dir / "run_meta.json").exists()
        assert (run_dir / "events.ndjson").exists()
