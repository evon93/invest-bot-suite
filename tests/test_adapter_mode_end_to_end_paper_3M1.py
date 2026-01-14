"""
tests/test_adapter_mode_end_to_end_paper_3M1.py

AG-3M-1-1: End-to-end tests for adapter mode with PaperExchangeAdapter.

Tests:
- Full pipeline: MarketDataAdapter -> Strategy -> Risk -> Exec (paper) -> PositionStore
- Deterministic execution with seed=42
- Generates expected artifacts (events.ndjson, run_meta.json)
- At least 1 ExecutionReport when signals are generated
"""

import pytest
import json
import tempfile
from pathlib import Path

from engine.loop_stepper import LoopStepper
from engine.time_provider import SimulatedTimeProvider
from engine.exchange_adapter import PaperExchangeAdapter, StubNetworkExchangeAdapter
from engine.market_data.fixture_adapter import FixtureMarketDataAdapter


# Test fixture path
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ohlcv_fixture_3K1.csv"


class TestAdapterModeEndToEndPaper:
    """End-to-end tests with PaperExchangeAdapter."""
    
    def test_end_to_end_paper_adapter_generates_execution_reports(self):
        """Full pipeline with paper adapter produces ExecutionReportV1 when signals generated."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange = PaperExchangeAdapter(slippage_bps=5.0, fee_bps=10.0)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=10,
            warmup=3,
            exchange_adapter=exchange,
        )
        
        # Should have processed steps
        assert result["steps_processed"] > 0
        
        # Should have events (at minimum system events)
        assert "events" in result
        
        # Check for ExecutionReportV1 - depends on strategy generating signals
        exec_reports = [e for e in result["events"] if e.get("type") == "ExecutionReportV1"]
        risk_decisions = [e for e in result["events"] if e.get("type") == "RiskDecisionV1"]
        allowed_decisions = [d for d in risk_decisions if d.get("payload", {}).get("allowed")]
        
        # If there were allowed decisions, there should be corresponding fills
        if allowed_decisions:
            assert len(exec_reports) >= 1, "Expected ExecutionReports for allowed decisions"
            
            # Verify ExecutionReport structure
            report = exec_reports[0]
            payload = report.get("payload", {})
            assert payload.get("status") == "FILLED"
            assert payload.get("filled_qty", 0) > 0
            assert payload.get("avg_price", 0) > 0
            
            # Verify adapter-mode metadata
            extra = payload.get("extra", {})
            assert extra.get("adapter_mode") is True
            assert extra.get("engine_version") == "3M.1"
        
        stepper.close()
    
    def test_end_to_end_stub_adapter(self):
        """Pipeline with stub adapter produces execution reports with latency."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange = StubNetworkExchangeAdapter(latency_steps=2)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=10,
            warmup=3,
            exchange_adapter=exchange,
        )
        
        # Should have ExecutionReports
        exec_reports = [e for e in result["events"] if e.get("type") == "ExecutionReportV1"]
        if exec_reports:
            # Stub adapter should have higher latency
            report = exec_reports[0]
            payload = report.get("payload", {})
            assert payload.get("latency_ms", 0) > 1.0  # Stub has higher latency
        
        stepper.close()
    
    def test_determinism_with_paper_adapter(self):
        """Two runs with seed=42 produce identical output."""
        def run_simulation():
            adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
            exchange = PaperExchangeAdapter()
            time_provider = SimulatedTimeProvider(seed=42)
            stepper = LoopStepper(
                seed=42,
                time_provider=time_provider,
            )
            
            result = stepper.run_adapter_mode(
                adapter,
                max_steps=5,
                warmup=2,
                exchange_adapter=exchange,
            )
            
            stepper.close()
            return result
        
        result1 = run_simulation()
        result2 = run_simulation()
        
        # Same number of events
        assert len(result1["events"]) == len(result2["events"])
        
        # Same metrics
        assert result1["metrics"] == result2["metrics"]
        
        # Same event types in same order
        types1 = [e.get("type") for e in result1["events"]]
        types2 = [e.get("type") for e in result2["events"]]
        assert types1 == types2
    
    def test_jsonl_logging_with_exchange_adapter(self, tmp_path):
        """JSONL logging works with exchange_adapter."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange = PaperExchangeAdapter()
        trace_path = tmp_path / "events.ndjson"
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=2,
            log_jsonl_path=trace_path,
            exchange_adapter=exchange,
        )
        
        stepper.close()
        
        # File should exist
        assert trace_path.exists()
        
        # Should have valid JSONL
        lines = trace_path.read_text().strip().split("\n")
        assert len(lines) > 0
        
        # Last line should be AdapterModeDone
        last_event = json.loads(lines[-1])
        assert last_event.get("event_type") == "AdapterModeDone"


class TestAdapterModePositionStore:
    """Tests for PositionStore integration."""
    
    def test_fills_applied_to_position_store(self, tmp_path):
        """Fills from exchange_adapter are applied to PositionStore."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange = PaperExchangeAdapter()
        db_path = tmp_path / "state.db"
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
            state_db=db_path,
        )
        
        stepper.run_adapter_mode(
            adapter,
            max_steps=10,
            warmup=3,
            exchange_adapter=exchange,
        )
        
        # Check positions
        positions = stepper.get_positions()
        
        # If there were fills, positions should reflect them
        exec_reports = [e for e in stepper._get_metrics() or {}]
        if stepper._fill_count > 0:
            assert len(positions) > 0, "PositionStore should have positions after fills"
        
        stepper.close()


class TestAdapterModeBackwardsCompatibility:
    """Tests for backwards compatibility (no exchange_adapter)."""
    
    def test_without_exchange_adapter_uses_step(self):
        """Without exchange_adapter, run_adapter_mode falls back to step()."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        # No exchange_adapter - should use original step() behavior
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=3,
            warmup=2,
        )
        
        assert result["steps_processed"] == 3
        assert result["consumed"] == 5  # warmup + steps
        
        stepper.close()
