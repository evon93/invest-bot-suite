from __future__ import annotations

import logging

from risk_logging import emit_risk_decision_log


def test_emit_risk_decision_log_enabled_emits(caplog):
    logger = logging.getLogger("test_risk_logging")
    caplog.set_level(logging.INFO, logger="test_risk_logging")

    emit_risk_decision_log(
        logger=logger,
        enabled=True,
        mode="active",
        risk_ctx=None,
        risk_decision={
            "allow_new_trades": True,
            "force_close_positions": False,
            "size_multiplier": 1.0,
            "stop_signals": [],
            "reasons": [],
        },
        annotated={
            "risk_allow": True,
            "risk_reasons": [],
            "risk_decision": {"dummy": True},
        },
    )

    recs = [r for r in caplog.records if r.name == "test_risk_logging"]
    assert any("RISK_DECISION" in r.message for r in recs)

    rec = next(r for r in recs if "RISK_DECISION" in r.message)
    assert getattr(rec, "risk_event", None) == "risk_decision_v0_5"
    assert getattr(rec, "risk_mode", None) == "active"


def test_emit_risk_decision_log_disabled_is_noop(caplog):
    logger = logging.getLogger("test_risk_logging_disabled")
    caplog.set_level(logging.INFO, logger="test_risk_logging_disabled")

    emit_risk_decision_log(
        logger=logger,
        enabled=False,
        mode="active",
        risk_ctx=None,
        risk_decision={"allow_new_trades": True},
        annotated={"risk_allow": True},
    )

    recs = [r for r in caplog.records if r.name == "test_risk_logging_disabled"]
    assert recs == []
