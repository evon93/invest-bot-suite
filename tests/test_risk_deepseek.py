import pytest
from risk_manager_v0_4_shim import RiskManager

# Prueba de compatibilidad con tests existentes 
def test_risk_manager_after_upgrade():
    mock_rules = {
        "position_limits": {"max_single_asset_pct": 0.05},
        "kelly": {"cap_factor": 0.4},
        "major_cryptos": ["BTC", "ETH"]
    }
    
    rm = RiskManager(mock_rules)
    
    # Verifica compatibilidad con tests antiguos
    assert rm.within_position_limits({"BTC": 0.03}) is True
    assert rm.within_position_limits({"BTC": 0.06}) is False
    
    # Verifica nueva funcionalidad
    btc_position = rm.cap_position_size("BTC", 10_000, 0.75)
    assert 0 < btc_position < 10_000
    