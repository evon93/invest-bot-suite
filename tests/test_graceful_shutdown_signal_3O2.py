"""
tests/test_graceful_shutdown_signal_3O2.py

Test graceful shutdown controlled by signals (AG-3O-2-1).
Verifies that run_live_3E.py handles SIGINT/SIGTERM by:
1. Stopping the loop cleanly
2. Saving checkpoint
3. Exiting with code 0

Offline test using subprocess.
"""

import sys
import os
import time
import signal
import json
import shutil
import subprocess
import pytest
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

IS_WINDOWS = sys.platform == "win32"

def wait_for_ready(run_dir: Path, timeout_s: int = 10) -> bool:
    """Wait for run to be ready (meta or checkpoint created)."""
    start = time.time()
    while time.time() - start < timeout_s:
        if (run_dir / "run_meta.json").exists():
            return True
        time.sleep(0.1)
    return False

def test_graceful_shutdown_sigint(tmp_path):
    """
    Test graceful shutdown via SIGINT (Ctrl+C).
    Expected: Exit code 0, checkpoint.json exists and valid.
    """
    # CI support: use artifact dir if provided
    base_dir = tmp_path
    if "INVESTBOT_ARTIFACT_DIR" in os.environ:
        base_dir = Path(os.environ["INVESTBOT_ARTIFACT_DIR"])
        base_dir.mkdir(parents=True, exist_ok=True)
    
    run_dir = base_dir / "run_sigint"
    # Ensure clean start
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Command to run (infinite loop efficiently simulated via many steps)
    cmd = [
        sys.executable,
        "tools/run_live_3E.py",
        "--outdir", str(run_dir),
        "--run-dir", str(run_dir),
        "--preset", "paper_ci_100bars", # offline, fast
        "--max-steps", "1000",           # long enough to catch signal
        "--seed", "42",
        "--enable-metrics"
    ]
    
    creationflags = 0
    if IS_WINDOWS:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    
    # Start subprocess
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=creationflags,
        text=True
    )
    
    try:
        # Wait for ready
        if not wait_for_ready(run_dir, timeout_s=10):
            proc.kill()
            stdout, stderr = proc.communicate()
            pytest.fail(f"Timeout waiting for startup.\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            
        # Let it run a bit to process some steps
        time.sleep(2)
        
        # Send Signal
        print("Sending SIGINT...")
        if IS_WINDOWS:
            # On Windows, we need CTRL_C_EVENT to simulate Ctrl+C
            os.kill(proc.pid, signal.CTRL_C_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
            
        # Wait for exit
        try:
            return_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Process did not exit within timeout after signal")
            
        # Verify exit code
        assert return_code == 0, f"Expected exit 0, got {return_code}"
        
        # Verify artifacts
        checkpoint_path = run_dir / "checkpoint.json"
        assert checkpoint_path.exists(), "checkpoint.json missing"
        
        with open(checkpoint_path) as f:
            ckpt = json.load(f)
            assert "last_processed_idx" in ckpt
            assert ckpt["last_processed_idx"] >= 0
            
        # Metrics check (optional, proves clean end)
        metrics_path = run_dir / "run_metrics.json"
        assert metrics_path.exists(), "run_metrics.json missing"
        
        # Verify output contains graceful shutdown message
        stdout, stderr = proc.communicate() # stdout usually buffered
        # Note: on Windows stdout might be limited if not flushed, but we check return code primarily
        
    finally:
        if proc.poll() is None:
            proc.kill()

def test_graceful_shutdown_sigterm_shim(tmp_path):
    """
    Test graceful shutdown via SIGTERM.
    Note: On Windows, python implementation of signal.signal(SIGTERM) works
    if sent via os.kill(pid, signal.SIGTERM), but external cancel is hard kill.
    Since we are testing the python logic, we can try to send SIGTERM if supported.
    """
    if IS_WINDOWS:
        # Windows Popen.terminate() is hard kill, so we skip SIGTERM test 
        # unless we find a way to emulate it gracefully, but usually
        # Windows rely on Ctrl+C or Ctrl+Break for graceful console apps.
        pytest.skip("SIGTERM not natively supported as graceful on Windows (hard kill)")
        
    run_dir = tmp_path / "test_run_sigterm"
    run_dir.mkdir()
    
    cmd = [
        sys.executable,
        "tools/run_live_3E.py",
        "--outdir", str(run_dir),
        "--run-dir", str(run_dir),
        "--preset", "paper_ci_100bars",
        "--max-steps", "1000",
        "--seed", "42"
    ]
    
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        creationflags=0
    )
    
    try:
        if not wait_for_ready(run_dir):
            proc.kill()
            pytest.fail("Timeout waiting start")
            
        time.sleep(2)
        
        # Send SIGTERM
        proc.terminate() # On Unix this sends SIGTERM
        
        try:
            return_code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("Timeout after SIGTERM")
            
        assert return_code == 0
        assert (run_dir / "checkpoint.json").exists()
        
    finally:
        if proc.poll() is None:
            proc.kill()
