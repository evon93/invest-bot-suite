"""
tests/test_contracts_events_v1_roundtrip.py

Roundtrip and validation tests for contracts/events_v1.py.
"""

import pytest
from contracts.events_v1 import (
    OrderIntentV1,
    RiskDecisionV1,
    ExecutionReportV1,
    ValidationError,
)


class TestOrderIntentV1:
    """Tests for OrderIntentV1."""

    def test_roundtrip_basic(self):
        """Test obj -> dict -> obj roundtrip preserves data."""
        original = OrderIntentV1(
            symbol="BTC/USDT",
            side="buy",
            qty=1.5,
            order_type="MARKET",
        )
        d = original.to_dict()
        restored = OrderIntentV1.from_dict(d)

        assert restored.symbol == original.symbol
        assert restored.side == "BUY"  # normalized
        assert restored.qty == original.qty
        assert restored.order_type == original.order_type
        assert restored.event_id == original.event_id

    def test_from_dict_with_aliases(self):
        """Test from_dict accepts legacy aliases."""
        data = {
            "ticker": "ETH/USDT",
            "action": "sell",
            "quantity": 2.0,
            "type": "LIMIT",
            "limit_price": 2000.0,
        }
        obj = OrderIntentV1.from_dict(data)

        assert obj.symbol == "ETH/USDT"
        assert obj.side == "SELL"
        assert obj.qty == 2.0
        assert obj.order_type == "LIMIT"
        assert obj.limit_price == 2000.0

    def test_validate_pass(self):
        """Test validate() passes on valid instance."""
        obj = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        assert obj.validate() is True

    def test_validate_fail_empty_symbol(self):
        """Test validate() fails on empty symbol."""
        obj = OrderIntentV1(symbol="", side="BUY", qty=1.0)
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "symbol is required" in str(exc.value)

    def test_validate_fail_invalid_side(self):
        """Test validate() fails on invalid side."""
        obj = OrderIntentV1(symbol="BTC/USDT", side="HOLD", qty=1.0)
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "side must be BUY or SELL" in str(exc.value)

    def test_validate_fail_qty_zero(self):
        """Test validate() fails when qty <= 0."""
        obj = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=0)
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "qty or notional must be > 0" in str(exc.value)

    def test_validate_fail_qty_negative(self):
        """Test validate() fails when qty < 0."""
        obj = OrderIntentV1(symbol="BTC/USDT", side="SELL", qty=-1.0)
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "qty or notional must be > 0" in str(exc.value)

    def test_validate_pass_with_notional(self):
        """Test validate() passes with notional instead of qty."""
        obj = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=None, notional=1000.0)
        assert obj.validate() is True

    def test_validate_fail_limit_no_price(self):
        """Test validate() fails on LIMIT order without limit_price."""
        obj = OrderIntentV1(
            symbol="BTC/USDT", side="BUY", qty=1.0, order_type="LIMIT"
        )
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "limit_price required for LIMIT orders" in str(exc.value)


class TestRiskDecisionV1:
    """Tests for RiskDecisionV1."""

    def test_roundtrip_basic(self):
        """Test obj -> dict -> obj roundtrip preserves data."""
        original = RiskDecisionV1(
            ref_order_event_id="order-123",
            allowed=True,
            adjusted_qty=0.5,
            rejection_reasons=[],
        )
        d = original.to_dict()
        restored = RiskDecisionV1.from_dict(d)

        assert restored.ref_order_event_id == original.ref_order_event_id
        assert restored.allowed == original.allowed
        assert restored.adjusted_qty == original.adjusted_qty
        assert restored.event_id == original.event_id

    def test_from_dict_with_aliases(self):
        """Test from_dict accepts legacy aliases."""
        data = {
            "order_id": "order-456",
            "allowed": False,
            "reasons": "MAX_POSITION_EXCEEDED",
        }
        obj = RiskDecisionV1.from_dict(data)

        assert obj.ref_order_event_id == "order-456"
        assert obj.allowed is False
        assert obj.rejection_reasons == ["MAX_POSITION_EXCEEDED"]

    def test_reasons_normalized_from_string(self):
        """Test rejection_reasons normalized from single string."""
        obj = RiskDecisionV1(
            ref_order_event_id="order-789",
            rejection_reasons="SINGLE_REASON",  # type: ignore
        )
        assert obj.rejection_reasons == ["SINGLE_REASON"]

    def test_reasons_normalized_from_none(self):
        """Test rejection_reasons normalized from None."""
        data = {"ref_order_event_id": "order-abc", "rejection_reasons": None}
        obj = RiskDecisionV1.from_dict(data)
        assert obj.rejection_reasons == []

    def test_validate_pass(self):
        """Test validate() passes on valid instance."""
        obj = RiskDecisionV1(ref_order_event_id="order-123", allowed=True)
        assert obj.validate() is True

    def test_validate_fail_empty_ref(self):
        """Test validate() fails on empty ref_order_event_id."""
        obj = RiskDecisionV1(ref_order_event_id="", allowed=False)
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "ref_order_event_id is required" in str(exc.value)


class TestExecutionReportV1:
    """Tests for ExecutionReportV1."""

    def test_roundtrip_basic(self):
        """Test obj -> dict -> obj roundtrip preserves data."""
        original = ExecutionReportV1(
            ref_order_event_id="order-123",
            status="FILLED",
            filled_qty=1.0,
            avg_price=50000.0,
            fee=0.001,
        )
        d = original.to_dict()
        restored = ExecutionReportV1.from_dict(d)

        assert restored.ref_order_event_id == original.ref_order_event_id
        assert restored.status == original.status
        assert restored.filled_qty == original.filled_qty
        assert restored.avg_price == original.avg_price
        assert restored.event_id == original.event_id

    def test_from_dict_with_aliases(self):
        """Test from_dict accepts legacy aliases."""
        data = {
            "order_id": "order-456",
            "status": "FILLED",
            "qty": 2.0,
            "price": 48000.0,
        }
        obj = ExecutionReportV1.from_dict(data)

        assert obj.ref_order_event_id == "order-456"
        assert obj.filled_qty == 2.0
        assert obj.avg_price == 48000.0

    def test_validate_pass(self):
        """Test validate() passes on valid instance."""
        obj = ExecutionReportV1(
            ref_order_event_id="order-123",
            status="FILLED",
            filled_qty=1.0,
            avg_price=50000.0,
        )
        assert obj.validate() is True

    def test_validate_fail_empty_ref(self):
        """Test validate() fails on empty ref_order_event_id."""
        obj = ExecutionReportV1(ref_order_event_id="", status="NEW")
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "ref_order_event_id is required" in str(exc.value)

    def test_validate_fail_invalid_status(self):
        """Test validate() fails on invalid status."""
        obj = ExecutionReportV1(
            ref_order_event_id="order-123",
            status="UNKNOWN",
        )
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "status must be one of" in str(exc.value)

    def test_validate_fail_negative_qty(self):
        """Test validate() fails on negative filled_qty."""
        obj = ExecutionReportV1(
            ref_order_event_id="order-123",
            status="FILLED",
            filled_qty=-1.0,
        )
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "filled_qty must be >= 0" in str(exc.value)

    def test_validate_fail_negative_price(self):
        """Test validate() fails on negative avg_price."""
        obj = ExecutionReportV1(
            ref_order_event_id="order-123",
            status="FILLED",
            avg_price=-100.0,
        )
        with pytest.raises(ValidationError) as exc:
            obj.validate()
        assert "avg_price must be >= 0" in str(exc.value)
