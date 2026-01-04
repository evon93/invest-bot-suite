"""
tests/test_risk_manager_v0_6_contract.py

Contract tests for RiskManager v0.6.
Verifies that assess() returns valid RiskDecisionV1 with proper types.
"""

import pytest
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1
from risk_manager_v0_6 import RiskManagerV06


@pytest.fixture
def risk_manager():
    """Create a RiskManagerV06 with default rules."""
    return RiskManagerV06({})


class TestAssessContract:
    """Contract tests for assess() method."""

    def test_returns_risk_decision_v1(self, risk_manager):
        """assess() must return a RiskDecisionV1 instance."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert isinstance(decision, RiskDecisionV1)

    def test_rejection_reasons_is_list_str(self, risk_manager):
        """rejection_reasons must always be list[str]."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert isinstance(decision.rejection_reasons, list)
        for reason in decision.rejection_reasons:
            assert isinstance(reason, str)

    def test_ref_order_event_id_matches(self, risk_manager):
        """ref_order_event_id must match the intent's event_id."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert decision.ref_order_event_id == intent.event_id

    def test_trace_id_propagated(self, risk_manager):
        """trace_id must be propagated from intent."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert decision.trace_id == intent.trace_id

    def test_allowed_is_bool(self, risk_manager):
        """allowed must be a boolean."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert isinstance(decision.allowed, bool)

    def test_extra_contains_metadata(self, risk_manager):
        """extra should contain v0.6 processing metadata."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert decision.extra.get("v06_processed") is True
        assert decision.extra.get("delegated_to_v04") is True

    def test_invalid_intent_returns_rejected(self, risk_manager):
        """Invalid intents should return rejected decision."""
        # Create intent with invalid data (empty symbol)
        intent = OrderIntentV1(symbol="", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        assert decision.allowed is False
        assert "INVALID_ORDER_INTENT" in decision.rejection_reasons

    def test_nav_parameter_used(self, risk_manager):
        """NAV parameter should be recorded in extra."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent, nav=50000.0)
        
        assert decision.extra.get("nav_used") == 50000.0

    def test_default_weight_parameter_used(self, risk_manager):
        """default_weight parameter should be recorded in extra."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent, default_weight=0.05)
        
        assert decision.extra.get("default_weight") == 0.05


class TestDecisionSerialization:
    """Tests for decision serialization."""

    def test_to_dict_works(self, risk_manager):
        """RiskDecisionV1 from assess() can be serialized."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = risk_manager.assess(intent)
        
        d = decision.to_dict()
        assert isinstance(d, dict)
        assert d["schema_id"] == "RiskDecisionV1"
        assert "rejection_reasons" in d
        assert isinstance(d["rejection_reasons"], list)

    def test_roundtrip(self, risk_manager):
        """Decision can roundtrip through dict."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        original = risk_manager.assess(intent)
        
        d = original.to_dict()
        restored = RiskDecisionV1.from_dict(d)
        
        assert restored.allowed == original.allowed
        assert restored.ref_order_event_id == original.ref_order_event_id
        assert restored.rejection_reasons == original.rejection_reasons
