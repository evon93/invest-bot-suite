import pytest
import subprocess
import sys
import os
from pathlib import Path

# Asumimos que el script está en tools/run_e2e_2J.py
SCRIPT_PATH = Path("tools/run_e2e_2J.py")

class TestE2ERunner2J:
    """ Tests for the 2J E2E Runner CLI """

    def test_help(self):
        """ Verify help command functionality """
        cmd = [sys.executable, str(SCRIPT_PATH), "--help"]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)
        assert result.returncode == 0, f"CMD failed: {result.stderr}"
        assert "--mode" in result.stdout
        assert "{quick,full}" in result.stdout

    def test_mode_quick_dry_run(self):
        """ Verify quick mode maps to correct calibration args """
        cmd = [sys.executable, str(SCRIPT_PATH), "--mode", "quick", "--dry-run"]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)
        assert result.returncode == 0, f"CMD failed: {result.stderr}"
        # Check if calibration call uses --mode quick
        assert "tools/run_calibration_2B.py" in result.stdout
        assert "--mode quick" in result.stdout

    def test_mode_full_dry_run(self):
        """ Verify full mode maps to full_demo """
        # full debe mapearse a full_demo segun el contrato 3B.1
        cmd = [sys.executable, str(SCRIPT_PATH), "--mode", "full", "--dry-run"]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)
        assert result.returncode == 0, f"CMD failed: {result.stderr}"
        assert "tools/run_calibration_2B.py" in result.stdout
        assert "--mode full_demo" in result.stdout
