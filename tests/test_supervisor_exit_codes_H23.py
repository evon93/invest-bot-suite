"""
tests/test_supervisor_exit_codes_H23.py

Tests for supervisor exit code semantics (AG-H2-3-1).

Validates:
- Exit code 0 on clean child exit
- Exit code 0 on graceful shutdown (StopController)
- Exit code 2 on child error with max_restarts exceeded
"""

import pytest
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from supervisor_live_3E_3H import Supervisor, StopController


class TestSupervisorExitCodeSemantics:
    """Test exit code semantics: 0=graceful, 2=error."""
    
    def test_exit_code_0_on_clean_child_exit(self, tmp_path: Path):
        """Child exit 0 → supervisor exit 0."""
        
        def mock_run(cmd: List[str]) -> int:
            return 0  # Clean exit
        
        def mock_sleep(delay: float) -> None:
            pass
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["dummy"],
            max_restarts=3,
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        exit_code = supervisor.run()
        assert exit_code == 0, "Clean child exit should result in supervisor exit code 0"
    
    def test_exit_code_2_on_child_error_max_restarts(self, tmp_path: Path):
        """Child error + max_restarts=0 → supervisor exit 2."""
        
        def mock_run(cmd: List[str]) -> int:
            return 1  # Error exit
        
        def mock_sleep(delay: float) -> None:
            pass
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["dummy"],
            max_restarts=0,  # No restarts allowed
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        exit_code = supervisor.run()
        assert exit_code == 2, "Child error with max_restarts exceeded should result in supervisor exit code 2"
    
    def test_exit_code_0_on_graceful_stop(self, tmp_path: Path):
        """Graceful stop via StopController → supervisor exit 0."""
        stop_controller = StopController()
        call_count = 0
        
        def mock_run(cmd: List[str]) -> int:
            nonlocal call_count
            call_count += 1
            # First call: request stop, then return error
            if call_count == 1:
                stop_controller.request_stop("SIGINT")
            return 1  # Would be error, but stop was requested
        
        def mock_sleep(delay: float) -> None:
            pass
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["dummy"],
            max_restarts=10,
            sleep_fn=mock_sleep,
            run_fn=mock_run,
            stop_controller=stop_controller,
        )
        
        exit_code = supervisor.run()
        assert exit_code == 0, "Graceful stop via StopController should result in supervisor exit code 0"
    
    def test_exit_code_2_on_multiple_restarts_then_exceed(self, tmp_path: Path):
        """Multiple restarts before exceeding max → supervisor exit 2."""
        call_count = 0
        
        def mock_run(cmd: List[str]) -> int:
            nonlocal call_count
            call_count += 1
            return 1  # Always error
        
        def mock_sleep(delay: float) -> None:
            pass
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["dummy"],
            max_restarts=2,  # Allow 2 restarts (3 total attempts)
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        exit_code = supervisor.run()
        assert call_count == 3, "Should have attempted 3 runs (initial + 2 restarts)"
        assert exit_code == 2, "Max restarts exceeded should result in supervisor exit code 2"
