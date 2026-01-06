"""
tests/test_inmemory_bus_roundtrip.py

Tests for InMemoryBus roundtrip and determinism.

Validates:
- Publish + poll roundtrip
- JSON serialization roundtrip
- Monotonic seq ordering
- FIFO behavior
- Empty poll returns []
- trace_id preservation

Part of ticket AG-3D-2-1.
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bus import InMemoryBus, BusEnvelope, BusBase


class TestBusEnvelope:
    """Tests for BusEnvelope dataclass."""

    def test_envelope_is_frozen(self):
        """BusEnvelope should be immutable."""
        env = BusEnvelope(
            seq=1,
            topic="test",
            event_type="TestEvent",
            trace_id="T-001",
            payload={"key": "value"},
        )
        
        with pytest.raises(AttributeError):
            env.seq = 2  # type: ignore

    def test_to_dict(self):
        """to_dict should return serializable dict."""
        env = BusEnvelope(
            seq=1,
            topic="order_intent",
            event_type="OrderIntentV1",
            trace_id="T-0001",
            payload={"qty": 10, "side": "buy"},
        )
        
        d = env.to_dict()
        
        assert d["seq"] == 1
        assert d["topic"] == "order_intent"
        assert d["event_type"] == "OrderIntentV1"
        assert d["trace_id"] == "T-0001"
        assert d["payload"] == {"qty": 10, "side": "buy"}


class TestInMemoryBusBasic:
    """Basic tests for InMemoryBus."""

    def test_implements_protocol(self):
        """InMemoryBus should implement BusBase protocol."""
        bus = InMemoryBus()
        assert isinstance(bus, BusBase)

    def test_publish_returns_envelope(self):
        """publish should return BusEnvelope with assigned seq."""
        bus = InMemoryBus()
        
        env = bus.publish(
            topic="order_intent",
            event_type="OrderIntentV1",
            trace_id="T-0001",
            payload={"qty": 10},
        )
        
        assert isinstance(env, BusEnvelope)
        assert env.seq == 1
        assert env.topic == "order_intent"
        assert env.trace_id == "T-0001"

    def test_poll_empty_returns_empty_list(self):
        """poll on empty topic should return []."""
        bus = InMemoryBus()
        
        result = bus.poll("nonexistent_topic")
        
        assert result == []

    def test_size_empty_topic(self):
        """size on empty topic should return 0."""
        bus = InMemoryBus()
        
        assert bus.size("order_intent") == 0


class TestInMemoryBusRoundtrip:
    """Roundtrip tests for InMemoryBus."""

    def test_publish_poll_roundtrip(self):
        """publish + poll should return same envelope."""
        bus = InMemoryBus()
        
        published = bus.publish(
            topic="order_intent",
            event_type="OrderIntentV1",
            trace_id="T-0001",
            payload={"qty": 10, "side": "buy"},
        )
        
        polled = bus.poll("order_intent", max_items=1)
        
        assert len(polled) == 1
        assert polled[0] == published
        assert polled[0].trace_id == "T-0001"
        assert polled[0].payload == {"qty": 10, "side": "buy"}

    def test_json_roundtrip_deterministic(self):
        """JSON serialization should be deterministic."""
        bus = InMemoryBus()
        payload = {"qty": 10, "side": "buy", "asset": "BTC-USD"}
        
        bus.publish(
            topic="order_intent",
            event_type="OrderIntentV1",
            trace_id="T-0001",
            payload=payload,
        )
        
        polled = bus.poll("order_intent")[0]
        
        # Serialize and deserialize
        json_str = json.dumps(polled.payload, sort_keys=True)
        deserialized = json.loads(json_str)
        
        assert deserialized == payload
        # Verify determinism: same payload should produce same JSON
        json_str2 = json.dumps(polled.payload, sort_keys=True)
        assert json_str == json_str2

    def test_trace_id_preservation(self):
        """trace_id should be preserved through roundtrip."""
        bus = InMemoryBus()
        
        bus.publish(
            topic="risk_decision",
            event_type="RiskDecisionV1",
            trace_id="TRACE-ABC-123",
            payload={"allowed": True},
        )
        
        polled = bus.poll("risk_decision")[0]
        
        assert polled.trace_id == "TRACE-ABC-123"


class TestInMemoryBusSequencing:
    """Tests for seq monotonicity and ordering."""

    def test_seq_monotonic_single_topic(self):
        """seq should be monotonically increasing within topic."""
        bus = InMemoryBus()
        
        env1 = bus.publish("order_intent", "E1", "T-1", {"n": 1})
        env2 = bus.publish("order_intent", "E2", "T-2", {"n": 2})
        
        assert env2.seq > env1.seq
        assert env1.seq == 1
        assert env2.seq == 2

    def test_seq_global_across_topics(self):
        """seq should be global monotonic across all topics."""
        bus = InMemoryBus()
        
        env1 = bus.publish("order_intent", "E1", "T-1", {})
        env2 = bus.publish("risk_decision", "E2", "T-2", {})
        env3 = bus.publish("execution_report", "E3", "T-3", {})
        
        assert env1.seq == 1
        assert env2.seq == 2
        assert env3.seq == 3

    def test_fifo_order(self):
        """poll should return events in FIFO order."""
        bus = InMemoryBus()
        
        bus.publish("order_intent", "E1", "T-1", {"n": 1})
        bus.publish("order_intent", "E2", "T-2", {"n": 2})
        bus.publish("order_intent", "E3", "T-3", {"n": 3})
        
        polled = bus.poll("order_intent", max_items=3)
        
        assert len(polled) == 3
        assert polled[0].payload["n"] == 1
        assert polled[1].payload["n"] == 2
        assert polled[2].payload["n"] == 3


class TestInMemoryBusMultiPoll:
    """Tests for multiple poll operations."""

    def test_poll_removes_from_queue(self):
        """poll should remove events from queue."""
        bus = InMemoryBus()
        
        bus.publish("order_intent", "E1", "T-1", {})
        bus.publish("order_intent", "E2", "T-2", {})
        
        assert bus.size("order_intent") == 2
        
        bus.poll("order_intent", max_items=1)
        
        assert bus.size("order_intent") == 1

    def test_poll_max_items_limit(self):
        """poll should respect max_items limit."""
        bus = InMemoryBus()
        
        for i in range(5):
            bus.publish("order_intent", "E", f"T-{i}", {})
        
        polled = bus.poll("order_intent", max_items=2)
        
        assert len(polled) == 2
        assert bus.size("order_intent") == 3

    def test_poll_less_than_max_items(self):
        """poll should return all if less than max_items available."""
        bus = InMemoryBus()
        
        bus.publish("order_intent", "E1", "T-1", {})
        
        polled = bus.poll("order_intent", max_items=10)
        
        assert len(polled) == 1


class TestInMemoryBusClear:
    """Tests for clear functionality."""

    def test_clear_specific_topic(self):
        """clear(topic) should clear only that topic."""
        bus = InMemoryBus()
        
        bus.publish("order_intent", "E1", "T-1", {})
        bus.publish("risk_decision", "E2", "T-2", {})
        
        bus.clear("order_intent")
        
        assert bus.size("order_intent") == 0
        assert bus.size("risk_decision") == 1

    def test_clear_all(self):
        """clear() should clear all topics and reset seq."""
        bus = InMemoryBus()
        
        bus.publish("order_intent", "E1", "T-1", {})
        bus.publish("risk_decision", "E2", "T-2", {})
        
        bus.clear()
        
        assert bus.size("order_intent") == 0
        assert bus.size("risk_decision") == 0
        
        # seq should reset
        env = bus.publish("order_intent", "E3", "T-3", {})
        assert env.seq == 1
