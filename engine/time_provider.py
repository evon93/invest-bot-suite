"""
engine/time_provider.py

Defines the TimeProvider protocol and implementations for deterministic time simulation.

AG-3I-1-1: Extended with now_utc(), monotonic_ns(), FrozenTimeProvider, and singleton.
"""

from typing import Protocol, Optional
from datetime import datetime, timezone
import time
from dataclasses import dataclass, field


class TimeProvider(Protocol):
    """Protocol for providing time and step information.
    
    AG-3I-1-1 contract:
    - now_utc(): Returns tz-aware UTC datetime (for timestamps)
    - monotonic_ns(): Returns monotonic nanoseconds (for duration/latency measurement)
    - now_ns(): Returns current time in nanoseconds (legacy)
    - step(): Returns current step count
    - advance_steps(n): Advances step count by n
    """

    def now_utc(self) -> datetime:
        """Return the current time as tz-aware UTC datetime."""
        ...

    def monotonic_ns(self) -> int:
        """Return monotonic time in nanoseconds (for duration measurement)."""
        ...

    def now_ns(self) -> int:
        """Return the current time in nanoseconds."""
        ...

    def step(self) -> int:
        """Return the current step count."""
        ...

    def advance_steps(self, n: int = 1) -> None:
        """Advance the step count by n (and potentially time)."""
        ...


class SystemTimeProvider:
    """
    Real time provider using system clock.
    
    AG-3I-1-1: Implements now_utc() and monotonic_ns() contract.
    """
    def __init__(self):
        self._step = 0

    def now_utc(self) -> datetime:
        """Return current time as tz-aware UTC datetime."""
        return datetime.now(timezone.utc)

    def monotonic_ns(self) -> int:
        """Return monotonic time in nanoseconds."""
        return time.monotonic_ns()

    def now_ns(self) -> int:
        """Return current time in nanoseconds (wall-clock)."""
        return time.time_ns()

    def step(self) -> int:
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n


@dataclass
class FrozenTimeProvider:
    """
    Frozen time provider for deterministic tests.
    
    AG-3I-1-1: Allows manual control of time for test reproducibility.
    
    Time is monotonic: monotonic_ns only increases, never decreases.
    """
    frozen_utc: datetime = field(default_factory=lambda: datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    start_monotonic_ns: int = 0
    _monotonic_ns: int = field(default=0, init=False)
    _step: int = field(default=0, init=False)

    def __post_init__(self):
        self._monotonic_ns = self.start_monotonic_ns

    def now_utc(self) -> datetime:
        """Return frozen UTC datetime (tz-aware)."""
        return self.frozen_utc

    def monotonic_ns(self) -> int:
        """Return current monotonic nanoseconds."""
        return self._monotonic_ns

    def now_ns(self) -> int:
        """Return frozen time as nanoseconds since epoch."""
        return int(self.frozen_utc.timestamp() * 1_000_000_000)

    def step(self) -> int:
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n

    def set_utc(self, dt: datetime) -> None:
        """
        Set frozen UTC datetime.
        
        Args:
            dt: Must be tz-aware. If not UTC, will be converted to UTC.
        
        Raises:
            ValueError: If dt is naive (no tzinfo).
        
        AG-3I-1-2: Added tz validation per DS audit.
        """
        if dt.tzinfo is None:
            raise ValueError("set_utc() requires tz-aware datetime, got naive")
        # Normalize to UTC if different timezone
        self.frozen_utc = dt.astimezone(timezone.utc)

    def advance_monotonic_ns(self, delta_ns: int) -> None:
        """Advance monotonic nanoseconds (must be >= 0 for monotonicity)."""
        if delta_ns < 0:
            raise ValueError("Cannot advance by negative nanoseconds (monotonicity)")
        self._monotonic_ns += delta_ns


@dataclass
class SimulatedTimeProvider:
    """
    Deterministic time provider for simulations.
    
    Supports two advancement modes:
    - advance_steps(n): Advances by n * quantum_ns (coarse, for bar-level steps)
    - advance_ns(delta): Advances by exact nanoseconds (fine, for stage-level timing)
    
    Time is monotonic: _now_ns only increases, never decreases.
    
    AG-3I-1-1: Extended with now_utc() and monotonic_ns().
    """
    seed: int = 42  # Kept for interface compatibility with other seeded components.
    start_ns: int = 0
    quantum_ns: int = 1_000_000_000  # 1 second per step (default)
    epoch_utc: datetime = field(default_factory=lambda: datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    _step: int = field(default=0, init=False)
    _now_ns: int = field(default=0, init=False)
    
    def __post_init__(self):
        # Initialize _now_ns from start_ns
        self._now_ns = self.start_ns

    def now_utc(self) -> datetime:
        """Return simulated UTC datetime based on epoch + elapsed ns."""
        from datetime import timedelta
        elapsed_seconds = self._now_ns / 1_000_000_000
        return self.epoch_utc + timedelta(seconds=elapsed_seconds)

    def monotonic_ns(self) -> int:
        """
        Return simulated monotonic nanoseconds.
        
        Note (AG-3I-1-2): In simulation mode, this returns the same counter as
        now_ns(). This differs from real systems where monotonic_ns() and
        time_ns() are independent clocks. The simulation uses a single internal
        counter (_now_ns) for both, ensuring determinism and simplicity.
        """
        return self._now_ns

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
    
    Deprecated: Use SystemTimeProvider for new code (AG-3I-1-1).
    """
    def __init__(self):
        self._step = 0

    def now_utc(self) -> datetime:
        """Return current time as tz-aware UTC datetime."""
        return datetime.now(timezone.utc)

    def monotonic_ns(self) -> int:
        """Return monotonic time in nanoseconds."""
        return time.monotonic_ns()

    def now_ns(self) -> int:
        return time.time_ns()

    def step(self) -> int:
        return self._step

    def advance_steps(self, n: int = 1) -> None:
        if n < 0:
            raise ValueError("Cannot advance by negative steps")
        self._step += n


# -----------------------------------------------------------------------------
# Singleton Pattern (AG-3I-1-1)
# -----------------------------------------------------------------------------

_global_time_provider: Optional[TimeProvider] = None


def get_time_provider() -> TimeProvider:
    """
    Get the global time provider.
    
    Returns SystemTimeProvider if no provider has been set.
    This is the recommended way to access time in production code.
    """
    global _global_time_provider
    if _global_time_provider is None:
        return SystemTimeProvider()
    return _global_time_provider


def set_time_provider(provider: Optional[TimeProvider]) -> None:
    """
    Set the global time provider.
    
    Use this in tests to inject FrozenTimeProvider or SimulatedTimeProvider.
    Set to None to restore default (SystemTimeProvider).
    
    WARNING: Not thread-safe. Call at test setup/teardown only.
    """
    global _global_time_provider
    _global_time_provider = provider
