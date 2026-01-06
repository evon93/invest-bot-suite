# AG-3C-3-1 Return Packet — RiskManager v0.6 Event-Native

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-3-1 (WSL + venv)  
**Rama:** `feature/3C_3_riskmanager_v0_6`  
**Estado:** ✅ COMPLETADO

---

## 1. Archivos Añadidos/Modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `risk_manager_v0_6.py` | NUEVO | RiskManager v0.6 event-native |
| `tests/test_risk_manager_v0_6_contract.py` | NUEVO | 11 tests de contrato |
| `tests/test_risk_manager_v0_6_compat_v0_4_parity.py` | NUEVO | 6 tests de paridad |
| `tools/run_live_integration_3B.py` | MOD | Añadido --risk-version flag |

---

## 2. API Implementada

### `RiskManagerV06.assess(order_intent, nav, default_weight, ctx) -> RiskDecisionV1`

```python
rm = RiskManagerV06("configs/risk_rules.yaml")
decision = rm.assess(order_intent, nav=10000.0, default_weight=0.10)
```

**Flujo interno:**

1. Valida `OrderIntentV1.validate()` → si falla, retorna decision rechazada
2. Convierte a dict via `adapt_order_intent_to_risk_input()`
3. Delega a `RiskManager v0.4.filter_signal()`
4. Normaliza razones a `list[str]`
5. Retorna `RiskDecisionV1`

**Normalización de razones:**

- `list[str]` → as-is
- `str` → `[str]`
- `dict` → `["key:value", ...]` sorted
- `None` → `[]`

---

## 3. Runner Wiring

### `--risk-version` flag

```bash
python tools/run_live_integration_3B.py --data data.csv --out out.ndjson --risk-version v0.6
```

| Valor | Comportamiento |
|-------|----------------|
| `v0.4` (default) | Usa shim inline existente |
| `v0.6` | Convierte OrderIntent→OrderIntentV1, usa assess(), output RiskDecisionV1 |

---

## 4. Tests

| Suite | Tests | Descripción |
|-------|-------|-------------|
| test_risk_manager_v0_6_contract.py | 11 | Verifica tipos, propagación IDs, serialización |
| test_risk_manager_v0_6_compat_v0_4_parity.py | 6 | Paridad allowed/reasons con v0.4 |

**pytest total:** 272 passed, 7 skipped

---

## 5. Commit

```
b611d44 3C.3: add risk_manager v0.6 event-native + parity tests
```

---

## 6. Artefactos

- [AG-3C-3-1_pytest.txt](AG-3C-3-1_pytest.txt)
- [AG-3C-3-1_diff.patch](AG-3C-3-1_diff.patch)
- [AG-3C-3-1_last_commit.txt](AG-3C-3-1_last_commit.txt)
