# AG-2E-3-3-gate-semantics: Corrección Semántica Activity Gate

**Branch**: `feature/2E_gate_semantics_fix`  
**Timestamp**: 2025-12-28T15:55  
**Estado**: Recuperado tras terminación de agente

---

## Recuperación

El agente anterior completó la implementación pero fue terminado antes de commit/push.

**Estado encontrado**:
- Cambios en `tools/run_calibration_2B.py` y tests staged (git add hecho)
- Artefactos de smoke tests en `report/out_2E_3_3_*` generados
- Sin commit realizado

**Acciones de recuperación**:
1. Verificado que la rama era `feature/2E_gate_semantics_fix` ✓
2. Re-ejecutado pytest: 121 passed ✓
3. Re-ejecutado smoke tests para confirmar comportamiento ✓
4. Commit + push + PR (este paso)

---

## Problema Original

La lógica anterior de `evaluate_gates` usaba:
```python
if active_n < min_active_n AND active_rate < min_active_rate:
    insufficient_activity = True
```

Esto significaba que el gate pasaba si **cualquiera** de los thresholds se cumplía, cuando debería fallar si **cualquiera** falla.

---

## Solución

Nueva lógica evalúa **cada threshold independientemente**:

```python
if min_active_n is not None and active_n < min_active_n:
    gate_fail_reasons.append("active_n_below_min")
    insufficient_activity = True

if min_active_rate is not None and active_rate < min_active_rate:
    gate_fail_reasons.append("active_rate_below_min")
    insufficient_activity = True

if max_inactive_rate is not None and inactive_rate > max_inactive_rate:
    gate_fail_reasons.append("inactive_rate_above_max")
    insufficient_activity = True

if min_active_pass_rate is not None and active_pass_rate < min_active_pass_rate:
    gate_fail_reasons.append("active_pass_rate_below_min")
```

---

## Cambios

| Archivo | Cambio |
|---------|--------|
| `tools/run_calibration_2B.py` | Corregida función `evaluate_gates` (líneas 265-291) |
| `tests/test_calibration_runner_2B.py` | +3 tests nuevos para gate semantics |

### Tests añadidos
- `test_gate_fail_active_rate_below_min` — verifica fallo por active_rate
- `test_gate_granular_fail_reasons` — verifica razones válidas
- `test_strict_gate_exit_code_on_fail` — verifica exit 1 con --strict-gate

---

## Verificación (2025-12-28T15:55)

| Check | Resultado |
|-------|-----------|
| pytest | 121 passed ✓ |
| full smoke (40) | FAIL: active_n_below_min, active_rate_below_min, inactive_rate_above_max ✓ |
| full --strict-gate | exit code 1 ✓ |

### run_meta.json verificado

```json
{
  "gate_passed": false,
  "insufficient_activity": true,
  "gate_fail_reasons": [
    "active_n_below_min",
    "active_rate_below_min",
    "inactive_rate_above_max"
  ],
  "active_n": 13,
  "active_rate": 0.325,
  "inactive_rate": 0.675
}
```

Con thresholds del YAML:
- `min_active_n: 20` → 13 < 20 ❌
- `min_active_rate: 0.60` → 0.325 < 0.60 ❌
- `max_inactive_rate: 0.40` → 0.675 > 0.40 ❌

---

## Artefactos

- `report/AG-2E-3-3-gate-semantics_return.md` (este archivo)
- `report/AG-2E-3-3-gate-semantics_pytest.txt`
- `report/AG-2E-3-3-gate-semantics_run.txt`
- `report/AG-2E-3-3-gate-semantics_diff.patch`
- `report/AG-2E-3-3-gate-semantics_last_commit.txt`
- `report/out_2E_3_3_full_smoke/`
- `report/out_2E_3_3_full_strict_smoke/`

---

## Commit

```
<<<<<<< HEAD
21f102d 2E: enforce activity gate thresholds + granular fail reasons
=======
3992d50 2E: enforce activity gate thresholds + granular fail reasons
>>>>>>> 21f102d (2E: enforce activity gate thresholds + granular fail reasons)
```

## PR

**Requiere login manual en GitHub**

Crear PR aquí: https://github.com/evon93/invest-bot-suite/compare/main...feature/2E_gate_semantics_fix

Título sugerido: `2E: enforce activity gate thresholds + granular fail reasons`
