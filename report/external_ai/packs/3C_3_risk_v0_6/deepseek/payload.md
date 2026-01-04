# DeepSeek Payload — Logic Audit & Parity Verification

## Summary

**Context:** RiskManager v0.6 wraps v0.4 internally. They should produce equivalent risk decisions.

**Audit Request:** Verify logic correctness, check v0.4/v0.6 parity, suggest additional tests.

---

## v0.6 Delegation Flow

```python
# risk_manager_v0_6.py
def assess(self, order_intent, nav=None, current_weights=None):
    # 1. Validate
    order_intent.validate()  # raises ValidationError if invalid
    
    # 2. Convert to v0.4 format
    signal = adapt_order_intent_to_risk_input(order_intent, nav=nav)
    # signal = {"assets": [symbol], "deltas": {symbol: weight}}
    
    # 3. Delegate to v0.4
    allowed, annotated = self._v04.filter_signal(signal, current_weights or {}, nav_eur=nav)
    
    # 4. Return RiskDecisionV1
    return RiskDecisionV1(allowed=allowed, rejection_reasons=annotated.get("risk_reasons", []))
```

---

## v0.4 Reference (filter_signal)

```python
# risk_manager_v_0_4.py
def filter_signal(self, signal: dict, current_weights: dict, nav_eur: float = None):
    allow = True
    reasons = []
    
    # 1. Position limits check
    if not self.within_position_limits(current_weights):
        allow = False
        reasons.append("position_limits")
    
    # 2. Liquidity check (stub)
    for asset in signal.get("assets", []):
        if not self._check_liquidity(asset):
            allow = False
            reasons.append(f"liquidity:{asset}")
    
    # 3. Kelly cap check
    if nav_eur:
        for asset, target_weight in signal.get("deltas", {}).items():
            max_weight = self.cap_position_size(asset, nav_eur, vol_pct) / nav_eur
            if target_weight > max_weight:
                allow = False
                reasons.append(f"kelly_cap:{asset}")
    
    return allow, {"risk_reasons": reasons, ...}
```

---

## Parity Test Example

```python
def test_parity_buy(v04, v06):
    signal = {"assets": ["BTC"], "deltas": {"BTC": 0.10}}
    allowed_v04, _ = v04.filter_signal(signal, {}, nav_eur=10000)
    
    intent = OrderIntentV1(symbol="BTC", side="BUY", qty=1.0)
    decision = v06.assess(intent, nav=10000, default_weight=0.10)
    
    assert decision.allowed == allowed_v04  # MUST MATCH
```

---

## Potential Parity Issues

| Scenario | v0.4 | v0.6 | Match? |
|----------|------|------|--------|
| BUY with qty | signal["deltas"] = default_weight | same | ✅ |
| BUY with notional | N/A | weight = notional/nav | ? |
| SELL (negative weight) | signal["deltas"] = -weight | same | ? |
| current_weights populated | checked by within_position_limits | passed through | ? |
| vol_pct for Kelly | hardcoded 0.65 in v0.4 | same | ✅ |

---

## Suggested Additional Tests

1. `test_parity_with_populated_current_weights`
2. `test_parity_sell_no_existing_position`
3. `test_parity_notional_vs_qty`
4. `test_parity_different_nav_values`
5. `test_parity_when_position_limits_exceeded`

---

**Full code in `txt/` folder. See manifest.md for file list.**
