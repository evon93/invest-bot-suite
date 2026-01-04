"""
adapters/risk_input_adapter.py

Adapter para convertir OrderIntentV1 a formato compatible con RiskManager.

Centraliza el "shim" que antes vivía inline en el runner, reduciendo
carga cognitiva y facilitando testing unitario.
"""

from typing import Dict, Any, Optional
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ValidationError


# Default target weight when only qty is provided (conservative)
DEFAULT_TARGET_WEIGHT = 0.10


class AdapterError(Exception):
    """Error during adapter conversion."""
    pass


def adapt_order_intent_to_risk_input(
    intent: OrderIntentV1,
    *,
    default_weight: float = DEFAULT_TARGET_WEIGHT,
    nav: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Adapta un OrderIntentV1 al formato dict esperado por RiskManager.filter_signal().

    El RiskManager v0.4 espera:
        signal = {
            "assets": [symbol, ...],
            "deltas": {symbol: target_weight, ...}
        }

    Este adapter:
    1. Valida campos mínimos del intent
    2. Convierte qty/notional a un target weight aproximado
    3. Retorna el dict listo para filter_signal()

    Args:
        intent: OrderIntentV1 a adaptar
        default_weight: Peso target por defecto si no se puede calcular
        nav: NAV para calcular weight desde notional (opcional)

    Returns:
        Dict compatible con RiskManager.filter_signal()

    Raises:
        AdapterError: Si el intent no tiene datos válidos
    """
    # Validación básica
    if not intent.symbol or not intent.symbol.strip():
        raise AdapterError("symbol is required")

    if intent.side not in {"BUY", "SELL"}:
        raise AdapterError(f"side must be BUY or SELL, got '{intent.side}'")

    # Determinar target weight
    target_weight = _compute_target_weight(intent, default_weight, nav)

    # Ajustar signo según side (SELL = peso negativo/reducción)
    if intent.side == "SELL":
        target_weight = -abs(target_weight)
    else:
        target_weight = abs(target_weight)

    return {
        "assets": [intent.symbol],
        "deltas": {intent.symbol: target_weight},
        # Metadata para trazabilidad
        "_adapter_meta": {
            "source_event_id": intent.event_id,
            "order_type": intent.order_type,
            "limit_price": intent.limit_price,
            "original_qty": intent.qty,
            "original_notional": intent.notional,
        }
    }


def _compute_target_weight(
    intent: OrderIntentV1,
    default_weight: float,
    nav: Optional[float],
) -> float:
    """
    Calcula el target weight a partir de qty/notional.

    Estrategia:
    1. Si notional y nav disponibles: weight = notional / nav
    2. Si qty disponible pero no notional: usa default_weight
    3. Si ninguno válido: AdapterError

    Returns:
        Target weight (0.0 - 1.0 típicamente)
    """
    has_qty = intent.qty is not None and intent.qty > 0
    has_notional = intent.notional is not None and intent.notional > 0

    if not has_qty and not has_notional:
        raise AdapterError("qty or notional must be > 0")

    # Preferir notional si NAV disponible
    if has_notional and nav and nav > 0:
        return intent.notional / nav

    # Fallback a default weight
    return default_weight


def adapt_risk_output_to_decision(
    intent: OrderIntentV1,
    allowed: bool,
    annotated: Dict[str, Any],
) -> RiskDecisionV1:
    """
    Convierte el output de RiskManager.filter_signal() a RiskDecisionV1.

    Args:
        intent: OrderIntent original (para ref_order_event_id)
        allowed: Resultado del filter_signal
        annotated: Dict anotado devuelto por filter_signal

    Returns:
        RiskDecisionV1 con datos normalizados
    """
    reasons = annotated.get("risk_reasons", [])

    # Calcular adjusted_qty si el delta fue modificado
    adjusted_qty = None
    original_symbol = intent.symbol
    if original_symbol in annotated.get("deltas", {}):
        # El RiskManager puede haber ajustado el delta
        # pero no tenemos forma directa de convertir de vuelta a qty
        # Dejamos None por ahora (futuro: pasar NAV para calcular)
        pass

    return RiskDecisionV1(
        ref_order_event_id=intent.event_id,
        allowed=allowed,
        adjusted_qty=adjusted_qty,
        rejection_reasons=reasons,
        trace_id=intent.trace_id,
        extra={"adapter_processed": True},
    )
