"""
tests/test_execworker_cache_miss_failfast.py

Tests ExecWorker fail-fast behavior.
"""

import pytest
from engine.bus_workers import ExecWorker, TOPIC_RISK_DECISION
from bus import InMemoryBus
from contracts.events_v1 import RiskDecisionV1

def test_exec_worker_raises_on_cache_miss():
    """ExecWorker must raise ValueError if original intent is not in cache."""
    
    bus = InMemoryBus()
    worker = ExecWorker(execution_config={})
    
    # Publish a RiskDecision refering to unknown order
    decision = RiskDecisionV1(
        ref_order_event_id="unknown-order-id",
        allowed=True,
        event_id="risk-1",
        trace_id="trace-1"
    )
    
    bus.publish(TOPIC_RISK_DECISION, "RiskDecisionV1", "trace-1", decision.to_dict())
    
    # Step should fail
    with pytest.raises(ValueError, match="cache miss"):
        worker.step(bus)

