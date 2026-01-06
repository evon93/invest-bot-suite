"""
tests/test_time_provider.py

Tests for TimeProvider implementations.
"""

import time
import pytest
from engine.time_provider import SimulatedTimeProvider, RealTimeProvider


class TestSimulatedTimeProvider:
    def test_determinism_and_monotonicity(self):
        """Verify simulated time is deterministic and monotonic."""
        provider = SimulatedTimeProvider(start_ns=1000, quantum_ns=100)
        
        # Initial state
        assert provider.step() == 0
        assert provider.now_ns() == 1000
        
        # Advance 1 step
        provider.advance_steps(1)
        assert provider.step() == 1
        assert provider.now_ns() == 1100
        
        # Advance 5 steps
        provider.advance_steps(5)
        assert provider.step() == 6
        assert provider.now_ns() == 1600

    def test_advance_validation(self):
        """Verify input validation."""
        provider = SimulatedTimeProvider()
        with pytest.raises(ValueError):
            provider.advance_steps(-1)

    def test_seed_param(self):
        """Verify seed parameter is accepted (even if not strictly used for RNG logic)."""
        p1 = SimulatedTimeProvider(seed=42)
        p2 = SimulatedTimeProvider(seed=42)
        assert p1.now_ns() == p2.now_ns()


class TestRealTimeProvider:
    def test_real_time_progression(self):
        """Verify real time provider behavior."""
        provider = RealTimeProvider()
        
        t1 = provider.now_ns()
        s1 = provider.step()
        assert s1 == 0
        
        # Advance steps shouldn't fail and should increment counter
        provider.advance_steps(1)
        assert provider.step() == 1
        
        # Ensure time is somewhat sane (returns int, not zero unless epoch)
        t2 = provider.now_ns()
        assert t2 >= t1
        assert isinstance(t2, int)

    def test_advance_validation(self):
        provider = RealTimeProvider()
        with pytest.raises(ValueError):
            provider.advance_steps(-1)
