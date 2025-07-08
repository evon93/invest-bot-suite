"""
tests/test_risk_suite.py
------------------------
Versión robusta, sólo usa el SHIM universal y mocks locales.
"""

import sys
import pytest
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from risk_manager_v0_4_shim import RiskManager

def test_risk_manager_imported():
    """RiskManager importado correctamente desde el SHIM"""
    assert RiskManager is not None

def test_risk_manager_basic_attrs():
    """RiskManager tiene los métodos esenciales esperados (v0.4)"""
    mock_rules = {
        "position_limits": {"max_single_asset_pct": 0.06, "max_crypto_pct": 1.0},
        "kelly": {
            "base_fraction": 0.5,
            "crypto_overrides": {
                "high_vol": 0.3,
                "med_vol": 0.2,
                "low_vol": 0.1,
                "percentile_thresholds": {"low": 0.5, "high": 0.8}
            },
            "per_asset": {},
            "cap_factor": 1,
            "min_trade_size_eur": 0.0,
            "max_trade_size_eur": 1e6,
        },
        "stop_loss": {},
        "volatility_stop": {},
        "major_cryptos": [],
        "liquidity_filter": {},
        "recalibration": {},
    }
    rm = RiskManager(mock_rules)
    for attr in (
        "within_position_limits",
        "filter_signal",
        "max_position_size",
    ):
        assert hasattr(rm, attr), f"Falta el método {attr}"

def test_risk_manager_methods():
    """Prueba funcionalidad de métodos básicos de RiskManager"""
    mock_rules = {
        "position_limits": {"max_single_asset_pct": 0.1, "max_crypto_pct": 1.0},
        "kelly": {
            "base_fraction": 0.5,
            "crypto_overrides": {
                "high_vol": 0.3,
                "med_vol": 0.2,
                "low_vol": 0.1,
                "percentile_thresholds": {"low": 0.5, "high": 0.8}
            },
            "per_asset": {},
            "cap_factor": 1,
            "min_trade_size_eur": 0.0,
            "max_trade_size_eur": 1e6,
        },
        "stop_loss": {},
        "volatility_stop": {},
        "major_cryptos": ["BTC"],
        "liquidity_filter": {"min_volume_usd": 10_000_000},
    }
    rm = RiskManager(mock_rules)
    assert rm.within_position_limits({"BTC": 0.05}) is True
    assert rm.within_position_limits({"BTC": 0.15}) is False
    allow, enriched = rm.filter_signal(
        {"deltas": {"BTC": 0.01}}, {"BTC": 0.01}, nav_eur=1_000.0
    )
    assert isinstance(allow, bool)
    assert isinstance(enriched, dict)
    assert rm.max_position_size(1000.0) <= 1000.0
