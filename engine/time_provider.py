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
    Time advances by quantum_ns for each step.
    """
    seed: int = 42  # Kept for interface compatibility with other seeded components, though not used for RNG here.
    start_ns: int = 0
    quantum_ns: int = 1_000_000_000  # 1 second per step
    _step: int = field(default=0, init=False)

    def now_ns(self) -> int:
        return self.start_ns + (self._step * self.quantum_ns)

    def step(self) -> int:
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n


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
