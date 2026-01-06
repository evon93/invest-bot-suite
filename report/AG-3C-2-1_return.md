# AG-3C-2-1 Return Packet — Risk Input Adapter

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-2-1 (WSL + venv)  
**Rama:** `feature/3C_2_risk_input_adapter`  
**Estado:** ✅ COMPLETADO

---

## 1. Archivos Añadidos

| Archivo | Descripción |
|---------|-------------|
| `adapters/__init__.py` | Package init con exports |
| `adapters/risk_input_adapter.py` | Adapter para convertir OrderIntentV1 a dict para RiskManager |
| `tests/test_risk_input_adapter.py` | 14 tests unitarios |

---

## 2. Funciones Implementadas

### `adapt_order_intent_to_risk_input(intent, default_weight, nav)`

Convierte `OrderIntentV1` al formato dict esperado por `RiskManager.filter_signal()`:

```python
{
    "assets": [symbol],
    "deltas": {symbol: target_weight},
    "_adapter_meta": {...}
}
```

**Comportamiento:**

- `BUY` → weight positivo
- `SELL` → weight negativo
- Si `notional` + `nav` disponibles: weight = notional/nav
- Si solo `qty`: usa `default_weight` (0.10)

**Validación:**

- `symbol` requerido (AdapterError si vacío)
- `side` ∈ {BUY, SELL}
- `qty > 0` OR `notional > 0`

### `adapt_risk_output_to_decision(intent, allowed, annotated)`

Convierte el output de `RiskManager.filter_signal()` a `RiskDecisionV1`:

- Propaga `ref_order_event_id`, `trace_id`
- Extrae `rejection_reasons` del annotated dict

---

## 3. Tests

| Test | Descripción |
|------|-------------|
| test_buy_with_qty | BUY con qty usa default weight |
| test_sell_with_qty | SELL produce weight negativo |
| test_limit_order_with_price | LIMIT preserva limit_price en meta |
| test_notional_with_nav | Calcula weight = notional/nav |
| test_error_missing_symbol | AdapterError si symbol vacío |
| test_error_invalid_side | AdapterError si side inválido |
| test_error_qty_zero | AdapterError si qty <= 0 |
| ... | (14 tests total) |

---

## 4. Compatibilidad

- **No modifica** runner 3B (mantiene `risk_shim_adapter` inline)
- Adapter disponible para adopción gradual en 3C+
- Usa `OrderIntentV1` de `contracts/events_v1.py`

---

## 5. Commit

```
82a5e9b 3C.2: extract risk input adapter + tests
```

**pytest:** 254 passed, 7 skipped (+14 tests nuevos)

---

## 6. Artefactos

- [AG-3C-2-1_pytest.txt](AG-3C-2-1_pytest.txt)
- [AG-3C-2-1_diff.patch](AG-3C-2-1_diff.patch)
- [AG-3C-2-1_last_commit.txt](AG-3C-2-1_last_commit.txt)
