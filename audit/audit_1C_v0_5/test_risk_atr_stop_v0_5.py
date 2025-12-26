import math

from risk_manager_v0_5 import RiskManagerV05


# --------------------------------------------------------------------------- #
#  Tests para compute_atr_stop                                               #
# --------------------------------------------------------------------------- #
def test_compute_atr_stop_long_basico():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    # price = 100, atr = 2 → dist_atr = 4, min_stop = 2 → distance = 4
    stop = RiskManagerV05.compute_atr_stop(100.0, 2.0, "long", cfg)
    assert stop is not None
    assert math.isclose(stop, 96.0, rel_tol=1e-9)


def test_compute_atr_stop_short_basico():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    stop = RiskManagerV05.compute_atr_stop(100.0, 2.0, "short", cfg)
    assert stop is not None
    assert math.isclose(stop, 104.0, rel_tol=1e-9)


def test_compute_atr_stop_sin_atr_usa_min_pct():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    stop = RiskManagerV05.compute_atr_stop(100.0, None, "long", cfg)
    # Sin ATR → distancia = 2% del precio → 2
    assert stop is not None
    assert math.isclose(stop, 98.0, rel_tol=1e-9)


def test_compute_atr_stop_precio_invalido():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    stop = RiskManagerV05.compute_atr_stop(0.0, 2.0, "long", cfg)
    assert stop is None
    stop2 = RiskManagerV05.compute_atr_stop("not-a-price", 2.0, "long", cfg)
    assert stop2 is None


def test_compute_atr_stop_side_desconocido():
    cfg = {"atr_multiplier": 2.0, "min_stop_pct": 0.02}
    stop = RiskManagerV05.compute_atr_stop(100.0, 2.0, "weird_side", cfg)
    assert stop is None


# --------------------------------------------------------------------------- #
#  Tests para is_stop_triggered                                              #
# --------------------------------------------------------------------------- #
def test_is_stop_triggered_long_true():
    assert RiskManagerV05.is_stop_triggered("long", 95.0, 94.0) is True
    assert RiskManagerV05.is_stop_triggered("long", 95.0, 95.0) is True


def test_is_stop_triggered_long_false():
    assert RiskManagerV05.is_stop_triggered("long", 95.0, 96.0) is False


def test_is_stop_triggered_short_true():
    assert RiskManagerV05.is_stop_triggered("short", 105.0, 106.0) is True
    assert RiskManagerV05.is_stop_triggered("short", 105.0, 105.0) is True


def test_is_stop_triggered_short_false():
    assert RiskManagerV05.is_stop_triggered("short", 105.0, 104.0) is False


def test_is_stop_triggered_invalid_inputs():
    assert RiskManagerV05.is_stop_triggered("long", "x", 100.0) is False
    assert RiskManagerV05.is_stop_triggered("short", 100.0, "y") is False
    assert RiskManagerV05.is_stop_triggered("unknown", 100.0, 100.0) is False
