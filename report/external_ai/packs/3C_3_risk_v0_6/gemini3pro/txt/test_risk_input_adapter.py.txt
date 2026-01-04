"""
tests/test_risk_input_adapter.py

Tests para adapters/risk_input_adapter.py
"""

import pytest
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1
from adapters.risk_input_adapter import (
    adapt_order_intent_to_risk_input,
    adapt_risk_output_to_decision,
    AdapterError,
    DEFAULT_TARGET_WEIGHT,
)


class TestAdaptOrderIntentToRiskInput:
    """Tests para adapt_order_intent_to_risk_input()."""

    def test_buy_with_qty(self):
        """Test conversión BUY con qty."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        result = adapt_order_intent_to_risk_input(intent)

        assert result["assets"] == ["BTC/USDT"]
        assert "BTC/USDT" in result["deltas"]
        assert result["deltas"]["BTC/USDT"] == DEFAULT_TARGET_WEIGHT
        assert result["_adapter_meta"]["source_event_id"] == intent.event_id

    def test_sell_with_qty(self):
        """Test conversión SELL con qty (weight negativo)."""
        intent = OrderIntentV1(symbol="ETH/USDT", side="SELL", qty=0.5)
        result = adapt_order_intent_to_risk_input(intent)

        assert result["assets"] == ["ETH/USDT"]
        assert result["deltas"]["ETH/USDT"] == -DEFAULT_TARGET_WEIGHT

    def test_limit_order_with_price(self):
        """Test orden LIMIT con limit_price."""
        intent = OrderIntentV1(
            symbol="BTC/USDT",
            side="BUY",
            qty=1.0,
            order_type="LIMIT",
            limit_price=50000.0,
        )
        result = adapt_order_intent_to_risk_input(intent)

        assert result["_adapter_meta"]["order_type"] == "LIMIT"
        assert result["_adapter_meta"]["limit_price"] == 50000.0

    def test_notional_with_nav(self):
        """Test conversión de notional a weight usando NAV."""
        intent = OrderIntentV1(
            symbol="BTC/USDT",
            side="BUY",
            qty=None,
            notional=1000.0,
        )
        result = adapt_order_intent_to_risk_input(intent, nav=10000.0)

        # weight = notional / nav = 1000 / 10000 = 0.1
        assert result["deltas"]["BTC/USDT"] == pytest.approx(0.1)

    def test_notional_without_nav_uses_default(self):
        """Test notional sin NAV usa default weight."""
        intent = OrderIntentV1(
            symbol="BTC/USDT",
            side="BUY",
            qty=None,
            notional=1000.0,
        )
        result = adapt_order_intent_to_risk_input(intent)  # sin nav

        assert result["deltas"]["BTC/USDT"] == DEFAULT_TARGET_WEIGHT

    def test_error_missing_symbol(self):
        """Test error cuando symbol está vacío."""
        intent = OrderIntentV1(symbol="", side="BUY", qty=1.0)
        with pytest.raises(AdapterError) as exc:
            adapt_order_intent_to_risk_input(intent)
        assert "symbol is required" in str(exc.value)

    def test_error_invalid_side(self):
        """Test error cuando side es inválido."""
        # Creamos manualmente un intent con side no normalizado
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        intent.side = "HOLD"  # Force invalid
        with pytest.raises(AdapterError) as exc:
            adapt_order_intent_to_risk_input(intent)
        assert "side must be BUY or SELL" in str(exc.value)

    def test_error_qty_zero(self):
        """Test error cuando qty <= 0 y no hay notional."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=0, notional=None)
        with pytest.raises(AdapterError) as exc:
            adapt_order_intent_to_risk_input(intent)
        assert "qty or notional must be > 0" in str(exc.value)

    def test_error_qty_negative(self):
        """Test error cuando qty < 0."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="SELL", qty=-1.0, notional=None)
        with pytest.raises(AdapterError) as exc:
            adapt_order_intent_to_risk_input(intent)
        assert "qty or notional must be > 0" in str(exc.value)

    def test_custom_default_weight(self):
        """Test uso de default_weight personalizado."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        result = adapt_order_intent_to_risk_input(intent, default_weight=0.05)

        assert result["deltas"]["BTC/USDT"] == 0.05


class TestAdaptRiskOutputToDecision:
    """Tests para adapt_risk_output_to_decision()."""

    def test_allowed_decision(self):
        """Test creación de RiskDecision cuando allowed=True."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        annotated = {"risk_reasons": [], "risk_allow": True}

        decision = adapt_risk_output_to_decision(intent, True, annotated)

        assert isinstance(decision, RiskDecisionV1)
        assert decision.allowed is True
        assert decision.rejection_reasons == []
        assert decision.ref_order_event_id == intent.event_id

    def test_rejected_decision(self):
        """Test creación de RiskDecision cuando allowed=False."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        annotated = {
            "risk_reasons": ["position_limits", "kelly_cap:BTC/USDT"],
            "risk_allow": False,
        }

        decision = adapt_risk_output_to_decision(intent, False, annotated)

        assert decision.allowed is False
        assert decision.rejection_reasons == ["position_limits", "kelly_cap:BTC/USDT"]

    def test_trace_id_propagation(self):
        """Test que trace_id se propaga del intent al decision."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        annotated = {"risk_reasons": []}

        decision = adapt_risk_output_to_decision(intent, True, annotated)

        assert decision.trace_id == intent.trace_id

    def test_extra_metadata(self):
        """Test que extra contiene metadata del adapter."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        annotated = {"risk_reasons": []}

        decision = adapt_risk_output_to_decision(intent, True, annotated)

        assert decision.extra.get("adapter_processed") is True
