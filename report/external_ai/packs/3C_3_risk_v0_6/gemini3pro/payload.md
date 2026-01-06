# Gemini3Pro Payload — Serialization & Validation Audit

## Summary

**Context:** Typed contracts for event-driven architecture with `to_dict`/`from_dict`/`validate` methods.

**Audit Request:** Review serialization correctness, invariant validation, suggest small improvements (<=30 lines).

---

## Contract: OrderIntentV1 (events_v1.py)

```python
@dataclass
class OrderIntentV1:
    symbol: str
    side: str
    qty: Optional[float] = None
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    notional: Optional[float] = None
    # ... auto-generated fields: event_id, ts, trace_id, meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": "OrderIntentV1",
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            # ... all fields
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderIntentV1":
        d = _apply_aliases(data, ALIASES_ORDER_INTENT)  # ticker->symbol, action->side, etc.
        return cls(symbol=d.get("symbol", ""), side=d.get("side", ""), ...)

    def validate(self) -> bool:
        if not self.symbol: raise ValidationError("symbol is required")
        if self.side not in {"BUY", "SELL"}: raise ValidationError("side must be BUY or SELL")
        if not (self.qty > 0 or self.notional > 0): raise ValidationError("qty or notional must be > 0")
        if self.order_type == "LIMIT" and self.limit_price is None: raise ValidationError("limit_price required")
        return True
```

---

## Alias Mapping

```python
ALIASES_ORDER_INTENT = {
    "ticker": "symbol", "asset": "symbol",
    "quantity": "qty", "amount": "qty",
    "action": "side", "direction": "side",
    "type": "order_type",
}
```

---

## Roundtrip Test Example

```python
def test_roundtrip_basic():
    original = OrderIntentV1(symbol="BTC/USDT", side="buy", qty=1.5)
    d = original.to_dict()
    restored = OrderIntentV1.from_dict(d)
    assert restored.symbol == original.symbol
    assert restored.side == "BUY"  # normalized
```

---

## Questions

1. Is `from_dict()` handling type coercion for `qty` (e.g., string "1.5")?
2. Should `validate()` check `qty > 0` even when `notional` is provided?
3. Are there missing invariants in `validate()`?

## Suggested Improvements Format

```markdown
1. [Add type coercion in from_dict for numeric fields] - ~10 lines
2. [Add schema_version validation] - ~5 lines
3. ...
```

---

**Full code in `txt/` folder. See manifest.md for file list.**
