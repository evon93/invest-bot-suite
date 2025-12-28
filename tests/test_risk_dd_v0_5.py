import math

from risk_manager_v0_5 import RiskManagerV05


# --------------------------------------------------------------------------- #
#  Tests para compute_drawdown                                                #
# --------------------------------------------------------------------------- #
def test_compute_drawdown_empty_curve():
    result = RiskManagerV05.compute_drawdown([])
    assert result["max_dd"] == 0.0
    assert result["peak_idx"] is None
    assert result["trough_idx"] is None


def test_compute_drawdown_monotonic_up():
    curve = [100.0, 105.0, 110.0, 120.0]
    result = RiskManagerV05.compute_drawdown(curve)
    assert math.isclose(result["max_dd"], 0.0, rel_tol=1e-9)
    # El peak se va actualizando; el trough del max_dd (0) puede ser el último índice
    assert result["peak_idx"] == result["trough_idx"]


def test_compute_drawdown_with_clear_dd():
    # Pico en 120, cae a 96 → DD = (120-96)/120 = 0.2
    curve = [100.0, 110.0, 120.0, 115.0, 96.0]
    result = RiskManagerV05.compute_drawdown(curve)
    assert math.isclose(result["max_dd"], 0.2, rel_tol=1e-9)
    assert result["peak_idx"] == 2  # valor 120
    assert result["trough_idx"] == 4  # valor 96


# --------------------------------------------------------------------------- #
#  Tests para eval_dd_guardrail                                               #
# --------------------------------------------------------------------------- #
def test_eval_dd_guardrail_normal_zone():
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    res = RiskManagerV05.eval_dd_guardrail(0.02, cfg)
    assert res["state"] == "normal"
    assert res["allow_new_trades"] is True
    assert math.isclose(res["size_multiplier"], 1.0, rel_tol=1e-9)
    assert res["hard_stop"] is False


def test_eval_dd_guardrail_soft_zone():
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    res = RiskManagerV05.eval_dd_guardrail(0.07, cfg)
    assert res["state"] == "risk_off_light"
    assert res["allow_new_trades"] is True
    assert math.isclose(res["size_multiplier"], 0.5, rel_tol=1e-9)
    assert res["hard_stop"] is False


def test_eval_dd_guardrail_hard_zone():
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    res = RiskManagerV05.eval_dd_guardrail(0.15, cfg)
    assert res["state"] == "hard_stop"
    assert res["allow_new_trades"] is False
    assert math.isclose(res["size_multiplier"], 0.0, rel_tol=1e-9)
    assert res["hard_stop"] is True


def test_eval_dd_guardrail_invalid_input():
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    res = RiskManagerV05.eval_dd_guardrail("not-a-number", cfg)
    assert res["state"] == "normal"
    assert res["allow_new_trades"] is True
    assert math.isclose(res["size_multiplier"], 1.0, rel_tol=1e-9)
    assert res["hard_stop"] is False
