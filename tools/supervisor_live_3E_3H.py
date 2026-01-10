#!/usr/bin/env python3
"""
tools/supervisor_live_3E_3H.py

24/7 Supervisor wrapper for run_live_3E.py (or any child process).

Features:
- Automatic restart on crash/non-zero exit
- Deterministic exponential backoff (no jitter)
- State persistence (supervisor_state.json)
- Append-only log (supervisor.log)
- No external dependencies

Usage:
    python supervisor_live_3E_3H.py --run-dir <dir> -- python tools/run_live_3E.py <args>

Part of ticket AG-3H-4-1.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def calculate_backoff(attempt: int, base_s: float, cap_s: float) -> float:
    """
    Calculate deterministic exponential backoff.
    
    Formula: delay = min(cap, base * 2^attempt)
    No jitter for determinism.
    """
    delay = base_s * (2 ** attempt)
    return min(delay, cap_s)


def get_iso_timestamp() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class Supervisor:
    """
    Process supervisor with automatic restart and backoff.
    
    State is persisted to supervisor_state.json.
    Logs are appended to supervisor.log.
    """
    
    def __init__(
        self,
        run_dir: Path,
        command: List[str],
        *,
        max_restarts: Optional[int] = None,
        backoff_base_s: float = 0.5,
        backoff_cap_s: float = 30.0,
        log_file: Optional[Path] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
        run_fn: Optional[Callable[[List[str]], int]] = None,
    ):
        """
        Initialize supervisor.
        
        Args:
            run_dir: Directory for state and logs
            command: Command line to execute (list of args)
            max_restarts: Maximum restart attempts (None = unlimited)
            backoff_base_s: Base delay for exponential backoff
            backoff_cap_s: Maximum delay cap
            log_file: Log file path (default: run_dir/supervisor.log)
            sleep_fn: Optional sleep function for testing
            run_fn: Optional run function for testing (returns exit code)
        """
        self._run_dir = Path(run_dir)
        self._command = command
        self._max_restarts = max_restarts
        self._backoff_base = backoff_base_s
        self._backoff_cap = backoff_cap_s
        
        self._log_path = log_file or (self._run_dir / "supervisor.log")
        self._state_path = self._run_dir / "supervisor_state.json"
        
        self._sleep_fn = sleep_fn or time.sleep
        self._run_fn = run_fn or self._default_run
        
        # State
        self._attempt = 0
        self._last_exit_code: Optional[int] = None
        self._last_exit_ts: Optional[str] = None
        self._next_delay: float = 0.0
        
        # Ensure run_dir exists
        self._run_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure log file parent directory exists
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _default_run(self, cmd: List[str]) -> int:
        """Default run function using subprocess."""
        result = subprocess.run(cmd)
        return result.returncode
    
    def _log(self, message: str) -> None:
        """Append message to log file."""
        timestamp = get_iso_timestamp()
        line = f"[{timestamp}] {message}\n"
        
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line)
    
    def _save_state(self) -> None:
        """Save current state to JSON file."""
        state = {
            "attempt": self._attempt,
            "last_exit_code": self._last_exit_code,
            "last_exit_ts": self._last_exit_ts,
            "next_delay_s": self._next_delay,
            "cmdline": self._command,
            "max_restarts": self._max_restarts,
            "backoff_base_s": self._backoff_base,
            "backoff_cap_s": self._backoff_cap,
        }
        
        with open(self._state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
    
    def run(self) -> int:
        """
        Run the supervisor loop.
        
        Returns:
            Final exit code (0 on clean exit, last child exit code otherwise)
        """
        self._log(f"Supervisor started. Command: {' '.join(self._command)}")
        self._log(f"Config: max_restarts={self._max_restarts}, backoff_base={self._backoff_base}s, backoff_cap={self._backoff_cap}s")
        
        while True:
            self._attempt += 1
            
            # Check max restarts (attempt 1 = first run, not a restart)
            if self._max_restarts is not None and self._attempt > self._max_restarts + 1:
                self._log(f"Max restarts ({self._max_restarts}) exceeded. Exiting.")
                self._save_state()
                return self._last_exit_code or 1
            
            self._log(f"Starting child (attempt {self._attempt})...")
            
            # Run child process
            try:
                exit_code = self._run_fn(self._command)
            except Exception as e:
                self._log(f"Error running child: {e}")
                exit_code = 1
            
            self._last_exit_code = exit_code
            self._last_exit_ts = get_iso_timestamp()
            
            # Check if clean exit
            if exit_code == 0:
                self._log(f"Child exited cleanly (code 0). Supervisor stopping.")
                self._save_state()
                return 0
            
            # Calculate backoff
            self._next_delay = calculate_backoff(
                self._attempt - 1,  # 0-indexed for backoff
                self._backoff_base,
                self._backoff_cap,
            )
            
            self._log(f"Child exited with code {exit_code}. Restarting in {self._next_delay:.2f}s...")
            self._save_state()
            
            # Wait before restart
            self._sleep_fn(self._next_delay)


def main():
    parser = argparse.ArgumentParser(
        description="24/7 Supervisor for child processes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  supervisor_live_3E_3H.py --run-dir out/ -- python run_live_3E.py --max-steps 100
  supervisor_live_3E_3H.py --max-restarts 10 -- python my_script.py
        """
    )
    
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=Path("report/out_3H4_supervisor_run"),
        help="Directory for state and logs (default: report/out_3H4_supervisor_run)"
    )
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=None,
        help="Maximum restart attempts (default: unlimited)"
    )
    parser.add_argument(
        "--backoff-base-s",
        type=float,
        default=0.5,
        help="Base delay for exponential backoff in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--backoff-cap-s",
        type=float,
        default=30.0,
        help="Maximum backoff delay cap in seconds (default: 30)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Log file path (default: <run-dir>/supervisor.log)"
    )
    
    # Parse known args and capture everything after "--" as child command
    args, remaining = parser.parse_known_args()
    
    # Extract child command (after "--")
    if "--" in sys.argv:
        separator_idx = sys.argv.index("--")
        child_command = sys.argv[separator_idx + 1:]
    elif remaining:
        child_command = remaining
    else:
        parser.error("No child command specified. Use: supervisor ... -- <command>")
    
    if not child_command:
        parser.error("No child command specified after '--'")
    
    print(f"Supervisor starting...")
    print(f"  Run dir: {args.run_dir}")
    print(f"  Command: {' '.join(child_command)}")
    print(f"  Max restarts: {args.max_restarts or 'unlimited'}")
    print(f"  Backoff: base={args.backoff_base_s}s, cap={args.backoff_cap_s}s")
    
    supervisor = Supervisor(
        run_dir=args.run_dir,
        command=child_command,
        max_restarts=args.max_restarts,
        backoff_base_s=args.backoff_base_s,
        backoff_cap_s=args.backoff_cap_s,
        log_file=args.log_file,
    )
    
    return supervisor.run()


if __name__ == "__main__":
    sys.exit(main())
