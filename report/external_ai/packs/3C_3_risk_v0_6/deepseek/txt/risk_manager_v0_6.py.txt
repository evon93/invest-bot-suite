"""
risk_manager_v0_6.py

Event-Native Risk Manager v0.6

Provides an event-driven API that accepts OrderIntentV1 and returns RiskDecisionV1,
internally delegating to RiskManager v0.4 for actual risk evaluation.

This module bridges the gap between the new event contract system (3C) and
the existing risk logic (v0.4), reducing cognitive load and enabling gradual migration.
"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ValidationError
from adapters.risk_input_adapter import (
    adapt_order_intent_to_risk_input,
    AdapterError,
)
from risk_manager_v_0_4 import RiskManager as RiskManagerV04


# Default values
DEFAULT_NAV = 10000.0
DEFAULT_WEIGHT = 0.10


class RiskManagerV06:
    """
    Event-Native Risk Manager v0.6
    
    Wraps RiskManager v0.4 with an event-driven interface.
    
    API:
        assess(order_intent, nav, default_weight, ctx) -> RiskDecisionV1
    
    Example:
        rm = RiskManagerV06("configs/risk_rules.yaml")
        decision = rm.assess(order_intent, nav=10000.0)
        if decision.allowed:
            # proceed with execution
    """

    def __init__(self, rules: Union[Dict, str, Path]):
        """
        Initialize RiskManager v0.6.
        
        Args:
            rules: Risk rules config (dict, path to YAML, or Path object)
        """
        self._v04 = RiskManagerV04(rules)

    def assess(
        self,
        order_intent: OrderIntentV1,
        *,
        nav: Optional[float] = None,
        default_weight: float = DEFAULT_WEIGHT,
        ctx: Optional[Any] = None,
        current_weights: Optional[Dict[str, float]] = None,
    ) -> RiskDecisionV1:
        """
        Assess an OrderIntentV1 and return a RiskDecisionV1.
        
        This method:
        1. Validates the order intent
        2. Adapts it to v0.4 format
        3. Delegates to v0.4 for risk evaluation
        4. Returns a properly typed RiskDecisionV1
        
        Args:
            order_intent: The order intent to assess
            nav: Net Asset Value for weight calculations (default: 10000.0)
            default_weight: Default target weight if can't compute (default: 0.10)
            ctx: Optional context (reserved for future use)
            current_weights: Current portfolio weights (default: empty)
            
        Returns:
            RiskDecisionV1 with allowed status and rejection reasons
            
        Raises:
            ValidationError: If order_intent is invalid
            AdapterError: If conversion to v0.4 format fails
        """
        # 1. Validate intent (if validate() exists)
        try:
            order_intent.validate()
        except ValidationError:
            # Return rejected decision for invalid intents
            return RiskDecisionV1(
                ref_order_event_id=order_intent.event_id,
                allowed=False,
                rejection_reasons=["INVALID_ORDER_INTENT"],
                trace_id=order_intent.trace_id,
                extra={"validation_failed": True},
            )

        # 2. Adapt to v0.4 format
        nav_value = nav if nav is not None else DEFAULT_NAV
        try:
            signal = adapt_order_intent_to_risk_input(
                order_intent,
                default_weight=default_weight,
                nav=nav_value,
            )
        except AdapterError as e:
            return RiskDecisionV1(
                ref_order_event_id=order_intent.event_id,
                allowed=False,
                rejection_reasons=[f"ADAPTER_ERROR:{str(e)}"],
                trace_id=order_intent.trace_id,
                extra={"adapter_error": str(e)},
            )

        # 3. Delegate to v0.4
        weights = current_weights if current_weights is not None else {}
        allowed, annotated = self._v04.filter_signal(signal, weights, nav_eur=nav_value)

        # 4. Extract and normalize rejection reasons
        reasons = self._normalize_reasons(annotated)

        # 5. Build and return RiskDecisionV1
        return RiskDecisionV1(
            ref_order_event_id=order_intent.event_id,
            allowed=allowed,
            rejection_reasons=reasons,
            trace_id=order_intent.trace_id,
            extra={
                "v06_processed": True,
                "delegated_to_v04": True,
                "nav_used": nav_value,
                "default_weight": default_weight,
            },
        )

    def _normalize_reasons(self, annotated: Dict[str, Any]) -> List[str]:
        """
        Extract and normalize rejection reasons from v0.4 annotated output.
        
        Tries multiple keys in order of preference:
        1. risk_reasons (v0.4 standard)
        2. rejection_reasons
        3. reasons
        
        Handles various input types:
        - list[str]: returned as-is
        - str: wrapped in list
        - dict: converted to ["key:value", ...] sorted
        - None: empty list
        
        Returns:
            List of string reasons, always normalized
        """
        # Try keys in order of preference
        raw = None
        for key in ("risk_reasons", "rejection_reasons", "reasons"):
            if key in annotated:
                raw = annotated[key]
                break

        if raw is None:
            return []

        if isinstance(raw, list):
            # Ensure all items are strings
            return [str(r) for r in raw if r]

        if isinstance(raw, str):
            return [raw] if raw else []

        if isinstance(raw, dict):
            # Convert dict to sorted list of "key:value" strings
            return sorted(f"{k}:{v}" for k, v in raw.items() if v)

        # Fallback: try to convert to string
        return [str(raw)] if raw else []

    @property
    def v04(self) -> RiskManagerV04:
        """Access the underlying v0.4 RiskManager."""
        return self._v04
