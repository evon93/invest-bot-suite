"""
engine/time_provider.py

Defines the TimeProvider protocol and implementations for deterministic time simulation.
"""

from typing import Protocol
import time
from dataclasses import dataclass, field


class TimeProvider(Protocol):
    """Protocol for providing time and step information."""

    def now_ns(self) -> int:
        """Return the current time in nanoseconds."""
        ...

    def step(self) -> int:
        """Return the current step count."""
        ...

    def advance_steps(self, n: int = 1) -> None:
        """Advance the step count by n (and potentially time)."""
        ...


@dataclass
class SimulatedTimeProvider:
    """
    Deterministic time provider for simulations.
    
    Supports two advancement modes:
    - advance_steps(n): Advances by n * quantum_ns (coarse, for bar-level steps)
    - advance_ns(delta): Advances by exact nanoseconds (fine, for stage-level timing)
    
    Time is monotonic: _now_ns only increases, never decreases.
    """
    seed: int = 42  # Kept for interface compatibility with other seeded components.
    start_ns: int = 0
    quantum_ns: int = 1_000_000_000  # 1 second per step (default)
    _step: int = field(default=0, init=False)
    _now_ns: int = field(default=0, init=False)
    
    def __post_init__(self):
        # Initialize _now_ns from start_ns
        self._now_ns = self.start_ns

    def now_ns(self) -> int:
        """Return current simulated time in nanoseconds."""
        return self._now_ns

    def step(self) -> int:
        """Return current step count."""
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        """Advance by n steps (each step = quantum_ns nanoseconds)."""
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n
        self._now_ns += n * self.quantum_ns
    
    def advance_ns(self, delta_ns: int) -> None:
        """Advance internal time by delta_ns nanoseconds (monotonically)."""
        if delta_ns < 0:
            raise ValueError("Cannot advance by negative nanoseconds")
        self._now_ns += delta_ns


class RealTimeProvider:
    """
    Real time provider using system clock.
    Step count is maintained manually.
    """
    def __init__(self):
        self._step = 0

    def now_ns(self) -> int:
        return time.time_ns()

    def step(self) -> int:
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n
