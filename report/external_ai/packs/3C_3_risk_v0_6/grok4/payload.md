# Grok4 Payload — RiskManager v0.6 Audit

## Summary

**Context:** RiskManager v0.6 is an event-native wrapper around v0.4, using typed contracts (`OrderIntentV1`, `RiskDecisionV1`).

**Audit Request:** Review architecture, identify edge cases, fill test matrix.

---

## Core Implementation: risk_manager_v0_6.py

```python
class RiskManagerV06:
    """Event-Native Risk Manager v0.6 - Wraps v0.4 with typed contracts."""

    def __init__(self, rules: Union[Dict, str, Path]):
        self._v04 = RiskManagerV04(rules)

    def assess(
        self,
        order_intent: OrderIntentV1,
        *,
        nav: Optional[float] = None,
        default_weight: float = 0.10,
        current_weights: Optional[Dict[str, float]] = None,
    ) -> RiskDecisionV1:
        # 1. Validate intent
        try:
            order_intent.validate()
        except ValidationError:
            return RiskDecisionV1(allowed=False, rejection_reasons=["INVALID_ORDER_INTENT"])

        # 2. Adapt to v0.4 format
        nav_value = nav if nav is not None else 10000.0
        signal = adapt_order_intent_to_risk_input(order_intent, default_weight=default_weight, nav=nav_value)

        # 3. Delegate to v0.4
        allowed, annotated = self._v04.filter_signal(signal, current_weights or {}, nav_eur=nav_value)

        # 4. Normalize reasons and return
        return RiskDecisionV1(allowed=allowed, rejection_reasons=self._normalize_reasons(annotated))

    def _normalize_reasons(self, annotated: Dict[str, Any]) -> List[str]:
        raw = annotated.get("risk_reasons") or annotated.get("rejection_reasons") or annotated.get("reasons")
        if raw is None: return []
        if isinstance(raw, list): return [str(r) for r in raw if r]
        if isinstance(raw, str): return [raw] if raw else []
        if isinstance(raw, dict): return sorted(f"{k}:{v}" for k, v in raw.items() if v)
        return [str(raw)] if raw else []
```

---

## Adapter: risk_input_adapter.py

```python
def adapt_order_intent_to_risk_input(intent: OrderIntentV1, *, default_weight: float = 0.10, nav: Optional[float] = None) -> Dict[str, Any]:
    if not intent.symbol: raise AdapterError("symbol is required")
    if intent.side not in {"BUY", "SELL"}: raise AdapterError(f"side must be BUY or SELL")
    
    target_weight = _compute_target_weight(intent, default_weight, nav)
    if intent.side == "SELL": target_weight = -abs(target_weight)
    
    return {"assets": [intent.symbol], "deltas": {intent.symbol: target_weight}}
```

---

## Test Matrix (Please Fill Missing)

| Scenario | Expected | Tested? | Notes |
|----------|----------|---------|-------|
| Valid BUY intent | allowed or risk-rejected | ✅ | |
| Valid SELL intent | allowed or risk-rejected | ✅ | |
| Empty symbol | allowed=False, INVALID_ORDER_INTENT | ✅ | |
| side="HOLD" | allowed=False, ADAPTER_ERROR | ? | |
| qty=0, notional=None | allowed=False | ? | |
| qty=-1 | allowed=False | ? | |
| LIMIT order, no limit_price | ? | ? | |
| notional only, no NAV | uses default_weight | ? | |
| v0.4 returns dict as reasons | normalized to list[str] | ? | |

---

## Questions

1. Is `_normalize_reasons()` handling all edge cases?
2. What's the expected behavior for short positions (SELL with no existing position)?
3. Should `assess()` propagate ValidationError instead of catching it?

---

**Full code in `txt/` folder. See manifest.md for file list.**
