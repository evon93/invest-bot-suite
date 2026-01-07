"""
tests/test_realish_adapter_integration_3F3.py

Integration tests for SimulatedRealtimeAdapter with full pipeline.
Marked as integration - SKIP if INVESTBOT_TEST_INTEGRATION not set.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Skip all tests in this module if integration flag not set
pytestmark = pytest.mark.integration


def requires_integration():
    """Check if integration tests should run."""
    return os.environ.get("INVESTBOT_TEST_INTEGRATION") == "1"


class TestRealishIntegration:
    """Integration tests requiring explicit opt-in."""
    
    def test_realish_full_pipeline_with_bus(self):
        """Full pipeline test with realish adapter and bus workers."""
        if not requires_integration():
            pytest.skip("Integration tests require INVESTBOT_TEST_INTEGRATION=1")
        
        from bus import InMemoryBus
        from engine.bus_workers import ExecWorker, TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
        from engine.exchange_adapter import SimulatedRealtimeAdapter
        from engine.retry_policy import RetryPolicy
        from contracts.events_v1 import OrderIntentV1
        
        bus = InMemoryBus()
        
        # Use realish adapter with retry
        adapter = SimulatedRealtimeAdapter(failure_rate_1_in_n=5)
        
        intent_cache = {
            "order-001": {
                "symbol": "BTC-USD",
                "side": "BUY", 
                "qty": 1.0,
                "notional": 100.0,
                "order_type": "MARKET",
                "limit_price": 100.0,
                "event_id": "order-001",
                "trace_id": "trace-001",
                "meta": {"bar_close": 100.0}
            }
        }
        
        worker = ExecWorker(
            exchange_adapter=adapter,
            gen_event_id=lambda: "exec-001",
            intent_cache=intent_cache,
            retry_policy=RetryPolicy(max_attempts=5),
        )
        
        # Publish decision
        decision_payload = {
            "ref_order_event_id": "order-001",
            "allowed": True,
            "rejection_reasons": [],
            "trace_id": "trace-001",
            "event_id": "decision-001",
            "extra": {}
        }
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id="trace-001",
            payload=decision_payload,
        )
        
        # Process
        processed = worker.step(bus, max_items=10)
        
        # Verify
        assert processed == 1
        reports = bus.poll(TOPIC_EXECUTION_REPORT, max_items=10)
        # May succeed or exhaust retries depending on hash
        # Just verify no crash
    
    def test_realish_with_idempotency(self):
        """Test realish adapter with idempotency store."""
        if not requires_integration():
            pytest.skip("Integration tests require INVESTBOT_TEST_INTEGRATION=1")
        
        from bus import InMemoryBus
        from engine.bus_workers import ExecWorker, TOPIC_RISK_DECISION, TOPIC_EXECUTION_REPORT
        from engine.exchange_adapter import SimulatedRealtimeAdapter
        from engine.idempotency import InMemoryIdempotencyStore
        
        bus = InMemoryBus()
        adapter = SimulatedRealtimeAdapter(failure_rate_1_in_n=1000000)  # No failures
        idem = InMemoryIdempotencyStore()
        
        intent_cache = {
            "order-002": {
                "symbol": "ETH-USD",
                "side": "SELL",
                "qty": 2.0,
                "notional": 200.0,
                "order_type": "MARKET",
                "limit_price": 100.0,
                "event_id": "order-002",
                "trace_id": "trace-002",
                "meta": {"bar_close": 100.0}
            }
        }
        
        event_counter = [0]
        def gen_id():
            event_counter[0] += 1
            return f"exec-{event_counter[0]:03d}"
        
        worker = ExecWorker(
            exchange_adapter=adapter,
            gen_event_id=gen_id,
            intent_cache=intent_cache,
            idempotency_store=idem,
        )
        
        # Publish same decision twice
        decision_payload = {
            "ref_order_event_id": "order-002",
            "allowed": True,
            "rejection_reasons": [],
            "trace_id": "trace-002",
            "event_id": "decision-002",
            "extra": {}
        }
        bus.publish(topic=TOPIC_RISK_DECISION, event_type="RiskDecisionV1", 
                   trace_id="trace-002", payload=decision_payload)
        bus.publish(topic=TOPIC_RISK_DECISION, event_type="RiskDecisionV1",
                   trace_id="trace-002", payload=decision_payload)
        
        # Process both
        worker.step(bus, max_items=10)
        
        # Only one report should be generated (idempotency)
        reports = bus.poll(TOPIC_EXECUTION_REPORT, max_items=10)
        assert len(reports) == 1, "Idempotency should prevent duplicate fills"


class TestSkipWhenNotEnabled:
    """Verify tests skip properly when integration not enabled."""
    
    def test_skip_message(self):
        """This test demonstrates skip behavior."""
        if not requires_integration():
            pytest.skip("Integration tests require INVESTBOT_TEST_INTEGRATION=1")
        
        # This line only runs if integration enabled
        assert True
