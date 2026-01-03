"""
tests/test_contracts_3A.py

Tests for contracts/event_messages.py (Phase 3A).
"""
import pytest
import json
from contracts.event_messages import (
    OrderIntent, RiskDecision, ExecutionReport, ExecutionContext
)

def test_order_intent_roundtrip():
    oi = OrderIntent(
        symbol="BTC-USD",
        side="BUY",
        qty=1.5,
        order_type="LIMIT",
        limit_price=50000.0,
        meta={"strategy": "trend_following"}
    )
    
    # To Dict
    d = oi.to_dict()
    assert d["symbol"] == "BTC-USD"
    assert d["schema_id"] == "OrderIntent"
    assert d["qty"] == 1.5
    
    # To JSON
    j = oi.to_json()
    assert '"symbol": "BTC-USD"' in j
    
    # From JSON
    oi2 = OrderIntent.from_json(j)
    assert oi2 == oi
    assert oi2.meta["strategy"] == "trend_following"

def test_order_intent_validation():
    # Missing symbol
    with pytest.raises(ValueError, match="symbol is required"):
        OrderIntent(symbol="", side="BUY", qty=1.0)
        
    # Missing side
    with pytest.raises(ValueError, match="side is required"):
        OrderIntent(symbol="BTC", side="", qty=1.0)
        
    # Missing qty AND notional
    with pytest.raises(ValueError, match="Either qty or notional"):
        OrderIntent(symbol="BTC", side="BUY")

def test_risk_decision_compatibility():
    # Test handling of extra fields (forward compatibility)
    data = {
        "schema_id": "RiskDecision",
        "ref_order_event_id": "ord-123",
        "allowed": True,
        "unexpected_field": "should_be_ignored"
    }
    
    rd = RiskDecision.from_dict(data)
    assert rd.ref_order_event_id == "ord-123"
    assert rd.allowed is True
    # 'unexpected_field' should not be in the object attributes (filtered out)
    assert not hasattr(rd, "unexpected_field")

def test_execution_report_defaults():
    er = ExecutionReport(ref_order_event_id="ord-999")
    assert er.status == "NEW"
    assert er.filled_qty == 0.0
    
    er.status = "FILLED"
    er.filled_qty = 1.0
    
    j = er.to_json()
    er2 = ExecutionReport.from_json(j)
    assert er2.status == "FILLED"
    assert er2.filled_qty == 1.0
    assert er2.ref_order_event_id == "ord-999"

def test_execution_context():
    ec = ExecutionContext(seed=123)
    assert ec.seed == 123
    assert ec.schema_id == "ExecutionContext"
