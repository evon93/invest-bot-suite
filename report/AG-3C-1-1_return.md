# AG-3C-1-1 Return Packet — Contracts Canonicalization v1

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-1-1 (WSL + venv)  
**Rama:** `feature/3C_1_contracts_v1`  
**Estado:** ✅ COMPLETADO

---

## 1. Archivos Añadidos

| Archivo | Descripción |
|---------|-------------|
| `contracts/events_v1.py` | Contratos canónicos v1 (OrderIntentV1, RiskDecisionV1, ExecutionReportV1) |
| `tests/test_contracts_events_v1_roundtrip.py` | Tests de roundtrip, aliases, y validación |

---

## 2. Contratos Implementados

### OrderIntentV1

- **Campos**: symbol, side, qty, order_type, limit_price, notional, event_id, ts, trace_id, meta
- **Aliases from_dict**: `ticker/asset` → symbol, `quantity/amount` → qty, `action/direction` → side, `type` → order_type
- **Normalización**: side → UPPERCASE
- **Validación**: symbol requerido, side ∈ {BUY,SELL}, qty>0 OR notional>0, limit_price requerido si LIMIT

### RiskDecisionV1

- **Campos**: ref_order_event_id, allowed, adjusted_qty, adjusted_notional, rejection_reasons, extra
- **Aliases from_dict**: `reasons/reason` → rejection_reasons, `order_id/order_event_id` → ref_order_event_id
- **Normalización**: rejection_reasons → list[str] (acepta string único, None, list)
- **Validación**: ref_order_event_id requerido, rejection_reasons debe ser list

### ExecutionReportV1

- **Campos**: ref_order_event_id, status, filled_qty, avg_price, fee, slippage, latency_ms, ref_risk_event_id, extra
- **Aliases from_dict**: `order_id` → ref_order_event_id, `price/fill_price` → avg_price, `qty/quantity` → filled_qty
- **Validación**: ref_order_event_id requerido, status ∈ VALID_STATUSES, filled_qty≥0, avg_price≥0

---

## 3. Tests

| Suite | Tests | Resultado |
|-------|-------|-----------|
| test_contracts_events_v1_roundtrip.py | 22 tests | ✅ PASS |
| pytest completo | 240 passed, 7 skipped | ✅ PASS |

**Cobertura de tests:**

- Roundtrip obj→dict→obj para los 3 contratos
- from_dict con aliases legacy
- validate() PASS en casos válidos
- validate() FAIL: empty symbol, invalid side, qty≤0, invalid status, negative values

---

## 4. Commit

```
425f6c7 3C.1: add events_v1 contracts + roundtrip tests
```

Push: `feature/3C_1_contracts_v1` → origin

---

## 5. Artefactos

- [AG-3C-1-1_pytest.txt](AG-3C-1-1_pytest.txt)
- [AG-3C-1-1_diff.patch](AG-3C-1-1_diff.patch)
- [AG-3C-1-1_last_commit.txt](AG-3C-1-1_last_commit.txt)

---

## 6. Compatibilidad

- **No modifica** `event_messages.py` existente (pipeline 3B intacto)
- **No añade** dependencias nuevas
- Coexiste con contratos legacy; v1 puede adoptarse gradualmente
