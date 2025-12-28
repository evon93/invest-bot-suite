# Modo Monitor vs Active — RiskManager v0.5

**Branch:** `feature/2A_riskcontext_v0_6_and_monitor`  
**Fecha:** 2025-12-16

---

## Semántica

| Aspecto | `mode=active` | `mode=monitor` |
|---------|--------------|----------------|
| Bloquea señales | ✅ Sí | ❌ No |
| Capea deltas (Kelly) | ✅ Sí | ❌ No |
| Fuerza cierre (DD hard) | ✅ Sí | ❌ No |
| Registra "would_*" | ❌ No | ✅ Sí |
| `risk_allow` final | Calculado | Siempre `True` |
| `risk_reasons` final | Calculado | Siempre `[]` |

---

## Configuración

```yaml
# risk_rules.yaml
risk_manager:
  mode: monitor  # o "active" (default)
```

---

## Campos en annotated (modo monitor)

```python
annotated["risk_monitor"] = {
    "would_allow": bool,          # Lo que habría devuelto en active
    "would_reasons": list[str],   # Motivos que habrían bloqueado
    "would_decision": dict,       # risk_decision completo calculado
    "would_deltas": dict,         # Deltas capados por Kelly (si aplica)
}

annotated["risk_allow"] = True           # Siempre True en monitor
annotated["risk_reasons"] = []           # Siempre vacío en monitor
annotated["risk_decision"]["mode"] = "monitor"
```

---

## Flujo en filter_signal

1. Se calculan **todos los guardrails** normalmente (DD, ATR, Kelly, límites)
2. Se acumulan decisiones en `risk_decision` y mutaciones en `annotated["deltas"]`
3. **Si mode=monitor:**
   - Guardar snapshot `would_*` en `risk_monitor`
   - Reset: `allow=True`, `reasons=[]`, `annotated=signal_original.copy()`
   - Restaurar `deltas` originales
   - Resetear `risk_decision` a defaults
4. Escribir campos finales en annotated

---

## Bugfix: Shallow Copy de Deltas (2A/3.4)

**Problema:** Al restaurar `annotated = signal_original.copy()`, los deltas seguían mutados porque `signal.copy()` es shallow y el dict interno de deltas se compartía.

**Solución:** Guardar snapshot deep copy al inicio:

```python
orig_deltas = dict(signal.get("deltas", {}))

# (después de calcular todo)
if mode == "monitor":
    annotated["deltas"] = dict(orig_deltas)  # Restaura originales
```

**Test:** `tests/test_risk_mode_monitor_v0_5.py::test_monitor_does_not_apply_kelly_capping_but_records_would_deltas`

---

## Tests relevantes

- [`tests/test_risk_mode_monitor_v0_5.py`](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_risk_mode_monitor_v0_5.py) (2 tests)
  - `test_monitor_records_would_block_but_applies_noop`
  - `test_monitor_does_not_apply_kelly_capping_but_records_would_deltas`

**Snapshots:**
- `report/pytest_2A_3.4_monitor_tests_after_fix.txt` (2 passed)
