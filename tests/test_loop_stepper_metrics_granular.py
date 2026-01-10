"""
tests/test_loop_stepper_metrics_granular.py

Tests for granular metrics observability (AG-3H-1-1).

Validates:
- Stage events are recorded (strategy, risk, exec, position)
- Summary includes stages_by_name and outcomes_by_stage
- Determinism: two identical runs produce identical summary
"""

import json
import pytest
from pathlib import Path
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper
from engine.metrics_collector import MetricsCollector, MetricsWriter, NoOpMetricsCollector
from engine.time_provider import SimulatedTimeProvider


def make_ohlcv_df(n_bars: int = 20, seed: int = 42) -> pd.DataFrame:
    """Create deterministic OHLCV DataFrame for testing."""
    np.random.seed(seed)
    
    dates = pd.date_range("2024-01-01", periods=n_bars, freq="1h", tz="UTC")
    closes = 100.0 + np.cumsum(np.random.randn(n_bars) * 2)
    
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes - 0.5,
        "high": closes + 1.0,
        "low": closes - 1.0,
        "close": closes,
        "volume": np.random.randint(1000, 10000, n_bars),
    })


class TestGranularMetricsFilesCreated:
    """Test that metrics files are created with stage data."""
    
    def test_metrics_ndjson_and_summary_created(self, tmp_path: Path):
        """Run with metrics enabled creates both files."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        # Create time provider and collector
        time_provider = SimulatedTimeProvider(seed=42)
        collector = MetricsCollector()
        writer = MetricsWriter(run_dir=tmp_path)
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            time_provider=time_provider,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        # Run with metrics
        collector.start("run_main")
        result = stepper.run_bus_mode(
            ohlcv,
            bus,
            max_steps=5,
            warmup=10,
            metrics_collector=collector,
        )
        collector.end("run_main", status="FILLED")
        
        # Write events and summary
        for event in collector.get_stage_events():
            writer.append_event(event)
        writer.write_summary(collector.snapshot_summary())
        writer.close()
        stepper.close()
        
        # Verify files exist
        ndjson_path = tmp_path / "metrics.ndjson"
        summary_path = tmp_path / "metrics_summary.json"
        
        assert ndjson_path.exists(), "metrics.ndjson not created"
        assert summary_path.exists(), "metrics_summary.json not created"
        
        # Verify NDJSON has content
        with open(ndjson_path, "r") as f:
            lines = f.readlines()
        assert len(lines) > 0, "metrics.ndjson is empty"
        
        # Verify each line is valid JSON with stage field
        for line in lines:
            event = json.loads(line)
            assert "stage" in event
            assert "step_id" in event
            assert "trace_id" in event


class TestGranularMetricsStagesPresent:
    """Test that summary includes stage-level metrics."""
    
    def test_summary_contains_stages_by_name(self, tmp_path: Path):
        """Summary should have stages_by_name with latency percentiles."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        time_provider = SimulatedTimeProvider(seed=42)
        collector = MetricsCollector()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            time_provider=time_provider,
        )
        
        ohlcv = make_ohlcv_df(n_bars=25)
        
        stepper.run_bus_mode(
            ohlcv,
            bus,
            max_steps=10,
            warmup=10,
            metrics_collector=collector,
        )
        stepper.close()
        
        summary = collector.snapshot_summary()
        
        # Check structure
        assert "stages_by_name" in summary
        assert "outcomes_by_stage" in summary
        assert "stage_events_count" in summary
        
        stages = summary["stages_by_name"]
        
        # At minimum, we expect strategy stage (intents published)
        # Risk, exec, position may also appear if there was activity
        assert len(stages) >= 1, f"Expected at least 1 stage, got: {stages}"
        
        # Verify stage structure
        for stage_name, stage_data in stages.items():
            assert "count" in stage_data
            assert "p50_ms" in stage_data
            assert "p95_ms" in stage_data
    
    def test_outcomes_by_stage_structure(self, tmp_path: Path):
        """Outcomes should be per-stage counters."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        time_provider = SimulatedTimeProvider(seed=42)
        collector = MetricsCollector()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            time_provider=time_provider,
        )
        
        ohlcv = make_ohlcv_df(n_bars=25)
        
        stepper.run_bus_mode(
            ohlcv,
            bus,
            max_steps=10,
            warmup=10,
            metrics_collector=collector,
        )
        stepper.close()
        
        summary = collector.snapshot_summary()
        outcomes = summary["outcomes_by_stage"]
        
        # Each stage should have outcome counters
        for stage_name, stage_outcomes in outcomes.items():
            assert isinstance(stage_outcomes, dict)
            # "ok" should be present for successful processing
            assert "ok" in stage_outcomes


class TestGranularMetricsDeterminism:
    """Test that metrics are deterministic across runs."""
    
    def test_two_identical_runs_same_summary(self, tmp_path: Path):
        """Two runs with same seed produce identical summary."""
        
        def run_simulation(run_dir: Path, seed: int = 42) -> dict:
            db_path = run_dir / "state.db"
            bus = InMemoryBus()
            
            time_provider = SimulatedTimeProvider(seed=seed)
            collector = MetricsCollector()
            
            stepper = LoopStepper(
                state_db=db_path,
                seed=seed,
                time_provider=time_provider,
            )
            
            ohlcv = make_ohlcv_df(n_bars=20, seed=seed)
            
            stepper.run_bus_mode(
                ohlcv,
                bus,
                max_steps=5,
                warmup=10,
                metrics_collector=collector,
            )
            stepper.close()
            
            return collector.snapshot_summary()
        
        run_a = tmp_path / "run_a"
        run_b = tmp_path / "run_b"
        run_a.mkdir()
        run_b.mkdir()
        
        summary_a = run_simulation(run_a, seed=42)
        summary_b = run_simulation(run_b, seed=42)
        
        # Compare summaries - should be identical
        # We serialize and compare to catch subtle differences
        json_a = json.dumps(summary_a, sort_keys=True)
        json_b = json.dumps(summary_b, sort_keys=True)
        
        assert json_a == json_b, (
            f"Summaries differ:\nRun A: {json_a[:500]}\nRun B: {json_b[:500]}"
        )


class TestGranularMetricsWithNoOpCollector:
    """Test that NoOpMetricsCollector doesn't crash."""
    
    def test_noop_collector_no_crash(self, tmp_path: Path):
        """NoOp collector should work without errors."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        time_provider = SimulatedTimeProvider(seed=42)
        collector = NoOpMetricsCollector()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            time_provider=time_provider,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        # Should not crash
        stepper.run_bus_mode(
            ohlcv,
            bus,
            max_steps=5,
            warmup=10,
            metrics_collector=collector,
        )
        stepper.close()
        
        # NoOp returns empty
        assert collector.snapshot_summary() == {}
        assert collector.get_stage_events() == []


class TestRecordStageDirectly:
    """Direct unit tests for record_stage method."""
    
    def test_record_stage_stores_event(self):
        """record_stage should store event with all fields."""
        collector = MetricsCollector()
        
        collector.record_stage(
            stage="strategy",
            step_id=1,
            trace_id="trace-123",
            t_start=0.0,
            t_end=0.001,
            outcome="ok",
        )
        
        events = collector.get_stage_events()
        assert len(events) == 1
        
        event = events[0]
        assert event["stage"] == "strategy"
        assert event["step_id"] == 1
        assert event["trace_id"] == "trace-123"
        assert event["t_start"] == 0.0
        assert event["t_end"] == 0.001
        assert event["dt"] == 0.001
        assert event["outcome"] == "ok"
    
    def test_record_stage_aggregates_latencies(self):
        """Multiple record_stage calls should aggregate latencies per stage."""
        collector = MetricsCollector()
        
        # Record multiple strategy stages
        for i in range(5):
            collector.record_stage(
                stage="strategy",
                step_id=i,
                trace_id=f"trace-{i}",
                t_start=float(i),
                t_end=float(i) + 0.002,  # 2ms each
                outcome="ok",
            )
        
        # Record a few risk stages
        for i in range(3):
            collector.record_stage(
                stage="risk",
                step_id=i,
                trace_id=f"risk-{i}",
                t_start=float(i),
                t_end=float(i) + 0.001,  # 1ms each
                outcome="ok",
            )
        
        summary = collector.snapshot_summary()
        stages = summary["stages_by_name"]
        
        assert "strategy" in stages
        assert "risk" in stages
        
        assert stages["strategy"]["count"] == 5
        assert stages["risk"]["count"] == 3
        
        # Check latencies make sense (2ms for strategy)
        assert stages["strategy"]["p50_ms"] == 2.0
        assert stages["risk"]["p50_ms"] == 1.0
    
    def test_record_stage_with_rejection(self):
        """record_stage should handle rejected outcomes."""
        collector = MetricsCollector()
        
        collector.record_stage(
            stage="risk",
            step_id=1,
            trace_id="trace-1",
            t_start=0.0,
            t_end=0.001,
            outcome="rejected",
            reason="dd_guardrail",
        )
        
        events = collector.get_stage_events()
        assert len(events) == 1
        assert events[0]["outcome"] == "rejected"
        assert events[0]["reason"] == "dd_guardrail"
        
        summary = collector.snapshot_summary()
        assert summary["outcomes_by_stage"]["risk"]["rejected"] == 1
