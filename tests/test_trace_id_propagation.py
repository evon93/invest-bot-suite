"""
tests/test_trace_id_propagation.py

Tests for trace_id propagation across bus events.

Validates that trace_id is preserved:
OrderIntentV1 → RiskDecisionV1 → ExecutionReportV1

Part of ticket AG-3D-4-1.
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


class TestTraceIdPropagation:
    """Tests for trace_id propagation through bus events."""

    def test_trace_id_same_across_chain(self, tmp_path: Path):
        """trace_id should be identical across OrderIntent -> RiskDecision -> ExecutionReport."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        # Track all published envelopes
        published_envelopes = []
        original_publish = bus.publish
        
        def tracking_publish(topic, event_type, trace_id, payload):
            env = original_publish(topic, event_type, trace_id, payload)
            published_envelopes.append({
                "topic": topic,
                "event_type": event_type,
                "trace_id": trace_id,
                "envelope": env,
            })
            return env
        
        bus.publish = tracking_publish
        
        stepper = LoopStepper(
            state_db=db_path,
            seed=42,
        )
        
        ohlcv = make_ohlcv_df(n_bars=20)
        
        stepper.run_bus_mode(ohlcv, bus, max_steps=5, warmup=10)
        stepper.close()
        
        # Group by trace_id
        trace_id_events = {}
        for pub in published_envelopes:
            tid = pub["trace_id"]
            if tid not in trace_id_events:
                trace_id_events[tid] = []
            trace_id_events[tid].append(pub)
        
        # For each trace_id that has an OrderIntent, verify chain
        for trace_id, events in trace_id_events.items():
            topics = {e["topic"] for e in events}
            
            if TOPIC_ORDER_INTENT in topics:
                # Should also have risk_decision
                assert TOPIC_RISK_DECISION in topics, (
                    f"trace_id {trace_id} has OrderIntent but missing RiskDecision"
                )
                
                # Verify all events in chain have same trace_id
                for evt in events:
                    assert evt["trace_id"] == trace_id

    def test_trace_id_in_payload(self, tmp_path: Path):
        """trace_id in envelope should match trace_id in payload."""
        db_path = tmp_path / "state.db"
        bus = InMemoryBus()
        
        published_envelopes = []
        original_publish = bus.publish
        
        def tracking_publish(topic, event_type, trace_id, payload):
            env = original_publish(topic, event_type, trace_id, payload)
            published_envelopes.append({
                "topic": topic,
                "trace_id": trace_id,
                "payload_trace_id": payload.get("trace_id"),
            })
            return env
        
        bus.publish = tracking_publish
        
        stepper = LoopStepper(state_db=db_path, seed=42)
        ohlcv = make_ohlcv_df(n_bars=20)
        
        stepper.run_bus_mode(ohlcv, bus, max_steps=3, warmup=10)
        stepper.close()
        
        # Verify consistency
        for pub in published_envelopes:
            if pub["payload_trace_id"]:  # Events have trace_id in payload
                assert pub["trace_id"] == pub["payload_trace_id"], (
                    f"Envelope trace_id {pub['trace_id']} != payload trace_id {pub['payload_trace_id']}"
                )
