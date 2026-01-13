"""
tests/test_loop_stepper_market_data_integration_3L1.py

Integration tests for LoopStepper.run_adapter_mode() consuming MarketDataAdapter.

AG-3L-1-1: Validates:
- Adapter mode consumes events via poll()
- Determinism with seed=42
- Produces expected events/metrics
"""

import pytest
from pathlib import Path
import json

import pandas as pd

from engine.loop_stepper import LoopStepper
from engine.time_provider import SimulatedTimeProvider
from engine.market_data.fixture_adapter import FixtureMarketDataAdapter


# Test fixture path
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ohlcv_fixture_3K1.csv"


class TestAdapterModeBasic:
    """Basic tests for run_adapter_mode()."""
    
    def test_adapter_mode_consumes_via_poll(self):
        """run_adapter_mode consumes events through adapter.poll()."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        initial_remaining = adapter.remaining()
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=3,
            warmup=2,
        )
        
        # Verify events were consumed
        assert adapter.remaining() < initial_remaining
        # Consumed = warmup + steps
        expected_consumed = 2 + 3  # warmup=2, max_steps=3
        assert result["consumed"] == expected_consumed
        # Steps processed
        assert result["steps_processed"] == 3
        
        stepper.close()
    
    def test_adapter_mode_returns_events(self):
        """run_adapter_mode returns list of events."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=3,
        )
        
        # Should have events (intents, decisions, reports)
        assert "events" in result
        assert isinstance(result["events"], list)
        
        stepper.close()
    
    def test_adapter_mode_respects_max_steps(self):
        """run_adapter_mode stops after max_steps."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        # Fixture has 10 bars, warmup=2, max_steps=3 → should stop at 5 consumed
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=3,
            warmup=2,
        )
        
        assert result["steps_processed"] == 3
        assert result["consumed"] == 5  # 2 warmup + 3 steps
        # Adapter should still have remaining
        assert adapter.remaining() == 5
        
        stepper.close()


class TestAdapterModeDeterminism:
    """Determinism tests for run_adapter_mode()."""
    
    def test_same_seed_produces_identical_output(self):
        """Two runs with seed=42 produce identical events."""
        def run_simulation():
            adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
            time_provider = SimulatedTimeProvider(seed=42)
            stepper = LoopStepper(
                seed=42,
                time_provider=time_provider,
            )
            
            result = stepper.run_adapter_mode(
                adapter,
                max_steps=3,
                warmup=2,
            )
            
            stepper.close()
            return result
        
        result1 = run_simulation()
        result2 = run_simulation()
        
        # Same number of events
        assert len(result1["events"]) == len(result2["events"])
        
        # Same event types
        types1 = [e.get("type") for e in result1["events"]]
        types2 = [e.get("type") for e in result2["events"]]
        assert types1 == types2
        
        # Same metrics
        assert result1["metrics"] == result2["metrics"]
    
    def test_different_seed_produces_different_output(self):
        """Runs with different seeds typically produce different events."""
        def run_simulation(seed):
            adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
            time_provider = SimulatedTimeProvider(seed=seed)
            stepper = LoopStepper(
                seed=seed,
                time_provider=time_provider,
            )
            
            result = stepper.run_adapter_mode(
                adapter,
                max_steps=3,
                warmup=2,
            )
            
            stepper.close()
            return result
        
        result1 = run_simulation(42)
        result2 = run_simulation(12345)
        
        # Events should have different trace_ids (random based on seed)
        if result1["events"] and result2["events"]:
            trace1 = result1["events"][0].get("payload", {}).get("trace_id", "")
            trace2 = result2["events"][0].get("payload", {}).get("trace_id", "")
            assert trace1 != trace2


class TestAdapterModeJsonl:
    """JSONL logging tests for run_adapter_mode()."""
    
    def test_produces_events_ndjson(self, tmp_path):
        """run_adapter_mode with log_jsonl_path creates NDJSON file."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        trace_path = tmp_path / "events.ndjson"
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        stepper.run_adapter_mode(
            adapter,
            max_steps=3,
            warmup=2,
            log_jsonl_path=trace_path,
        )
        
        stepper.close()
        
        # File should exist
        assert trace_path.exists()
        
        # Should have valid JSONL content
        lines = trace_path.read_text().strip().split("\n")
        assert len(lines) > 0
        
        # Last line should be AdapterModeDone
        last_event = json.loads(lines[-1])
        assert last_event.get("event_type") == "AdapterModeDone"


class TestAdapterModeWarmup:
    """Warmup behavior tests."""
    
    def test_insufficient_warmup_returns_early(self):
        """If adapter has less data than warmup, returns early with empty events."""
        # Create adapter with only 3 bars, but request warmup=5
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        # Consume most events first
        adapter.poll(max_items=8)  # Leave only 2
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=5,  # Need 5 but only 2 available
        )
        
        # Should return early with no events
        assert result["events"] == []
        assert result["consumed"] == 2  # Consumed what was available during warmup attempt
        
        stepper.close()
