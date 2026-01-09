"""
tests/test_metrics_collector_v0.py

Tests for MetricsCollector with deterministic clock.
"""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.metrics_collector import MetricsCollector, NoOpMetricsCollector


class FakeClock:
    """Deterministic clock for testing."""
    
    def __init__(self, start: float = 0.0, step: float = 0.001):
        self._time = start
        self._step = step
    
    def __call__(self) -> float:
        t = self._time
        self._time += self._step
        return t
    
    def advance(self, delta: float) -> None:
        self._time += delta


class TestMetricsCollectorBasic:
    """Basic functionality tests."""
    
    def test_start_end_records_latency(self):
        """start/end pair records latency correctly."""
        clock = FakeClock(start=0.0, step=0.010)  # 10ms steps
        collector = MetricsCollector(clock_fn=clock)
        
        collector.start("msg_1")  # t=0.0
        collector.end("msg_1", "FILLED")  # t=0.010
        
        summary = collector.snapshot_summary()
        assert summary["latency_count"] == 1
        assert summary["latency_p50_ms"] == 10.0  # 0.010s = 10ms
    
    def test_multiple_messages(self):
        """Multiple messages tracked correctly."""
        clock = FakeClock(start=0.0, step=0.001)
        collector = MetricsCollector(clock_fn=clock)
        
        for i in range(5):
            collector.start(f"msg_{i}")
            collector.end(f"msg_{i}", "FILLED")
        
        summary = collector.snapshot_summary()
        assert summary["processed"] == 5
        assert summary["filled"] == 5
        assert summary["latency_count"] == 5
    
    def test_status_counters(self):
        """Status counters increment correctly."""
        collector = MetricsCollector()
        
        collector.end("m1", "ALLOWED")
        collector.end("m2", "REJECTED", reason="max_position")
        collector.end("m3", "REJECTED", reason="max_position")
        collector.end("m4", "FILLED")
        collector.end("m5", "ERROR", reason="timeout")
        
        summary = collector.snapshot_summary()
        
        assert summary["processed"] == 5
        assert summary["allowed"] == 1
        assert summary["rejected"] == 2
        assert summary["filled"] == 1
        assert summary["errors"] == 1


class TestMetricsCollectorCounters:
    """Detailed counter tests."""
    
    def test_retries_counted(self):
        """Retry count accumulated correctly."""
        collector = MetricsCollector()
        
        collector.end("m1", "FILLED", retry_count=3)
        collector.end("m2", "FILLED", retry_count=2)
        
        summary = collector.snapshot_summary()
        assert summary["retries"] == 5
    
    def test_dupes_filtered(self):
        """Duplicate messages counted correctly."""
        collector = MetricsCollector()
        
        collector.end("m1", "ALLOWED")
        collector.end("m2", "ALLOWED", dupe=True)
        collector.end("m3", "ALLOWED", dupe=True)
        
        summary = collector.snapshot_summary()
        assert summary["processed"] == 3
        assert summary["dupes_filtered"] == 2
        # Note: dupe=True means we don't increment allowed
        assert summary["allowed"] == 1
    
    def test_errors_by_reason(self):
        """Errors broken down by reason."""
        collector = MetricsCollector()
        
        collector.end("m1", "ERROR", reason="timeout")
        collector.end("m2", "ERROR", reason="timeout")
        collector.end("m3", "ERROR", reason="network")
        
        summary = collector.snapshot_summary()
        assert summary["errors"] == 3
        assert summary["errors_by_reason"] == {"network": 1, "timeout": 2}
    
    def test_rejects_by_reason(self):
        """Rejections broken down by reason."""
        collector = MetricsCollector()
        
        collector.end("m1", "REJECTED", reason="dd_guardrail")
        collector.end("m2", "REJECTED", reason="max_position")
        collector.end("m3", "REJECTED", reason="dd_guardrail")
        
        summary = collector.snapshot_summary()
        assert summary["rejected"] == 3
        assert summary["rejects_by_reason"] == {"dd_guardrail": 2, "max_position": 1}


class TestMetricsCollectorPercentiles:
    """Percentile calculation tests."""
    
    def test_empty_latencies_returns_none(self):
        """Empty latencies return None for percentiles."""
        collector = MetricsCollector()
        
        summary = collector.snapshot_summary()
        
        assert summary["latency_p50_ms"] is None
        assert summary["latency_p95_ms"] is None
        assert summary["latency_count"] == 0
    
    def test_single_latency(self):
        """Single latency returns same for all percentiles."""
        clock = FakeClock(start=0.0, step=0.050)  # 50ms
        collector = MetricsCollector(clock_fn=clock)
        
        collector.start("msg_1")
        collector.end("msg_1", "FILLED")
        
        summary = collector.snapshot_summary()
        
        assert summary["latency_p50_ms"] == 50.0
        assert summary["latency_p95_ms"] == 50.0
    
    def test_p95_with_many_values(self):
        """P95 calculated correctly with many values."""
        collector = MetricsCollector()
        
        # Add 100 latencies manually
        for i in range(100):
            collector._latencies.append(float(i + 1))  # 1ms to 100ms equiv
        
        summary = collector.snapshot_summary()
        
        # P95 of 1..100 should be ~95
        assert summary["latency_p95_ms"] is not None
        assert 94000 <= summary["latency_p95_ms"] <= 96000  # rough check


class TestMetricsCollectorReset:
    """Reset functionality tests."""
    
    def test_reset_clears_all(self):
        """Reset clears counters and latencies."""
        collector = MetricsCollector()
        
        collector.start("m1")
        collector.end("m1", "FILLED", retry_count=1)
        collector.end("m2", "REJECTED", reason="test")
        
        # Verify something was recorded
        assert collector.snapshot_summary()["processed"] == 2
        
        collector.reset()
        
        summary = collector.snapshot_summary()
        assert summary["processed"] == 0
        assert summary["filled"] == 0
        assert summary["rejected"] == 0
        assert summary["retries"] == 0
        assert summary["latency_count"] == 0


class TestNoOpMetricsCollector:
    """NoOp collector tests."""
    
    def test_noop_does_nothing(self):
        """NoOp collector is a no-op."""
        noop = NoOpMetricsCollector()
        
        noop.start("m1")
        noop.end("m1", "FILLED")
        
        summary = noop.snapshot_summary()
        assert summary == {}
    
    def test_noop_reset_does_nothing(self):
        """NoOp reset is a no-op."""
        noop = NoOpMetricsCollector()
        noop.reset()  # Should not raise
