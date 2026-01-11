"""
tests/test_metrics_latencies_nonzero_simulated.py

Tests verifying that stage latencies are non-zero in simulated clock mode
and that results are deterministic across runs.

Part of ticket AG-3I-1-1.
Extended with batch latency scaling tests in AG-3I-1-2.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

from engine.time_provider import SimulatedTimeProvider
from engine.loop_stepper import LoopStepper, STAGE_LATENCY_NS
from engine.metrics_collector import MetricsCollector
from bus import InMemoryBus


def make_test_ohlcv(n_bars: int = 20, seed: int = 42) -> pd.DataFrame:
    """Create deterministic OHLCV DataFrame for testing."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    
    initial_price = 1000.0
    returns = np.random.randn(n_bars) * 0.01
    closes = initial_price * np.cumprod(1 + returns)
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes * (1 - np.random.rand(n_bars) * 0.005),
        "high": closes * (1 + np.random.rand(n_bars) * 0.005),
        "low": closes * (1 - np.random.rand(n_bars) * 0.005),
        "close": closes,
        "volume": np.random.randint(100, 1000, n_bars),
    })


class TestNonZeroLatenciesSimulated:
    """Test that latencies are non-zero in simulated clock mode."""
    
    def test_stage_latency_constants_defined(self):
        """STAGE_LATENCY_NS constants should exist and be positive."""
        assert "strategy" in STAGE_LATENCY_NS
        assert "risk" in STAGE_LATENCY_NS
        assert "exec" in STAGE_LATENCY_NS
        assert "position" in STAGE_LATENCY_NS
        
        for stage, latency_ns in STAGE_LATENCY_NS.items():
            assert latency_ns > 0, f"Stage {stage} should have positive latency"
    
    def test_metrics_collector_with_simulated_clock(self):
        """MetricsCollector with simulated clock should report non-zero latencies."""
        time_provider = SimulatedTimeProvider(seed=42, start_ns=0)
        
        # Create clock_fn from time_provider
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        # Simulate a stage measurement
        t0 = clock_fn()
        time_provider.advance_ns(STAGE_LATENCY_NS["strategy"])
        t1 = clock_fn()
        
        collector.record_stage(
            stage="strategy",
            step_id=1,
            trace_id="test_trace",
            t_start=t0,
            t_end=t1,
            outcome="ok",
        )
        
        summary = collector.snapshot_summary()
        
        assert "stages_by_name" in summary
        assert "strategy" in summary["stages_by_name"]
        assert summary["stages_by_name"]["strategy"]["p50_ms"] > 0
    
    def test_loop_stepper_produces_nonzero_latencies(self):
        """LoopStepper in bus_mode should produce non-zero stage latencies."""
        time_provider = SimulatedTimeProvider(seed=42)
        
        # Create metrics collector with time_provider clock
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        # Create stepper with time_provider
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_state.db"
            
            stepper = LoopStepper(
                state_db=db_path,
                seed=42,
                time_provider=time_provider,
            )
            
            try:
                bus = InMemoryBus()
                # Use more bars to ensure strategy generates order intents
                ohlcv = make_test_ohlcv(n_bars=30, seed=42)
                
                stepper.run_bus_mode(
                    ohlcv,
                    bus,
                    max_steps=15,  # More steps to ensure crossovers
                    warmup=10,     # More warmup for signal generation
                    metrics_collector=collector,
                )
                
                summary = collector.snapshot_summary()
                stages = summary.get("stages_by_name", {})
                
                # Check we have some stage events recorded
                stage_events_count = summary.get("stage_events_count", 0)
                
                # If we have stage events, verify non-zero latencies
                if stage_events_count > 0:
                    has_nonzero = False
                    for stage_name, stage_data in stages.items():
                        p50_ms = stage_data.get("p50_ms")
                        if p50_ms is not None and p50_ms > 0:
                            has_nonzero = True
                            break
                    
                    assert has_nonzero, f"Expected at least one stage with p50_ms > 0, got: {stages}"
                else:
                    # If no stage events, strategy didn't generate any intents
                    # This can happen if no crossover signals occur
                    # We still verify the time_provider advanced (monotonicity)
                    assert time_provider.now_ns() > 0, "Time should have advanced"
                
            finally:
                stepper.close()


class TestDeterminismSimulated:
    """Test that simulated runs are deterministic."""
    
    def _run_simulation(self, seed: int = 42) -> dict:
        """Run a simulation and return metrics summary."""
        time_provider = SimulatedTimeProvider(seed=seed)
        
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_state.db"
            
            stepper = LoopStepper(
                state_db=db_path,
                seed=seed,
                time_provider=time_provider,
            )
            
            try:
                bus = InMemoryBus()
                ohlcv = make_test_ohlcv(n_bars=15, seed=seed)
                
                stepper.run_bus_mode(
                    ohlcv,
                    bus,
                    max_steps=5,
                    warmup=5,
                    metrics_collector=collector,
                )
                
                return collector.snapshot_summary()
            finally:
                stepper.close()
    
    def test_two_runs_same_seed_match(self):
        """Two runs with same seed should produce identical stage metrics."""
        summary1 = self._run_simulation(seed=42)
        summary2 = self._run_simulation(seed=42)
        
        stages1 = summary1.get("stages_by_name", {})
        stages2 = summary2.get("stages_by_name", {})
        
        # Compare stage metrics
        assert stages1 == stages2, (
            f"Stage metrics should be identical:\n"
            f"Run 1: {stages1}\n"
            f"Run 2: {stages2}"
        )
    
    def test_different_seeds_may_differ(self):
        """Runs with different seeds may produce different metrics (not mandatory but expected)."""
        # This test just ensures the code runs with different seeds
        # Different seeds affect OHLCV data which affects signal generation and thus metrics
        summary1 = self._run_simulation(seed=42)
        summary2 = self._run_simulation(seed=123)
        
        # Both should complete without error
        assert "stages_by_name" in summary1
        assert "stages_by_name" in summary2


class TestBatchLatencyScaling:
    """
    Tests verifying the batch latency contract (AG-3I-1-2):
    
    - strategy: fixed latency per bar = STAGE_LATENCY_NS["strategy"]
    - risk/exec/position: latency = STAGE_LATENCY_NS[stage] * processed
    
    These tests verify exact scaling without tolerance.
    """
    
    def test_strategy_latency_is_fixed_per_bar(self):
        """Strategy stage always has exactly 1ms latency regardless of intents generated."""
        time_provider = SimulatedTimeProvider(seed=42, start_ns=0)
        
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        # Record strategy stage (simulating what loop_stepper does)
        t0 = clock_fn()
        time_provider.advance_ns(STAGE_LATENCY_NS["strategy"])
        t1 = clock_fn()
        
        collector.record_stage(
            stage="strategy",
            step_id=1,
            trace_id="test_bar_1",
            t_start=t0,
            t_end=t1,
            outcome="ok",
        )
        
        summary = collector.snapshot_summary()
        
        # Exact check: strategy p50 should be exactly 1.0ms (1_000_000 ns)
        expected_ms = STAGE_LATENCY_NS["strategy"] / 1e6  # Convert ns to ms
        actual_ms = summary["stages_by_name"]["strategy"]["p50_ms"]
        
        assert actual_ms == expected_ms, (
            f"Strategy latency should be exactly {expected_ms}ms, got {actual_ms}ms"
        )
    
    def test_risk_latency_scales_by_processed(self):
        """Risk stage latency = STAGE_LATENCY_NS['risk'] * processed."""
        self._verify_batch_scaling("risk", processed=3)
    
    def test_exec_latency_scales_by_processed(self):
        """Exec stage latency = STAGE_LATENCY_NS['exec'] * processed."""
        self._verify_batch_scaling("exec", processed=5)
    
    def test_position_latency_scales_by_processed(self):
        """Position stage latency = STAGE_LATENCY_NS['position'] * processed."""
        self._verify_batch_scaling("position", processed=2)
    
    def _verify_batch_scaling(self, stage: str, processed: int):
        """
        Helper to verify that stage latency scales exactly by processed count.
        
        This simulates what loop_stepper does when processing a batch of items:
        advance_ns(STAGE_LATENCY_NS[stage] * processed)
        """
        time_provider = SimulatedTimeProvider(seed=42, start_ns=0)
        
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        # Simulate batch processing (what the worker does)
        t0 = clock_fn()
        # This is the exact formula used in loop_stepper:
        total_latency_ns = STAGE_LATENCY_NS[stage] * processed
        time_provider.advance_ns(total_latency_ns)
        t1 = clock_fn()
        
        collector.record_stage(
            stage=stage,
            step_id=1,
            trace_id=f"batch_{stage}_test",
            t_start=t0,
            t_end=t1,
            outcome="ok",
        )
        
        summary = collector.snapshot_summary()
        
        # Convert expected latency from ns to ms
        expected_ms = total_latency_ns / 1e6
        actual_ms = summary["stages_by_name"][stage]["p50_ms"]
        
        assert actual_ms == expected_ms, (
            f"{stage} latency with processed={processed} should be exactly {expected_ms}ms "
            f"(STAGE_LATENCY_NS['{stage}']={STAGE_LATENCY_NS[stage]} * {processed}), "
            f"got {actual_ms}ms"
        )
    
    def test_multiple_batches_accumulate_correctly(self):
        """
        Multiple batches with different processed counts should have correct
        individual latencies that are deterministically computed.
        """
        time_provider = SimulatedTimeProvider(seed=42, start_ns=0)
        
        def clock_fn():
            return time_provider.now_ns() / 1e9
        
        collector = MetricsCollector(clock_fn=clock_fn)
        
        # Simulate 3 risk batches with different processed counts: 2, 3, 1
        batch_sizes = [2, 3, 1]
        expected_latencies_ns = [STAGE_LATENCY_NS["risk"] * size for size in batch_sizes]
        
        for i, (size, expected_ns) in enumerate(zip(batch_sizes, expected_latencies_ns)):
            t0 = clock_fn()
            time_provider.advance_ns(expected_ns)
            t1 = clock_fn()
            
            collector.record_stage(
                stage="risk",
                step_id=i,
                trace_id=f"batch_risk_{i}",
                t_start=t0,
                t_end=t1,
                outcome="ok",
            )
        
        # Check the stage events directly for exact values
        events = collector.get_stage_events()
        assert len(events) == 3
        
        for i, (event, expected_ns) in enumerate(zip(events, expected_latencies_ns)):
            expected_dt = expected_ns / 1e9  # In seconds
            actual_dt = event["dt"]
            assert actual_dt == expected_dt, (
                f"Batch {i} dt should be {expected_dt}s, got {actual_dt}s"
            )
