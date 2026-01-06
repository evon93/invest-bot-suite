"""
tests/test_risk_manager_v0_6_compat_v0_4_parity.py

Parity tests between RiskManager v0.6 and v0.4.
Verifies that v0.6 produces equivalent results to v0.4 for the same inputs.
"""

import pytest
from contracts.events_v1 import OrderIntentV1
from risk_manager_v0_6 import RiskManagerV06, DEFAULT_NAV, DEFAULT_WEIGHT
from risk_manager_v_0_4 import RiskManager as RiskManagerV04


@pytest.fixture
def rules():
    """Common rules for both managers."""
    return {
        "position_limits": {
            "max_single_asset_pct": 0.10,
            "max_crypto_pct": 0.30,
            "max_altcoin_pct": 0.05,
        },
        "kelly": {
            "cap_factor": 0.5,
        },
        "major_cryptos": ["BTC", "ETH"],
    }


@pytest.fixture
def v04(rules):
    """RiskManager v0.4 instance."""
    return RiskManagerV04(rules)


@pytest.fixture
def v06(rules):
    """RiskManager v0.6 instance."""
    return RiskManagerV06(rules)


class TestParityAllowed:
    """Parity tests for 'allowed' result."""

    def test_simple_buy_allowed(self, v04, v06):
        """Simple BUY should produce same allowed result."""
        # Setup v0.4 input
        signal_v04 = {
            "assets": ["BTC/USDT"],
            "deltas": {"BTC/USDT": DEFAULT_WEIGHT},
        }
        current_weights = {}
        
        # v0.4 result
        allowed_v04, _ = v04.filter_signal(signal_v04, current_weights, nav_eur=DEFAULT_NAV)
        
        # v0.6 result (equivalent intent)
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = v06.assess(intent, nav=DEFAULT_NAV, default_weight=DEFAULT_WEIGHT)
        
        assert decision.allowed == allowed_v04

    def test_simple_sell_allowed(self, v04, v06):
        """Simple SELL should produce same allowed result."""
        # v0.4
        signal_v04 = {
            "assets": ["ETH/USDT"],
            "deltas": {"ETH/USDT": -DEFAULT_WEIGHT},
        }
        allowed_v04, _ = v04.filter_signal(signal_v04, {}, nav_eur=DEFAULT_NAV)
        
        # v0.6
        intent = OrderIntentV1(symbol="ETH/USDT", side="SELL", qty=1.0)
        decision = v06.assess(intent, nav=DEFAULT_NAV, default_weight=DEFAULT_WEIGHT)
        
        assert decision.allowed == allowed_v04

    def test_with_existing_weights(self, v04, v06):
        """With existing portfolio weights, results should match."""
        current_weights = {"BTC/USDT": 0.05}
        
        # v0.4
        signal_v04 = {
            "assets": ["BTC/USDT"],
            "deltas": {"BTC/USDT": 0.08},
        }
        allowed_v04, _ = v04.filter_signal(signal_v04, current_weights, nav_eur=DEFAULT_NAV)
        
        # v0.6
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = v06.assess(
            intent, 
            nav=DEFAULT_NAV, 
            default_weight=0.08,
            current_weights=current_weights,
        )
        
        assert decision.allowed == allowed_v04

    def test_limit_order_same_as_market(self, v04, v06):
        """LIMIT order should have same risk result as MARKET (only qty matters)."""
        # v0.4 doesn't distinguish order type in filter_signal
        signal_v04 = {
            "assets": ["BTC/USDT"],
            "deltas": {"BTC/USDT": DEFAULT_WEIGHT},
        }
        allowed_v04, _ = v04.filter_signal(signal_v04, {}, nav_eur=DEFAULT_NAV)
        
        # v0.6 with LIMIT
        intent = OrderIntentV1(
            symbol="BTC/USDT", 
            side="BUY", 
            qty=1.0,
            order_type="LIMIT",
            limit_price=50000.0,
        )
        decision = v06.assess(intent, nav=DEFAULT_NAV, default_weight=DEFAULT_WEIGHT)
        
        assert decision.allowed == allowed_v04

    def test_notional_based_weight(self, v04, v06):
        """Notional-based weight calculation should match v0.4."""
        nav = 100000.0
        notional = 5000.0
        expected_weight = notional / nav  # 0.05
        
        # v0.4 with that weight
        signal_v04 = {
            "assets": ["BTC/USDT"],
            "deltas": {"BTC/USDT": expected_weight},
        }
        allowed_v04, _ = v04.filter_signal(signal_v04, {}, nav_eur=nav)
        
        # v0.6 with notional
        intent = OrderIntentV1(
            symbol="BTC/USDT", 
            side="BUY", 
            qty=None,
            notional=notional,
        )
        decision = v06.assess(intent, nav=nav)
        
        assert decision.allowed == allowed_v04


class TestParityReasons:
    """Parity tests for rejection reasons."""

    def test_reasons_type_consistency(self, v06):
        """Reasons should always be list[str] even if v0.4 returns other types."""
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = v06.assess(intent)
        
        assert isinstance(decision.rejection_reasons, list)
        for r in decision.rejection_reasons:
            assert isinstance(r, str)

    def test_v04_reasons_preserved(self, v04, v06):
        """Reasons from v0.4 should be preserved in v0.6 output."""
        # This test verifies that if v0.4 returns reasons, v0.6 includes them
        # Since v0.4 returns reasons list directly, they should match
        
        signal_v04 = {
            "assets": ["BTC/USDT"],
            "deltas": {"BTC/USDT": DEFAULT_WEIGHT},
        }
        _, annotated = v04.filter_signal(signal_v04, {}, nav_eur=DEFAULT_NAV)
        v04_reasons = annotated.get("risk_reasons", [])
        
        intent = OrderIntentV1(symbol="BTC/USDT", side="BUY", qty=1.0)
        decision = v06.assess(intent, nav=DEFAULT_NAV, default_weight=DEFAULT_WEIGHT)
        
        # v0.6 reasons should at least contain v0.4 base reasons
        for reason in v04_reasons:
            assert reason in decision.rejection_reasons or len(v04_reasons) == 0
