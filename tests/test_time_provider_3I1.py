"""
tests/test_time_provider_3I1.py

AG-3I-1-1: Tests for TimeProvider contract extensions.

Verifies:
- SystemTimeProvider: monotonic_ns non-decreasing, now_utc tz-aware UTC
- FrozenTimeProvider: deterministic, monotonic, manual control
- Singleton: get_time_provider / set_time_provider behavior
"""

import pytest
from datetime import datetime, timezone

from engine.time_provider import (
    SystemTimeProvider,
    FrozenTimeProvider,
    SimulatedTimeProvider,
    get_time_provider,
    set_time_provider,
)


class TestSystemTimeProvider:
    """Tests for SystemTimeProvider (AG-3I-1-1 contract)."""

    def test_monotonic_ns_non_decreasing(self):
        """monotonic_ns() should never decrease between calls."""
        provider = SystemTimeProvider()
        
        t1 = provider.monotonic_ns()
        t2 = provider.monotonic_ns()
        t3 = provider.monotonic_ns()
        
        assert t2 >= t1, f"monotonic_ns decreased: {t2} < {t1}"
        assert t3 >= t2, f"monotonic_ns decreased: {t3} < {t2}"

    def test_now_utc_is_tzaware_utc(self):
        """now_utc() should return tz-aware datetime in UTC."""
        provider = SystemTimeProvider()
        
        dt = provider.now_utc()
        
        assert isinstance(dt, datetime), f"Expected datetime, got {type(dt)}"
        assert dt.tzinfo is not None, "now_utc() returned naive datetime"
        assert dt.tzinfo == timezone.utc, f"Expected UTC, got {dt.tzinfo}"

    def test_now_ns_returns_positive_int(self):
        """now_ns() should return a positive integer (nanoseconds since epoch)."""
        provider = SystemTimeProvider()
        
        ns = provider.now_ns()
        
        assert isinstance(ns, int), f"Expected int, got {type(ns)}"
        assert ns > 0, "now_ns() should be positive (time since epoch)"

    def test_step_and_advance(self):
        """step() and advance_steps() should work correctly."""
        provider = SystemTimeProvider()
        
        assert provider.step() == 0
        provider.advance_steps(3)
        assert provider.step() == 3
        
        with pytest.raises(ValueError):
            provider.advance_steps(-1)


class TestFrozenTimeProvider:
    """Tests for FrozenTimeProvider (AG-3I-1-1 deterministic tests)."""

    def test_deterministic_time(self):
        """FrozenTimeProvider should return consistent values."""
        dt = datetime(2025, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        provider = FrozenTimeProvider(frozen_utc=dt, start_monotonic_ns=1000)
        
        # Multiple calls should return same values
        assert provider.now_utc() == dt
        assert provider.now_utc() == dt
        assert provider.monotonic_ns() == 1000
        assert provider.monotonic_ns() == 1000

    def test_monotonic_never_decreases(self):
        """monotonic_ns should never decrease when advanced."""
        provider = FrozenTimeProvider(start_monotonic_ns=0)
        
        t1 = provider.monotonic_ns()
        provider.advance_monotonic_ns(100)
        t2 = provider.monotonic_ns()
        provider.advance_monotonic_ns(0)  # Advance by 0 should be fine
        t3 = provider.monotonic_ns()
        
        assert t2 >= t1, f"monotonic decreased: {t2} < {t1}"
        assert t3 >= t2, f"monotonic decreased: {t3} < {t2}"

    def test_negative_advance_raises(self):
        """Negative advances should raise ValueError (monotonicity contract)."""
        provider = FrozenTimeProvider()
        
        with pytest.raises(ValueError, match="monotonicity"):
            provider.advance_monotonic_ns(-1)
        
        with pytest.raises(ValueError):
            provider.advance_steps(-1)

    def test_set_utc(self):
        """set_utc() should allow changing the frozen UTC time."""
        provider = FrozenTimeProvider()
        
        original = provider.now_utc()
        new_dt = datetime(2030, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        provider.set_utc(new_dt)
        
        assert provider.now_utc() == new_dt
        assert provider.now_utc() != original

    def test_now_utc_is_tzaware(self):
        """FrozenTimeProvider.now_utc() should be tz-aware."""
        provider = FrozenTimeProvider()
        
        dt = provider.now_utc()
        
        assert dt.tzinfo is not None, "now_utc() returned naive datetime"
        assert dt.tzinfo == timezone.utc

    # AG-3I-1-2: Tests for tz validation in set_utc()

    def test_set_utc_naive_datetime_raises(self):
        """set_utc() should raise ValueError for naive datetime (AG-3I-1-2)."""
        provider = FrozenTimeProvider()
        
        naive_dt = datetime(2025, 6, 15, 12, 0, 0)  # No tzinfo
        
        with pytest.raises(ValueError, match="tz-aware"):
            provider.set_utc(naive_dt)

    def test_set_utc_normalizes_non_utc_to_utc(self):
        """set_utc() should normalize non-UTC timezone to UTC (AG-3I-1-2)."""
        from datetime import timedelta
        
        provider = FrozenTimeProvider()
        
        # Create a datetime in a non-UTC timezone (UTC+2)
        tz_plus2 = timezone(timedelta(hours=2))
        dt_plus2 = datetime(2025, 6, 15, 14, 0, 0, tzinfo=tz_plus2)  # 14:00 UTC+2 = 12:00 UTC
        
        provider.set_utc(dt_plus2)
        result = provider.now_utc()
        
        # Should be normalized to UTC
        assert result.tzinfo == timezone.utc
        assert result.hour == 12  # 14:00 UTC+2 = 12:00 UTC


class TestSimulatedTimeProviderExtensions:
    """Tests for SimulatedTimeProvider AG-3I-1-1 extensions."""

    def test_now_utc_progresses_with_ns(self):
        """now_utc() should progress based on internal nanoseconds."""
        epoch = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        provider = SimulatedTimeProvider(start_ns=0, epoch_utc=epoch)
        
        assert provider.now_utc() == epoch
        
        # Advance 1 second
        provider.advance_ns(1_000_000_000)
        dt = provider.now_utc()
        
        assert dt.year == 2025
        assert dt.second == 1  # 1 second after epoch

    def test_monotonic_ns_equals_now_ns(self):
        """For simulation, monotonic_ns() should equal now_ns()."""
        provider = SimulatedTimeProvider(start_ns=1000)
        
        assert provider.monotonic_ns() == provider.now_ns() == 1000
        
        provider.advance_steps(1)
        assert provider.monotonic_ns() == provider.now_ns()


class TestSingleton:
    """Tests for get_time_provider / set_time_provider singleton."""

    def test_default_returns_system_provider(self):
        """get_time_provider() should return SystemTimeProvider when not set."""
        # Reset to default
        set_time_provider(None)
        
        provider = get_time_provider()
        
        assert isinstance(provider, SystemTimeProvider)

    def test_set_and_get(self):
        """set_time_provider() should affect get_time_provider()."""
        frozen = FrozenTimeProvider(start_monotonic_ns=42)
        
        set_time_provider(frozen)
        try:
            provider = get_time_provider()
            assert provider is frozen
            assert provider.monotonic_ns() == 42
        finally:
            # Cleanup
            set_time_provider(None)

    def test_reset_to_none(self):
        """Setting None should restore default behavior."""
        frozen = FrozenTimeProvider()
        set_time_provider(frozen)
        
        # Now reset
        set_time_provider(None)
        
        provider = get_time_provider()
        assert isinstance(provider, SystemTimeProvider)
