from risk_manager_v0_5 import RiskManagerV05


def test_monitor_records_would_block_but_applies_noop():
    # Fuerza dos motivos de bloqueo en active:
    # - position_limits (peso actual excede)
    # - dd_hard (DD 20%)
    rm = RiskManagerV05(
        {
            "risk_manager": {"mode": "monitor"},
            "position_limits": {"max_single_asset_pct": 0.01, "max_crypto_pct": 0.30, "max_altcoin_pct": 0.05},
        }
    )

    signal = {"assets": ["ASSET_X"], "deltas": {"ASSET_X": 0.50}}
    current_weights = {"ASSET_X": 0.50}  # excede max_single_asset_pct=0.01

    dd_cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}

    allow, ann = rm.filter_signal(
        signal,
        current_weights=current_weights,
        nav_eur=1000.0,
        equity_curve=[100.0, 80.0],  # DD=20% -> hard_stop
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices={},
    )

    # Aplicado (monitor) -> NOOP
    assert allow is True
    assert ann["risk_decision"].get("mode") == "monitor"
    assert ann["risk_decision"]["allow_new_trades"] is True
    assert ann.get("risk_allow") is True
    assert ann.get("risk_reasons") == []

    # Observabilidad: lo que habría pasado en active
    assert "risk_monitor" in ann
    mon = ann["risk_monitor"]
    assert mon["would_allow"] is False
    assert "position_limits" in mon["would_reasons"]
    assert "dd_hard" in mon["would_reasons"]
    assert mon["would_decision"]["force_close_positions"] is True


def test_monitor_does_not_apply_kelly_capping_but_records_would_deltas():
    # Fuerza cap muy agresivo para que en active capee el delta
    rm = RiskManagerV05(
        {
            "risk_manager": {"mode": "monitor"},
            "kelly": {"cap_factor": 0.01},
        }
    )

    signal = {"assets": ["ASSET_X"], "deltas": {"ASSET_X": 0.50}}
    allow, ann = rm.filter_signal(
        signal,
        current_weights={},
        nav_eur=1000.0,
        equity_curve=[100.0, 99.0],
        dd_cfg={"max_dd_soft": 0.50, "max_dd_hard": 0.80, "size_multiplier_soft": 1.0},
        atr_ctx={},
        last_prices={},
    )

    # Aplicado (monitor) -> no toca deltas
    assert allow is True
    assert ann["deltas"]["ASSET_X"] == 0.50

    # Would: en active debería capear a ~0.01
    mon = ann["risk_monitor"]
    assert "would_deltas" in mon
    assert mon["would_deltas"]["ASSET_X"] <= 0.02  # tolerancia por floats
