from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Optional

try:
    from risk_context_v0_6 import RiskContextV06
except Exception:  # pragma: no cover
    RiskContextV06 = Any  # type: ignore


def emit_risk_decision_log(
    *,
    logger: logging.Logger,
    enabled: bool,
    mode: str,
    risk_ctx: Optional[RiskContextV06],
    risk_decision: Mapping[str, Any],
    annotated: Mapping[str, Any],
) -> None:
    """
    Logging estructurado mínimo para decisiones de riesgo.
    - enabled=False => no hace nada.
    - No lanza excepciones (best-effort).
    """
    if not enabled:
        return

    try:
        payload: dict[str, Any] = {
            "event": "risk_decision_v0_5",
            "mode": mode,
            "risk_allow": annotated.get("risk_allow"),
            "risk_reasons": annotated.get("risk_reasons"),
            "risk_decision": dict(risk_decision),
        }

        # Campo opcional: portfolio_id si existe en raw
        if risk_ctx is not None and hasattr(risk_ctx, "raw"):
            raw = getattr(risk_ctx, "raw") or {}
            portfolio = raw.get("portfolio") or {}
            payload["portfolio_id"] = portfolio.get("portfolio_id") or raw.get("portfolio_id")

        # Log como JSON + extra para caplog/consumo futuro
        logger.info(
            "RISK_DECISION %s",
            json.dumps(payload, sort_keys=True),
            extra={
                "risk_event": payload.get("event"),
                "risk_mode": mode,
            },
        )
    except Exception:
        logger.exception("RISK_DECISION logging failed")
