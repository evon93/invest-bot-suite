"""
tests/test_retry_idempotency_integration_3F2.py

Integration tests for retry + idempotency in ExecWorker.
Uses flaky adapter to test retry behavior and duplicate prevention.
"""

import pytest
import sys
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bus import InMemoryBus
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from engine.bus_workers import ExecWorker, TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
from engine.retry_policy import RetryPolicy
from engine.idempotency import InMemoryIdempotencyStore
from engine.exchange_adapter import ExecutionContext


class FlakyAdapter:
    """
    Adapter that fails a configurable number of times before succeeding.
    Used to test retry behavior.
    """
    
    def __init__(self, fail_count: int = 2, fail_with: type = ConnectionError):
        self.fail_count = fail_count
        self.fail_with = fail_with
        self.call_count = 0
        self.submitted_reports = []
    
    def submit(
        self,
        intent: OrderIntentV1,
        decision: RiskDecisionV1,
        context: ExecutionContext,
        report_event_id: str,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> ExecutionReportV1:
        self.call_count += 1
        
        if self.call_count <= self.fail_count:
            raise self.fail_with(f"Simulated failure #{self.call_count}")
        
        # Success
        report = ExecutionReportV1(
            ref_order_event_id=intent.event_id,
            status="FILLED",
            filled_qty=intent.qty or 1.0,
            avg_price=100.0,
            fee=0.1,
            slippage=0.05,
            latency_ms=10.0,
            ref_risk_event_id=decision.event_id,
            trace_id=intent.trace_id,
            event_id=report_event_id,
            ts=intent.ts,
            extra={"adapter": "FlakyAdapter", "attempts": self.call_count}
        )
        self.submitted_reports.append(report)
        return report


def make_test_intent(event_id: str = "intent-001") -> Dict[str, Any]:
    """Create a test intent payload."""
    return {
        "symbol": "BTC-USD",
        "side": "BUY",
        "qty": 1.0,
        "notional": 100.0,
        "order_type": "MARKET",
        "limit_price": None,
        "event_id": event_id,
        "trace_id": f"trace-{event_id}",
        "ts": "2024-01-01T00:00:00Z",
        "meta": {"bar_close": 100.0},
    }


def make_test_decision(ref_order_event_id: str, event_id: str = "decision-001") -> Dict[str, Any]:
    """Create a test decision payload."""
    return {
        "ref_order_event_id": ref_order_event_id,
        "allowed": True,
        "rejection_reasons": [],
        "trace_id": f"trace-{ref_order_event_id}",
        "event_id": event_id,
        "ts": "2024-01-01T00:00:01Z",
        "extra": {},
    }


class TestFlakyAdapterRetry:
    """Tests for retry behavior with flaky adapter."""
    
    def test_flaky_adapter_retries_succeed(self):
        """Adapter fails 2x then succeeds - should produce 1 fill after 3 attempts."""
        bus = InMemoryBus()
        flaky = FlakyAdapter(fail_count=2)
        
        intent_cache = {}
        intent_payload = make_test_intent("order-001")
        intent_cache["order-001"] = intent_payload
        
        sleep_calls = []
        def mock_sleep(ms):
            sleep_calls.append(ms)
        
        worker = ExecWorker(
            exchange_adapter=flaky,
            gen_event_id=lambda: "exec-001",
            intent_cache=intent_cache,
            retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=10),
            sleep_fn=mock_sleep,
        )
        
        # Publish decision to bus
        decision_payload = make_test_decision("order-001", "decision-001")
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-order-001",
            payload=decision_payload,
        )
        
        # Process
        processed = worker.step(bus, max_items=10)
        
        # Verify
        assert processed == 1
        assert flaky.call_count == 3  # Failed 2x, succeeded 1x
        assert len(flaky.submitted_reports) == 1
        assert len(sleep_calls) == 2  # Slept before retries 2 and 3
        
        # Verify report published to bus
        reports = bus.poll(TOPIC_EXECUTION_REPORT, max_items=10)
        assert len(reports) == 1
        assert reports[0].payload["status"] == "FILLED"
    
    def test_retry_exhausted_no_report(self):
        """All retries fail - no report should be published."""
        bus = InMemoryBus()
        flaky = FlakyAdapter(fail_count=100)  # Always fails
        
        intent_cache = {}
        intent_payload = make_test_intent("order-002")
        intent_cache["order-002"] = intent_payload
        
        worker = ExecWorker(
            exchange_adapter=flaky,
            gen_event_id=lambda: "exec-002",
            intent_cache=intent_cache,
            retry_policy=RetryPolicy(max_attempts=3, base_delay_ms=1),
        )
        
        decision_payload = make_test_decision("order-002", "decision-002")
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-order-002",
            payload=decision_payload,
        )
        
        # Process - should not raise (handled internally)
        processed = worker.step(bus, max_items=10)
        
        assert processed == 1  # Decision was processed
        assert flaky.call_count == 3  # All 3 attempts made
        
        # No report published
        reports = bus.poll(TOPIC_EXECUTION_REPORT, max_items=10)
        assert len(reports) == 0


class TestIdempotencyPrevention:
    """Tests for idempotency preventing duplicate fills."""
    
    def test_duplicate_decision_produces_single_fill(self):
        """Same decision submitted twice - only one fill."""
        bus = InMemoryBus()
        flaky = FlakyAdapter(fail_count=0)  # Always succeeds
        
        intent_cache = {}
        intent_payload = make_test_intent("order-003")
        intent_cache["order-003"] = intent_payload
        
        idem_store = InMemoryIdempotencyStore()
        
        event_id_counter = [0]
        def gen_event_id():
            event_id_counter[0] += 1
            return f"exec-{event_id_counter[0]:03d}"
        
        worker = ExecWorker(
            exchange_adapter=flaky,
            gen_event_id=gen_event_id,
            intent_cache=intent_cache,
            idempotency_store=idem_store,
        )
        
        # Publish same decision twice
        decision_payload = make_test_decision("order-003", "decision-003")
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-order-003",
            payload=decision_payload,
        )
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-order-003",
            payload=decision_payload,
        )
        
        # Process both
        processed = worker.step(bus, max_items=10)
        
        # Verify only one fill
        assert processed == 2  # Both decisions processed from queue
        assert flaky.call_count == 1  # Only one actual submission
        assert len(flaky.submitted_reports) == 1
        
        # Only one report published
        reports = bus.poll(TOPIC_EXECUTION_REPORT, max_items=10)
        assert len(reports) == 1
    
    def test_different_orders_not_affected(self):
        """Different orders are processed independently."""
        bus = InMemoryBus()
        flaky = FlakyAdapter(fail_count=0)
        
        intent_cache = {}
        intent_cache["order-a"] = make_test_intent("order-a")
        intent_cache["order-b"] = make_test_intent("order-b")
        
        idem_store = InMemoryIdempotencyStore()
        
        event_id_counter = [0]
        def gen_event_id():
            event_id_counter[0] += 1
            return f"exec-{event_id_counter[0]:03d}"
        
        worker = ExecWorker(
            exchange_adapter=flaky,
            gen_event_id=gen_event_id,
            intent_cache=intent_cache,
            idempotency_store=idem_store,
        )
        
        # Publish two different decisions
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-a",
            payload=make_test_decision("order-a", "decision-a"),
        )
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-b",
            payload=make_test_decision("order-b", "decision-b"),
        )
        
        processed = worker.step(bus, max_items=10)
        
        assert processed == 2
        assert flaky.call_count == 2  # Both submitted
        assert len(flaky.submitted_reports) == 2


class TestNoRealSleep:
    """Tests verifying no real sleeps in test mode."""
    
    def test_default_sleep_is_noop(self):
        """Default ExecWorker sleep_fn is no-op."""
        import time
        
        bus = InMemoryBus()
        flaky = FlakyAdapter(fail_count=2)
        
        intent_cache = {}
        intent_cache["order-x"] = make_test_intent("order-x")
        
        # No sleep_fn provided - uses default no-op
        worker = ExecWorker(
            exchange_adapter=flaky,
            gen_event_id=lambda: "exec-x",
            intent_cache=intent_cache,
            retry_policy=RetryPolicy(max_attempts=5, base_delay_ms=100000),  # 100s would be obvious if blocking
        )
        
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-x",
            payload=make_test_decision("order-x", "decision-x"),
        )
        
        start = time.time()
        worker.step(bus, max_items=10)
        elapsed = time.time() - start
        
        # Should complete nearly instantly
        assert elapsed < 1.0, f"Expected no blocking sleep, got {elapsed}s"
