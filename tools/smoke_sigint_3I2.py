#!/usr/bin/env python3
"""
tools/smoke_sigint_3I2.py

Smoke test for graceful shutdown (AG-3I-2-1).

Demonstrates:
- StopController idempotent behavior
- Supervisor stops cleanly on pre-set stop
- No traceback on shutdown

NOT for commit - only for smoke verification.
"""

import sys
import tempfile
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from supervisor_live_3E_3H import Supervisor, StopController


def main():
    print("=== AG-3I-2-1 Smoke Test: Graceful Shutdown ===\n")
    
    # Test 1: StopController idempotent
    print("Test 1: StopController idempotent behavior")
    ctrl = StopController()
    print(f"  Initial: is_stop_requested={ctrl.is_stop_requested}, reason={ctrl.stop_reason}")
    
    ctrl.request_stop("SIGINT")
    print(f"  After request_stop('SIGINT'): reason={ctrl.stop_reason}")
    
    ctrl.request_stop("SIGTERM")
    ctrl.request_stop("manual")
    print(f"  After 2 more requests: reason={ctrl.stop_reason} (should still be SIGINT)")
    
    assert ctrl.stop_reason == "SIGINT", "First reason should win"
    print("  PASS: First reason wins\n")
    
    # Test 2: Supervisor stops before starting child
    print("Test 2: Supervisor pre-stop shutdown")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        stop_ctrl = StopController()
        stop_ctrl.request_stop("pre_start_stop")
        
        run_count = [0]
        def mock_run(cmd):
            run_count[0] += 1
            return 0
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["echo", "hello"],
            run_fn=mock_run,
            stop_controller=stop_ctrl,
        )
        
        result = supervisor.run()
        
        print(f"  Exit code: {result} (expected: 0)")
        print(f"  Child runs: {run_count[0]} (expected: 0)")
        
        assert result == 0, "Should exit cleanly"
        assert run_count[0] == 0, "No child should be started"
        print("  PASS: Supervisor exited without starting child\n")
    
    # Test 3: Verify shutdown reason in state
    print("Test 3: Shutdown reason recorded")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["echo"],
            run_fn=lambda cmd: 0,
        )
        
        supervisor.run()
        
        import json
        with open(tmp_path / "supervisor_state.json", "r") as f:
            state = json.load(f)
        
        print(f"  shutdown_reason: {state.get('shutdown_reason')}")
        assert state.get("shutdown_reason") == "child_clean_exit"
        print("  PASS: shutdown_reason correctly recorded\n")
    
    # Test 4: Signal handlers install without error
    print("Test 4: Signal handlers install cleanly")
    with tempfile.TemporaryDirectory() as tmpdir:
        supervisor = Supervisor(
            run_dir=Path(tmpdir),
            command=["test"],
            run_fn=lambda cmd: 0,
        )
        try:
            supervisor.install_signal_handlers()
            print("  PASS: Signal handlers installed without error\n")
        except Exception as e:
            print(f"  FAIL: {e}")
            return 1
    
    print("=== All smoke tests PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
