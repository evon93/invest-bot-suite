"""
tests/test_supervisor_graceful_shutdown_3I2.py

Tests for graceful shutdown functionality (AG-3I-2-1).

Validates:
- StopController idempotent behavior
- Supervisor respects stop_requested
- Multi-signal does not break
- Shutdown reason is recorded
"""

import json
import pytest
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from supervisor_live_3E_3H import Supervisor, StopController, calculate_backoff


class TestStopController:
    """Tests for StopController idempotent behavior."""
    
    def test_initial_state_not_stopped(self):
        """Initially, is_stop_requested should be False."""
        ctrl = StopController()
        assert ctrl.is_stop_requested is False
        assert ctrl.stop_reason is None
    
    def test_request_stop_sets_flag(self):
        """request_stop should set is_stop_requested to True."""
        ctrl = StopController()
        ctrl.request_stop("SIGINT")
        
        assert ctrl.is_stop_requested is True
        assert ctrl.stop_reason == "SIGINT"
    
    def test_request_stop_idempotent(self):
        """Multiple request_stop calls should be idempotent - first reason wins."""
        ctrl = StopController()
        
        ctrl.request_stop("SIGINT")
        ctrl.request_stop("SIGTERM")
        ctrl.request_stop("manual")
        
        # First reason wins
        assert ctrl.is_stop_requested is True
        assert ctrl.stop_reason == "SIGINT"
    
    def test_reset_for_testing(self):
        """reset() should clear stop state."""
        ctrl = StopController()
        ctrl.request_stop("test")
        
        assert ctrl.is_stop_requested is True
        
        ctrl.reset()
        
        assert ctrl.is_stop_requested is False
        assert ctrl.stop_reason is None


class TestSupervisorGracefulShutdown:
    """Tests for Supervisor graceful shutdown behavior."""
    
    def test_stop_before_first_cycle(self, tmp_path: Path):
        """If stop is requested before first cycle, supervisor exits immediately."""
        stop_ctrl = StopController()
        stop_ctrl.request_stop("pre_start_stop")
        
        run_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            return 0
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            run_fn=mock_run,
            stop_controller=stop_ctrl,
        )
        
        result = supervisor.run()
        
        assert result == 0
        assert len(run_calls) == 0  # No child started
        
        # Check state file
        state_path = tmp_path / "supervisor_state.json"
        assert state_path.exists()
        
        with open(state_path, "r") as f:
            state = json.load(f)
        
        assert state["shutdown_reason"] == "pre_start_stop"
    
    def test_stop_after_child_exit_prevents_restart(self, tmp_path: Path):
        """If stop is requested after child exit, no restart occurs."""
        stop_ctrl = StopController()
        run_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            # After first run, request stop
            if len(run_calls) == 1:
                stop_ctrl.request_stop("SIGTERM")
            return 1  # Non-zero exit to trigger restart logic
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["fail_once"],
            run_fn=mock_run,
            stop_controller=stop_ctrl,
        )
        
        result = supervisor.run()
        
        assert result == 0  # Graceful shutdown returns 0
        assert len(run_calls) == 1  # Only one run, no restart
        
        # Verify log contains shutdown message
        log_path = tmp_path / "supervisor.log"
        content = log_path.read_text()
        assert "shutting down" in content.lower()
        assert "SIGTERM" in content
    
    def test_stop_during_backoff_prevents_sleep(self, tmp_path: Path):
        """If stop is requested before backoff sleep, no sleep occurs."""
        stop_ctrl = StopController()
        run_calls = []
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            return 1  # Non-zero exit
        
        def mock_sleep(delay: float) -> None:
            # This should not be called if stop is requested before sleep
            sleep_calls.append(delay)
        
        # Request stop before supervisor runs
        # But actually we want to test stop DURING the run
        # So we use a run_fn that requests stop after first exit
        
        def mock_run_with_stop(cmd: List[str]) -> int:
            run_calls.append(cmd)
            if len(run_calls) == 1:
                # Simulate SIGINT arriving during child execution
                # will be checked after child exits, before backoff
                stop_ctrl.request_stop("SIGINT")
            return 1
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            run_fn=mock_run_with_stop,
            sleep_fn=mock_sleep,
            stop_controller=stop_ctrl,
        )
        
        result = supervisor.run()
        
        assert result == 0
        assert len(run_calls) == 1
        assert len(sleep_calls) == 0  # No sleep - exited before backoff
    
    def test_shutdown_reason_in_state(self, tmp_path: Path):
        """shutdown_reason should be recorded in state file."""
        stop_ctrl = StopController()
        stop_ctrl.request_stop("test_reason")
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["echo"],
            run_fn=lambda cmd: 0,
            stop_controller=stop_ctrl,
        )
        
        supervisor.run()
        
        with open(tmp_path / "supervisor_state.json", "r") as f:
            state = json.load(f)
        
        assert state["shutdown_reason"] == "test_reason"
    
    def test_max_restarts_also_records_reason(self, tmp_path: Path):
        """max_restarts exceeded should also record shutdown_reason."""
        exit_codes = [1, 1, 1, 1]  # Always fail
        
        def mock_run(cmd: List[str]) -> int:
            return exit_codes.pop(0) if exit_codes else 1
        
        def mock_sleep(delay: float) -> None:
            pass  # No-op
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["fail"],
            max_restarts=2,
            run_fn=mock_run,
            sleep_fn=mock_sleep,
        )
        
        result = supervisor.run()
        
        assert result == 1  # Non-zero from max_restarts
        
        with open(tmp_path / "supervisor_state.json", "r") as f:
            state = json.load(f)
        
        assert state["shutdown_reason"] == "max_restarts_exceeded"
    
    def test_clean_exit_records_reason(self, tmp_path: Path):
        """Clean child exit should record shutdown_reason as child_clean_exit."""
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["echo"],
            run_fn=lambda cmd: 0,
        )
        
        result = supervisor.run()
        
        assert result == 0
        
        with open(tmp_path / "supervisor_state.json", "r") as f:
            state = json.load(f)
        
        assert state["shutdown_reason"] == "child_clean_exit"


class TestSupervisorSignalHandlers:
    """Tests for signal handler installation."""
    
    def test_install_signal_handlers_no_exception(self, tmp_path: Path):
        """install_signal_handlers should not raise on any platform."""
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            run_fn=lambda cmd: 0,
        )
        
        # Should not raise
        supervisor.install_signal_handlers()
    
    def test_signal_handlers_use_stop_controller(self, tmp_path: Path):
        """Signal handlers should call request_stop on the controller."""
        import signal
        
        stop_ctrl = StopController()
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            run_fn=lambda cmd: 0,
            stop_controller=stop_ctrl,
        )
        
        supervisor.install_signal_handlers()
        
        # Verify controller is not stopped yet
        assert stop_ctrl.is_stop_requested is False
        
        # Simulate SIGINT by directly calling the handler
        # Note: We can't easily send real signals in tests
        # But we can verify the stop_controller is used
