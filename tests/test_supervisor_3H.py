"""
tests/test_supervisor_3H.py

Tests for 24/7 Supervisor (AG-3H-4-1).

Validates:
- Backoff calculation is deterministic
- Supervisor restarts on non-zero exit
- Supervisor stops on exit code 0
- State and log files are created
- Max restarts limit is respected
"""

import json
import pytest
from pathlib import Path
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from supervisor_live_3E_3H import Supervisor, calculate_backoff


class TestBackoffCalculation:
    """Test deterministic backoff formula."""
    
    def test_backoff_exponential(self):
        """Backoff should double each attempt."""
        base = 0.5
        cap = 30.0
        
        delays = [calculate_backoff(i, base, cap) for i in range(6)]
        
        assert delays[0] == 0.5   # 0.5 * 2^0
        assert delays[1] == 1.0   # 0.5 * 2^1
        assert delays[2] == 2.0   # 0.5 * 2^2
        assert delays[3] == 4.0   # 0.5 * 2^3
        assert delays[4] == 8.0   # 0.5 * 2^4
        assert delays[5] == 16.0  # 0.5 * 2^5
    
    def test_backoff_capped(self):
        """Backoff should not exceed cap."""
        base = 1.0
        cap = 5.0
        
        delays = [calculate_backoff(i, base, cap) for i in range(10)]
        
        assert delays[0] == 1.0  # 1 * 2^0
        assert delays[1] == 2.0  # 1 * 2^1
        assert delays[2] == 4.0  # 1 * 2^2
        assert delays[3] == 5.0  # capped (8 > 5)
        assert delays[4] == 5.0  # capped (16 > 5)
        assert all(d == 5.0 for d in delays[3:])
    
    def test_backoff_deterministic(self):
        """Same inputs should produce same outputs."""
        for _ in range(10):
            assert calculate_backoff(3, 0.5, 30) == 4.0


class TestSupervisorRestartBehavior:
    """Test supervisor restart logic."""
    
    def test_exits_on_code_zero(self, tmp_path: Path):
        """Supervisor should exit when child returns 0."""
        exit_codes = [0]  # Child exits cleanly immediately
        run_calls = []
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["echo", "hello"],
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        result = supervisor.run()
        
        assert result == 0
        assert len(run_calls) == 1
        assert len(sleep_calls) == 0  # No sleep needed
    
    def test_restarts_on_non_zero(self, tmp_path: Path):
        """Supervisor should restart on non-zero exit."""
        exit_codes = [1, 1, 0]  # Fail twice, then succeed
        run_calls = []
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            backoff_base_s=1.0,
            backoff_cap_s=10.0,
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        result = supervisor.run()
        
        assert result == 0
        assert len(run_calls) == 3  # 2 failures + 1 success
        assert len(sleep_calls) == 2  # Sleep after each failure
        assert sleep_calls[0] == 1.0  # First backoff
        assert sleep_calls[1] == 2.0  # Second backoff
    
    def test_max_restarts_limit(self, tmp_path: Path):
        """Supervisor should stop after max_restarts."""
        exit_codes = [1] * 100  # Always fail
        run_calls = []
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            run_calls.append(cmd)
            return exit_codes.pop(0) if exit_codes else 1
        
        def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["fail"],
            max_restarts=3,  # Allow 3 restarts after initial run
            backoff_base_s=0.1,
            backoff_cap_s=1.0,
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        result = supervisor.run()
        
        assert result == 1  # Returns last exit code
        assert len(run_calls) == 4  # 1 initial + 3 restarts
        assert len(sleep_calls) == 4  # Sleep after each failure


class TestSupervisorStateAndLogs:
    """Test state persistence and logging."""
    
    def test_state_file_created(self, tmp_path: Path):
        """State file should be created with correct content."""
        exit_codes = [1, 0]  # Fail once, then succeed
        
        def mock_run(cmd: List[str]) -> int:
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            pass  # No-op
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test", "--arg"],
            backoff_base_s=0.5,
            backoff_cap_s=10.0,
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        supervisor.run()
        
        state_path = tmp_path / "supervisor_state.json"
        assert state_path.exists()
        
        with open(state_path, "r") as f:
            state = json.load(f)
        
        assert state["attempt"] == 2  # 2 attempts total
        assert state["last_exit_code"] == 0  # Ended with success
        assert state["cmdline"] == ["test", "--arg"]
        assert state["backoff_base_s"] == 0.5
        assert state["backoff_cap_s"] == 10.0
    
    def test_log_file_created(self, tmp_path: Path):
        """Log file should be created with entries."""
        exit_codes = [1, 0]
        
        def mock_run(cmd: List[str]) -> int:
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            pass
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        supervisor.run()
        
        log_path = tmp_path / "supervisor.log"
        assert log_path.exists()
        
        content = log_path.read_text()
        
        # Check log contains expected entries
        assert "Supervisor started" in content
        assert "Starting child" in content
        assert "exited with code 1" in content
        # AG-3I-2-1: Message changed from 'exited cleanly' to 'shutting down'
        assert "shutting down" in content.lower() or "child_clean_exit" in content
    
    def test_custom_log_file_path(self, tmp_path: Path):
        """Custom log file path should be respected."""
        custom_log = tmp_path / "custom" / "my.log"
        
        def mock_run(cmd: List[str]) -> int:
            return 0
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            log_file=custom_log,
            run_fn=mock_run,
        )
        
        supervisor.run()
        
        assert custom_log.exists()


class TestSupervisorBackoffProgression:
    """Test backoff delay progression."""
    
    def test_backoff_increases_with_attempts(self, tmp_path: Path):
        """Each restart should have longer backoff."""
        exit_codes = [1, 1, 1, 1, 0]  # 4 failures then success
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            backoff_base_s=1.0,
            backoff_cap_s=100.0,  # High cap to see full progression
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        supervisor.run()
        
        # Verify exponential progression
        assert sleep_calls == [1.0, 2.0, 4.0, 8.0]
    
    def test_backoff_caps_at_max(self, tmp_path: Path):
        """Backoff should cap at max value."""
        exit_codes = [1, 1, 1, 1, 1, 0]
        sleep_calls = []
        
        def mock_run(cmd: List[str]) -> int:
            return exit_codes.pop(0) if exit_codes else 0
        
        def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)
        
        supervisor = Supervisor(
            run_dir=tmp_path,
            command=["test"],
            backoff_base_s=1.0,
            backoff_cap_s=3.0,  # Cap at 3 seconds
            sleep_fn=mock_sleep,
            run_fn=mock_run,
        )
        
        supervisor.run()
        
        # 1, 2, 3, 3, 3 (capped after third)
        assert sleep_calls == [1.0, 2.0, 3.0, 3.0, 3.0]
