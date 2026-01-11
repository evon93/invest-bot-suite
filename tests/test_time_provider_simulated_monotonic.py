"""
tests/test_time_provider_simulated_monotonic.py

Tests for SimulatedTimeProvider's advance_ns() method and monotonicity guarantees.
Part of ticket AG-3I-1-1.
"""

import pytest
from engine.time_provider import SimulatedTimeProvider


class TestSimulatedTimeProviderAdvanceNs:
    """Tests for advance_ns() functionality."""
    
    def test_advance_ns_basic(self):
        """advance_ns() should increment _now_ns by the specified delta."""
        provider = SimulatedTimeProvider(start_ns=0)
        assert provider.now_ns() == 0
        
        provider.advance_ns(1_000_000)  # 1ms
        assert provider.now_ns() == 1_000_000
        
        provider.advance_ns(500_000)  # 0.5ms
        assert provider.now_ns() == 1_500_000
    
    def test_advance_ns_zero(self):
        """advance_ns(0) should be allowed and not change time."""
        provider = SimulatedTimeProvider(start_ns=100)
        provider.advance_ns(0)
        assert provider.now_ns() == 100
    
    def test_advance_ns_negative_raises(self):
        """advance_ns() with negative delta should raise ValueError."""
        provider = SimulatedTimeProvider()
        with pytest.raises(ValueError, match="negative nanoseconds"):
            provider.advance_ns(-1)
    
    def test_monotonicity_with_mixed_advances(self):
        """Time should be monotonically increasing with mixed advance methods."""
        provider = SimulatedTimeProvider(start_ns=0, quantum_ns=1_000_000_000)
        
        times = [provider.now_ns()]
        
        provider.advance_steps(1)
        times.append(provider.now_ns())
        
        provider.advance_ns(500_000)
        times.append(provider.now_ns())
        
        provider.advance_steps(2)
        times.append(provider.now_ns())
        
        provider.advance_ns(100)
        times.append(provider.now_ns())
        
        # Verify strict monotonicity
        for i in range(1, len(times)):
            assert times[i] > times[i-1], f"Time not monotonic at index {i}: {times}"
    
    def test_determinism_same_sequence(self):
        """Same sequence of advances should produce identical results."""
        def run_sequence():
            p = SimulatedTimeProvider(seed=42, start_ns=1000, quantum_ns=100_000)
            p.advance_ns(50_000)
            p.advance_steps(3)
            p.advance_ns(25_000)
            return p.now_ns(), p.step()
        
        result1 = run_sequence()
        result2 = run_sequence()
        
        assert result1 == result2, "Results should be deterministic"
    
    def test_advance_steps_also_advances_now_ns(self):
        """advance_steps() should increment both _step and _now_ns."""
        provider = SimulatedTimeProvider(start_ns=0, quantum_ns=1_000_000_000)  # 1s
        
        assert provider.step() == 0
        assert provider.now_ns() == 0
        
        provider.advance_steps(2)
        
        assert provider.step() == 2
        assert provider.now_ns() == 2_000_000_000  # 2 seconds
    
    def test_start_ns_initialization(self):
        """now_ns() should start at start_ns value."""
        provider = SimulatedTimeProvider(start_ns=5_000_000_000)  # 5 seconds
        assert provider.now_ns() == 5_000_000_000


class TestSimulatedTimeProviderBackwardCompat:
    """Ensure backward compatibility with existing tests."""
    
    def test_existing_interface_unchanged(self):
        """Existing interface (now_ns, step, advance_steps) should work as before."""
        provider = SimulatedTimeProvider(start_ns=1000, quantum_ns=100)
        
        assert provider.step() == 0
        assert provider.now_ns() == 1000
        
        provider.advance_steps(1)
        assert provider.step() == 1
        assert provider.now_ns() == 1100
        
        provider.advance_steps(5)
        assert provider.step() == 6
        assert provider.now_ns() == 1600
    
    def test_seed_param_accepted(self):
        """Seed parameter should be accepted."""
        p1 = SimulatedTimeProvider(seed=42)
        p2 = SimulatedTimeProvider(seed=42)
        assert p1.now_ns() == p2.now_ns()
