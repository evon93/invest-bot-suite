"""
tests/test_graceful_shutdown_supervisor_3O2.py

Test graceful shutdown of Supervisor + Child (AG-3O-2-2).
Verifies that:
1. Supervisor starts child (run_live_3E.py).
2. Supervisor handles SIGTERM.
3. Supervisor instructs child to stop (or child receives signal).
4. Both exit cleanly with code 0.
"""

import sys
import os
import time
import signal
import shutil
import subprocess
import pytest
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

IS_WINDOWS = sys.platform == "win32"

def wait_for_ready(run_dir: Path, timeout_s: int = 15) -> bool:
    """Wait for run to be ready (meta or checkpoint created)."""
    start = time.time()
    while time.time() - start < timeout_s:
        # Check inside the sub-run-dir created by supervisor?
        # Supervisor invocation: --run-dir <dir>
        # RunLive invocation: --run-dir <dir>
        # So meta should be in <dir>/run_meta.json
        if (run_dir / "run_meta.json").exists():
            return True
        time.sleep(0.5)
    return False

def test_supervisor_graceful_sigterm(tmp_path):
    """
    Test Supervisor receiving SIGTERM shuts down child gracefully.
    """
    if IS_WINDOWS:
        pytest.skip("SIGTERM is hard-kill on Windows, skipping graceful test")

    # CI support
    base_dir = tmp_path
    if "INVESTBOT_ARTIFACT_DIR" in os.environ:
        base_dir = Path(os.environ["INVESTBOT_ARTIFACT_DIR"])
        base_dir.mkdir(parents=True, exist_ok=True)
    
    supervisor_dir = base_dir / "sup_sigterm"
    if supervisor_dir.exists():
        shutil.rmtree(supervisor_dir)
    supervisor_dir.mkdir(parents=True, exist_ok=True)
    
    # Command: python tools/supervisor_live_3E_3H.py --run-dir <dir> -- python tools/run_live_3E.py ...
    
    run_live_cmd = [
        sys.executable, "tools/run_live_3E.py",
        "--outdir", str(supervisor_dir), # legacy arg, mapped to run_dir usually
        "--run-dir", str(supervisor_dir),
        "--preset", "paper_ci_100bars",
        "--max-steps", "1000",
        "--seed", "42"
    ]
    
    supervisor_cmd = [
        sys.executable, "tools/supervisor_live_3E_3H.py",
        "--run-dir", str(supervisor_dir),
        "--",
    ] + run_live_cmd
    
    # Start Supervisor
    proc = subprocess.Popen(
        supervisor_cmd,
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for readiness
        if not wait_for_ready(supervisor_dir):
            proc.kill()
            stdout, stderr = proc.communicate()
            pytest.fail(f"Timeout waiting for startup.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            
        time.sleep(2) # Process some bars
        
        # Send SIGTERM to Supervisor
        print("Sending SIGTERM to Supervisor...")
        proc.terminate()
        
        # Wait for exit
        try:
            return_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Supervisor did not exit within timeout")
            
        assert return_code == 0, f"Supervisor exited with {return_code} instead of 0"
        
        # Check artifacts
        assert (supervisor_dir / "checkpoint.json").exists(), "Child checkpoint missing"
        assert (supervisor_dir / "supervisor_state.json").exists(), "Supervisor state missing"
        
    finally:
        if proc.poll() is None:
            proc.kill()
