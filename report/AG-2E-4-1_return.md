# AG-2E-4-1: Instrumentación de Razones de Inactividad

**Branch**: `feature/2E_inactive_instrumentation`  
**Timestamp**: 2025-12-28T17:48

---

## Cambios

Instrumentación completa para diagnosticar por qué un combo no opera (num_trades=0).

| Componente | Cambio |
|------------|--------|
| `backtest_initial.py` | Añadido `self.diagnostics` con contadores: `signal_count`, `signal_rejected_count` (risk), `price_missing_count`. |
| `tools/run_calibration_2B.py` | Nueva función `classify_inactive_reason()` que usa los diagnósticos para setear flags `rejection_*`. |
| `tests/test_calibration_runner_2B.py` | Añadidos tests unitarios para clasificación y test de integridad de columnas. |

### Lógica de Clasificación (Prioridad)

1. `price_missing` (datos sucios)
2. `no_signal` (nunca se intentó rebalancear)
3. `blocked_risk` (intentos rechazados por RiskManager)
4. `size_zero` (intentos aceptados pero tamaño 0, requiere soporte futuro)
5. `other` (fallback)

---

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest | 126 passed ✓ |
| Full Demo Smoke | `rejection_blocked_risk` identificada correctamente en 27 escenarios inactivos (antes "other") ✓ |
| CSV Output | Filas inactivas tienen flags correctos (ej: `0,1,0,0,0` para blocked risk) ✓ |

### run_meta.json (Full Demo)

```json
{
  "gate_profile": "full_demo",
  "gate_passed": true,
  "rejection_reasons_agg": {
    "rejection_no_signal": 0,
    "rejection_blocked_risk": 27,
    "rejection_size_zero": 0,
    "rejection_price_missing": 0,
    "rejection_other": 0
  },
  "top_inactive_reasons": ["rejection_blocked_risk"]
}
```

---

## Artefactos

- `report/AG-2E-4-1_return.md`
- `report/AG-2E-4-1_diff.patch`
- `report/AG-2E-4-1_run.txt`
- `report/AG-2E-4-1_pytest.txt`
- `report/AG-2E-4-1_last_commit.txt`

## Commit

```
12f8e03 2E: instrument inactive reasons for calibration combos
```
