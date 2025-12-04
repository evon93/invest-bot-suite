import math
import pytest
from risk_manager_v0_5 import RiskManagerV05

# --------------------------------------------------------------------------- #
#  Extended Tests for compute_drawdown
# --------------------------------------------------------------------------- #
def test_compute_drawdown_nan_values():
    # Test behavior with NaN in the curve
    curve = [100.0, 110.0, float('nan'), 105.0]
    # Expectation: Should handle gracefully or propagate. 
    # Current implementation will likely fail comparison with NaN or propagate it.
    # Let's see what happens.
    try:
        result = RiskManagerV05.compute_drawdown(curve)
        # If it returns, check if max_dd is valid
        assert not math.isnan(result["max_dd"]), "Max DD should not be NaN"
    except Exception as e:
        pytest.fail(f"compute_drawdown raised exception on NaN: {e}")

def test_compute_drawdown_negative_values():
    # Curve goes negative (bankruptcy scenario)
    curve = [100.0, 50.0, -10.0, -20.0]
    result = RiskManagerV05.compute_drawdown(curve)
    # Peak is 100. Min is -20. DD = (100 - (-20)) / 100 = 1.2
    assert math.isclose(result["max_dd"], 1.2, rel_tol=1e-9)

def test_compute_drawdown_all_negative():
    # Started underwater and stayed there
    curve = [-10.0, -20.0, -5.0]
    result = RiskManagerV05.compute_drawdown(curve)
    # Peak <= 0 logic triggers "continue"
    # Should result in 0.0 DD because no valid peak was established > 0
    assert result["max_dd"] == 0.0

# --------------------------------------------------------------------------- #
#  Extended Tests for eval_dd_guardrail
# --------------------------------------------------------------------------- #
def test_eval_dd_guardrail_boundary_exact():
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    
    # Exact soft limit
    res_soft = RiskManagerV05.eval_dd_guardrail(0.05, cfg)
    # 0.05 < 0.05 is False -> checks < 0.10 -> True -> risk_off_light
    assert res_soft["state"] == "risk_off_light"
    
    # Exact hard limit
    res_hard = RiskManagerV05.eval_dd_guardrail(0.10, cfg)
    # 0.10 < 0.10 is False -> hard_stop
    assert res_hard["state"] == "hard_stop"

# --------------------------------------------------------------------------- #
#  Extended Tests for compute_atr_stop
# --------------------------------------------------------------------------- #
def test_compute_atr_stop_zero_atr():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    # ATR = 0.0 -> Should fall back to min_stop_pct
    stop = RiskManagerV05.compute_atr_stop(100.0, 0.0, "long", cfg)
    # min_dist = 2.0. stop = 98.0
    assert math.isclose(stop, 98.0, rel_tol=1e-9)

def test_compute_atr_stop_large_atr():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    # ATR = 10.0 -> dist_atr = 20.0. min_dist = 2.0. max = 20.0
    stop = RiskManagerV05.compute_atr_stop(100.0, 10.0, "long", cfg)
    assert math.isclose(stop, 80.0, rel_tol=1e-9)

def test_compute_atr_stop_negative_price_input():
    cfg = {}
    stop = RiskManagerV05.compute_atr_stop(-100.0, 5.0, "long", cfg)
    assert stop is None

# --------------------------------------------------------------------------- #
#  Extended Tests for is_stop_triggered
# --------------------------------------------------------------------------- #
def test_is_stop_triggered_exact_match():
    # Long: last == stop -> True
    assert RiskManagerV05.is_stop_triggered("long", 100.0, 100.0) is True
    # Short: last == stop -> True
    assert RiskManagerV05.is_stop_triggered("short", 100.0, 100.0) is True

def test_is_stop_triggered_precision():
    # Floating point proximity
    stop = 100.0
    last = 100.0000000000001
    # Long: last > stop -> False
    assert RiskManagerV05.is_stop_triggered("long", stop, last) is False
    
    last_below = 99.9999999999999
    # Long: last < stop -> True
    assert RiskManagerV05.is_stop_triggered("long", stop, last_below) is True
