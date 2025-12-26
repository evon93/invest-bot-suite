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


# --------------------------------------------------------------------------- #
#  Tests for dd_skipped / atr_skipped flags (1D.core)
# --------------------------------------------------------------------------- #
def make_rm(rules=None) -> RiskManagerV05:
    """Crea un RiskManagerV05 con reglas mínimas."""
    if rules is None:
        rules = {}
    return RiskManagerV05(rules)


def test_filter_signal_dd_skipped_empty_equity():
    """
    Caso: equity_curve vacía → dd_skipped=True, sin excepción.
    """
    rm = make_rm()
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.01}}
    current_weights = {"BTC": 0.01}
    dd_cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=10_000.0,
        equity_curve=[],
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]
    
    # DD skipped, no exception
    assert decision.get("dd_skipped") is True
    assert "dd_skipped_reason" in annotated
    # Should still allow trades (degrade-to-safe)
    assert allow is True


def test_filter_signal_dd_skipped_only_nan():
    """
    Caso: equity_curve solo NaN/inf → dd_skipped=True, sin excepción.
    """
    rm = make_rm()
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.01}}
    current_weights = {"BTC": 0.01}
    dd_cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=10_000.0,
        equity_curve=[float('nan'), float('inf'), float('-inf')],
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]
    
    assert decision.get("dd_skipped") is True
    assert annotated.get("dd_skipped_reason") == "invalid_or_empty_equity_curve"
    assert allow is True


def test_filter_signal_dd_skipped_missing_context():
    """
    Caso: falta equity_curve o dd_cfg → dd_skipped=True.
    """
    rm = make_rm()
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.01}}
    current_weights = {"BTC": 0.01}

    # Sin equity_curve ni dd_cfg
    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=10_000.0,
    )

    decision = annotated["risk_decision"]
    
    assert decision.get("dd_skipped") is True
    assert annotated.get("dd_skipped_reason") == "missing_equity_curve_or_dd_cfg"
    assert allow is True


def test_filter_signal_atr_skipped_empty_ctx():
    """
    Caso: atr_ctx vacío → atr_skipped=True, sin excepción.
    """
    rm = make_rm()
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.01}}
    current_weights = {"BTC": 0.01}
    dd_cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=10_000.0,
        equity_curve=[100.0, 101.0],
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]
    
    assert decision.get("atr_skipped") is True
    assert annotated.get("atr_skipped_reason") == "missing_or_empty_atr_ctx"
    assert allow is True


def test_filter_signal_atr_skipped_missing_ctx():
    """
    Caso: atr_ctx no pasado → atr_skipped=True.
    """
    rm = make_rm()
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.01}}
    current_weights = {"BTC": 0.01}
    dd_cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=10_000.0,
        equity_curve=[100.0, 101.0],
        dd_cfg=dd_cfg,
        # atr_ctx no pasado
    )

    decision = annotated["risk_decision"]
    
    assert decision.get("atr_skipped") is True
    assert allow is True


def test_compute_drawdown_skipped_flag():
    """
    Verifica que compute_drawdown devuelve skipped=True para curvas vacías/invalidas
    y skipped=False para curvas válidas.
    """
    # Curva vacía
    result_empty = RiskManagerV05.compute_drawdown([])
    assert result_empty["skipped"] is True
    assert result_empty["max_dd"] == 0.0
    
    # Curva solo NaN
    result_nan = RiskManagerV05.compute_drawdown([float('nan'), float('nan')])
    assert result_nan["skipped"] is True
    
    # Curva válida
    result_valid = RiskManagerV05.compute_drawdown([100.0, 95.0, 98.0])
    assert result_valid["skipped"] is False
    assert result_valid["max_dd"] > 0.0

