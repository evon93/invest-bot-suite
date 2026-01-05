"""
tests/test_3E_determinism_gate.py

Wrapper test for tools/check_determinism_3E.py
"""

import subprocess
import sys
import pytest
from pathlib import Path

CHECKER_PATH = Path('tools/check_determinism_3E.py')

def test_determinism_3E(tmp_path):
    """Run determinism checker with temp dirs."""
    
    dir_a = tmp_path / "run_a"
    dir_b = tmp_path / "run_b"
    
    cmd = [
        sys.executable, str(CHECKER_PATH),
        "--outdir-a", str(dir_a),
        "--outdir-b", str(dir_b),
        "--seed", "42",
        "--clock", "simulated",
        "--exchange", "paper"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
    assert result.returncode == 0, f"Determinism checker failed: {result.stdout}"
