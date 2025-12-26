import pytest

from risk_manager_v0_5 import RiskManagerV05


def make_rm(rules=None) -> RiskManagerV05:
    """Crea un RiskManagerV05 con reglas mínimas."""
    if rules is None:
        rules = {}
    return RiskManagerV05(rules)


def test_decision_normal():
    """
    Escenario base sin DD relevante, sin stops ATR y sin límites/kelly activos.
    Debe permitir nuevas operaciones, sin forzar cierres ni reducir tamaño.
    """
    rm = make_rm()

    signal = {
        "assets": ["BTC"],
        "deltas": {"BTC": 0.01},
    }
    current_weights = {"BTC": 0.01}
    nav_eur = 10_000.0

    equity_curve = [100.0, 102.0, 101.0, 103.0]
    dd_cfg = {
        "max_dd_soft": 0.05,
        "max_dd_hard": 0.10,
        "size_multiplier_soft": 0.5,
    }

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=nav_eur,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]

    assert allow is True
    assert annotated["risk_allow"] is True

    assert decision["allow_new_trades"] is True
    assert decision["force_close_positions"] is False
    assert decision["size_multiplier"] == pytest.approx(1.0)
    assert decision["stop_signals"] == []
    assert "dd_soft" not in decision["reasons"]
    assert "dd_hard" not in decision["reasons"]
    assert "stop_loss_atr" not in decision["reasons"]
    assert "position_limits" not in decision["reasons"]


def test_decision_dd_soft():
    """
    Drawdown en zona soft: DD entre max_dd_soft y max_dd_hard.
    Debe reducir size_multiplier ("risk_off_light") pero seguir permitiendo trades.
    """
    rm = make_rm()

    signal = {
        "assets": ["BTC"],
        "deltas": {"BTC": 0.01},
    }
    current_weights = {"BTC": 0.01}
    nav_eur = 10_000.0

    # DD ~6% (entre 5% y 10%) → estado soft
    equity_curve = [100.0, 95.0, 94.0]
    dd_cfg = {
        "max_dd_soft": 0.05,
        "max_dd_hard": 0.10,
        "size_multiplier_soft": 0.5,
    }

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=nav_eur,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]

    assert allow is True
    assert annotated["risk_allow"] is True

    assert decision["allow_new_trades"] is True
    assert decision["force_close_positions"] is False
    assert 0.0 < decision["size_multiplier"] < 1.0
    assert "dd_soft" in decision["reasons"]
    assert "dd_hard" not in decision["reasons"]


def test_decision_dd_hard():
    """
    Drawdown en zona hard: DD >= max_dd_hard.
    Debe bloquear nuevas operaciones, forzar cierre y size_multiplier = 0.
    """
    rm = make_rm()

    signal = {
        "assets": ["BTC"],
        "deltas": {"BTC": 0.01},
    }
    current_weights = {"BTC": 0.01}
    nav_eur = 10_000.0

    # DD 20% (> 10%) → estado hard_stop
    equity_curve = [100.0, 80.0]
    dd_cfg = {
        "max_dd_soft": 0.05,
        "max_dd_hard": 0.10,
        "size_multiplier_soft": 0.5,
    }

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=nav_eur,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]

    assert allow is False
    assert annotated["risk_allow"] is False

    assert decision["allow_new_trades"] is False
    assert decision["force_close_positions"] is True
    assert decision["size_multiplier"] == pytest.approx(0.0)
    assert "dd_hard" in decision["reasons"]


def test_decision_atr_stop():
    """
    Sin DD relevante, pero con un stop ATR activado para un ticker.
    Debe marcar el ticker en stop_signals y añadir motivo 'stop_loss_atr',
    sin necesidad de bloquear nuevas operaciones globalmente.
    """
    rm = make_rm()

    signal = {
        "assets": ["BTC"],
        "deltas": {"BTC": 0.01},
    }
    current_weights = {"BTC": 0.01}
    nav_eur = 10_000.0

    equity_curve = [100.0, 101.0, 102.0]
    dd_cfg = {
        "max_dd_soft": 0.05,
        "max_dd_hard": 0.10,
        "size_multiplier_soft": 0.5,
    }

    atr_ctx = {
        "BTC": {
            "entry_price": 100.0,
            "atr": 2.0,
            "side": "long",
            "atr_multiplier": 2.0,
            "min_stop_pct": 0.01,
            "last_price": 95.0,  # muy por debajo del stop
        }
    }

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=nav_eur,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx=atr_ctx,
        last_prices={},
    )

    decision = annotated["risk_decision"]

    assert allow is True
    assert annotated["risk_allow"] is True

    assert "BTC" in decision["stop_signals"]
    assert "stop_loss_atr" in decision["reasons"]


def test_decision_limits_and_kelly():
    """
    Caso combinado donde:
    - Se violan límites de posición (position_limits).
    - Kelly recorta un delta excesivo para un activo.

    Debe reflejar ambos motivos en risk_decision.reasons.
    """
    rules = {
        "position_limits": {
            "max_single_asset_pct": 0.10,
            "max_crypto_pct": 0.30,
            "max_altcoin_pct": 0.05,
        },
        "major_cryptos": ["CRYPTO_BTC", "CRYPTO_ETH"],
        "kelly": {
            "cap_factor": 0.5,
            "crypto_overrides": {
                "high_vol": 0.3,
                "med_vol": 0.4,
                "low_vol": 0.5,
            },
            "percentile_thresholds": {"low": 0.5, "high": 0.8},
        },
    }
    rm = make_rm(rules=rules)

    # Violamos max_crypto_pct con la suma de pesos crypto
    current_weights = {
        "CRYPTO_BTC": 0.20,
        "CRYPTO_ETH": 0.20,
    }

    # Delta demasiado grande para Kelly (0.8 > 0.4 esperado por overrides)
    signal = {
        "assets": ["CRYPTO_BTC"],
        "deltas": {"CRYPTO_BTC": 0.8},
    }
    nav_eur = 10_000.0

    equity_curve = [100.0, 101.0, 102.0]  # sin DD relevante
    dd_cfg = {
        "max_dd_soft": 0.05,
        "max_dd_hard": 0.10,
        "size_multiplier_soft": 0.5,
    }

    allow, annotated = rm.filter_signal(
        signal,
        current_weights,
        nav_eur=nav_eur,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    decision = annotated["risk_decision"]

    # Debe haber bloqueado por límites/Kelly
    assert allow is False
    assert annotated["risk_allow"] is False

    assert decision["allow_new_trades"] is False
    assert "position_limits" in decision["reasons"]
    assert any(
        r.startswith("kelly_cap:CRYPTO_BTC") for r in decision["reasons"]
    )
