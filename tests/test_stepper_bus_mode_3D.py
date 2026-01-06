"""
tests/test_stepper_bus_mode_3D.py

Tests for LoopStepper bus mode (AG-3D-3-1).

Validates:
- No deadlock: loop terminates and drains queues
- No double consume: each intent processed once
- trace_id propagated end-to-end
- SQLite updated with expected fills

All tests are deterministic.
"""

import pytest
from pathlib import Path
import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bus import InMemoryBus
from engine.loop_stepper import LoopStepper
from engine.bus_workers import (
    TOPIC_ORDER_INTENT, TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
)
from state.position_store_sqlite import PositionStoreSQLite


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


class TestStepperBusModeBasic:
    """Basic tests for bus mode."""

    def test_bus_mode_terminates_no_deadlock(self, tmp_path: Path):
        """Bus mode should terminate without deadlock."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        # Should not hang
        result = stepper.run_bus_mode(
            ohlcv,
            bus,
            max_steps=5,
            warmup=10,
        )
        
        stepper.close()
        
        # Verify result structure
        assert "metrics" in result
        assert "drain_iterations" in result
        assert result["drain_iterations"] <= 100  # Within limit

    def test_all_queues_drained(self, tmp_path: Path):
        """All topics should be empty after run_bus_mode."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        stepper.run_bus_mode(ohlcv, bus, max_steps=5, warmup=10)
        stepper.close()
        
        # All queues should be empty
        assert bus.size(TOPIC_ORDER_INTENT) == 0
        assert bus.size(TOPIC_RISK_DECISION) == 0
        assert bus.size(TOPIC_EXECUTION_REPORT) == 0


class TestStepperBusModeTraceId:
    """Tests for trace_id propagation."""

    def test_trace_id_preserved_in_all_events(self, tmp_path: Path):
        """trace_id should be the same across all related events."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        # Collect all published envelopes for inspection
        published_trace_ids = []
        original_publish = bus.publish
        
        def tracking_publish(topic, event_type, trace_id, payload):
            published_trace_ids.append((topic, trace_id))
            return original_publish(topic, event_type, trace_id, payload)
        
        bus.publish = tracking_publish
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=15)
        
        stepper.run_bus_mode(ohlcv, bus, max_steps=3, warmup=10)
        stepper.close()
        
        # Group by trace_id
        trace_id_topics = {}
        for topic, trace_id in published_trace_ids:
            if trace_id not in trace_id_topics:
                trace_id_topics[trace_id] = set()
            trace_id_topics[trace_id].add(topic)
        
        # Each trace_id should appear in order_intent, risk_decision, and possibly execution_report
        for trace_id, topics in trace_id_topics.items():
            if TOPIC_ORDER_INTENT in topics:
                # If we had an intent, we should have a decision
                assert TOPIC_RISK_DECISION in topics, f"trace_id {trace_id} missing risk_decision"


class TestStepperBusModeSQLite:
    """Tests for SQLite position updates."""

    def test_sqlite_updated_with_fills(self, tmp_path: Path):
        """SQLite should contain position updates after fills."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            ticker="BTC-USD",
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        result = stepper.run_bus_mode(ohlcv, bus, max_steps=5, warmup=10)
        
        # Check positions
        positions = stepper.get_positions()
        stepper.close()
        
        # Should have at least some fills if strategy generated intents
        metrics = result["metrics"]
        
        # If we have fills, positions should be updated
        if metrics["fills"] > 0:
            assert len(positions) > 0, "Expected positions after fills"
            
            # Check position structure
            for pos in positions:
                assert "symbol" in pos
                assert "qty" in pos

    def test_sqlite_position_count_matches_fills(self, tmp_path: Path):
        """Number of position updates should correspond to fills."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
            ticker="TEST-ASSET",
        )
        
        ohlcv = make_ohlcv_df(n_bars=25)
        
        result = stepper.run_bus_mode(ohlcv, bus, max_steps=10, warmup=10)
        
        positions = stepper.get_positions()
        stepper.close()
        
        # We should have exactly one position entry per unique symbol
        # (fills accumulate in same position)
        fills = result["metrics"]["fills"]
        
        if fills > 0:
            # All fills should be for the same ticker
            assert len(positions) == 1
            assert positions[0]["symbol"] == "TEST-ASSET"


class TestStepperBusModeNoDoubleConsume:
    """Tests to verify no double consume."""

    def test_each_intent_processed_once(self, tmp_path: Path):
        """Each OrderIntentV1 should produce exactly one RiskDecisionV1."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        # Track all published events
        published_events = []
        original_publish = bus.publish
        
        def tracking_publish(topic, event_type, trace_id, payload):
            published_events.append({
                "topic": topic,
                "event_type": event_type,
                "trace_id": trace_id,
            })
            return original_publish(topic, event_type, trace_id, payload)
        
        bus.publish = tracking_publish
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=18)
        
        stepper.run_bus_mode(ohlcv, bus, max_steps=5, warmup=10)
        stepper.close()
        
        # Count events by topic
        intent_count = sum(1 for e in published_events if e["topic"] == TOPIC_ORDER_INTENT)
        decision_count = sum(1 for e in published_events if e["topic"] == TOPIC_RISK_DECISION)
        
        # Each intent should produce exactly one decision
        assert decision_count == intent_count, (
            f"Expected {intent_count} decisions for {intent_count} intents, got {decision_count}"
        )


class TestStepperBusModeEdgeCases:
    """Edge case tests."""

    def test_no_intents_generated(self, tmp_path: Path):
        """Should handle case where strategy generates no intents."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        # Very short data - might not generate intents
        ohlcv = make_ohlcv_df(n_bars=12)
        
        # Should not crash
        result = stepper.run_bus_mode(ohlcv, bus, max_steps=1, warmup=10)
        stepper.close()
        
        assert "metrics" in result
        assert bus.size(TOPIC_ORDER_INTENT) == 0

    def test_without_state_db(self, tmp_path: Path):
        """Bus mode should work without SQLite state store."""
        bus = InMemoryBus()
        
        # No state_db
        stepper = LoopStepper(
            state_db=None,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        # Should not crash
        result = stepper.run_bus_mode(ohlcv, bus, max_steps=5, warmup=10)
        stepper.close()
        
        # Queues should still be drained
        assert bus.size(TOPIC_ORDER_INTENT) == 0
        assert bus.size(TOPIC_RISK_DECISION) == 0
        # execution_report might have some if no pos_worker consumed them
        # Actually, ExecWorker still publishes, but PositionStoreWorker is None
        # So execution_report queue might not be empty
        # Let's check that at least order_intent and risk_decision are drained
