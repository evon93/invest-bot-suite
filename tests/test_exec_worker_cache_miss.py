"""
tests/test_exec_worker_cache_miss.py

Tests for ExecWorker cache-miss fail-fast behavior.

Validates that ExecWorker raises ValueError when:
- ref_order_event_id not in intent_cache
- Required fields missing or invalid

Part of ticket AG-3D-4-1.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from bus import InMemoryBus, BusEnvelope
from engine.bus_workers import (
    ExecWorker, RiskWorker,
    TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
)
from contracts.events_v1 import RiskDecisionV1


class TestExecWorkerCacheMiss:
    """Tests for cache-miss fail-fast behavior."""

    def test_cache_miss_raises_valueerror(self):
        """ExecWorker should raise ValueError when intent not in cache."""
        bus = InMemoryBus()
        intent_cache = {}  # Empty cache
        
        exec_worker = ExecWorker(
            {"slippage_bps": 5.0},
            gen_event_id=lambda: "exec-id",
            intent_cache=intent_cache,
        )
        
        # Publish a RiskDecisionV1 with ref_order_event_id that's not in cache
        decision = RiskDecisionV1(
            ref_order_event_id="nonexistent-intent-id",
            allowed=True,
            rejection_reasons=[],
            trace_id="trace-123",
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-123",
            payload=decision.to_dict(),
        )
        
        # ExecWorker should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            exec_worker.step(bus, max_items=1)
        
        error_msg = str(exc_info.value)
        assert "cache miss" in error_msg.lower()
        assert "nonexistent-intent-id" in error_msg
        assert "trace-123" in error_msg

    def test_cache_miss_no_execution_report_published(self):
        """On cache miss, no ExecutionReportV1 should be published."""
        bus = InMemoryBus()
        intent_cache = {}
        
        exec_worker = ExecWorker(
            {"slippage_bps": 5.0},
            gen_event_id=lambda: "exec-id",
            intent_cache=intent_cache,
        )
        
        decision = RiskDecisionV1(
            ref_order_event_id="missing-id",
            allowed=True,
            rejection_reasons=[],
            trace_id="trace-456",
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-456",
            payload=decision.to_dict(),
        )
        
        # Before processing
        assert bus.size(TOPIC_EXECUTION_REPORT) == 0
        
        # Process (should fail)
        try:
            exec_worker.step(bus, max_items=1)
        except ValueError:
            pass  # Expected
        
        # After processing - no execution report should be published
        assert bus.size(TOPIC_EXECUTION_REPORT) == 0

    def test_valid_cache_entry_succeeds(self):
        """ExecWorker should succeed with valid cache entry."""
        bus = InMemoryBus()
        
        # Valid cache entry
        intent_cache = {
            "valid-intent-id": {
                "event_id": "valid-intent-id",
                "symbol": "BTC-USD",
                "side": "BUY",
                "qty": 1.5,
                "limit_price": 50000.0,
                "meta": {"current_price": 50000.0},
            }
        }
        
        exec_worker = ExecWorker(
            {"slippage_bps": 5.0},
            gen_event_id=lambda: "exec-id",
            intent_cache=intent_cache,
        )
        
        decision = RiskDecisionV1(
            ref_order_event_id="valid-intent-id",
            allowed=True,
            rejection_reasons=[],
            trace_id="trace-789",
            event_id="decision-id",
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-789",
            payload=decision.to_dict(),
        )
        
        # Should succeed without raising
        exec_worker.step(bus, max_items=1)
        
        # ExecutionReport should be published
        assert bus.size(TOPIC_EXECUTION_REPORT) == 1

    def test_invalid_side_raises_valueerror(self):
        """ExecWorker should raise ValueError for invalid side."""
        bus = InMemoryBus()
        
        intent_cache = {
            "test-id": {
                "event_id": "test-id",
                "symbol": "BTC",
                "side": "INVALID",  # Invalid side
                "qty": 1.0,
                "limit_price": 100.0,
            }
        }
        
        exec_worker = ExecWorker(
            {"slippage_bps": 5.0},
            gen_event_id=lambda: "exec-id",
            intent_cache=intent_cache,
        )
        
        decision = RiskDecisionV1(
            ref_order_event_id="test-id",
            allowed=True,
            rejection_reasons=[],
            trace_id="trace-000",
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-000",
            payload=decision.to_dict(),
        )
        
        with pytest.raises(ValueError) as exc_info:
            exec_worker.step(bus, max_items=1)
        
        assert "invalid side" in str(exc_info.value).lower()

    def test_missing_symbol_raises_valueerror(self):
        """ExecWorker should raise ValueError for missing symbol."""
        bus = InMemoryBus()
        
        intent_cache = {
            "test-id": {
                "event_id": "test-id",
                "side": "BUY",
                "qty": 1.0,
                "limit_price": 100.0,
                # Missing symbol
            }
        }
        
        exec_worker = ExecWorker(
            {"slippage_bps": 5.0},
            gen_event_id=lambda: "exec-id",
            intent_cache=intent_cache,
        )
        
        decision = RiskDecisionV1(
            ref_order_event_id="test-id",
            allowed=True,
            rejection_reasons=[],
            trace_id="trace-111",
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-111",
            payload=decision.to_dict(),
        )
        
        with pytest.raises(ValueError) as exc_info:
            exec_worker.step(bus, max_items=1)
        
        assert "missing symbol" in str(exc_info.value).lower()
