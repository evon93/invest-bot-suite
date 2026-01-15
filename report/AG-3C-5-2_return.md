# AG-3C-5-2 Return Packet — DS Hardening (LoopStepper/Runner)

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-5-2 (WSL + venv)  
**Rama:** `feature/3C_5_2_ds_hardening`  
**Estado:** ✅ COMPLETADO

---

## 1. Cambios Implementados

### `engine/loop_stepper.py`

- **Determinismo IDs:** Usa `random.Random(seed)` interno para generar UUIDs deterministas para `OrderIntent`, `RiskDecisionV1`, `ExecutionReportV1`.
- **Determinismo TS:** Usa timestamp de cierre de barra (`close time`) para todos los eventos de esa barra, asegurando reproducibilidad.
- **Trace Chain:** Sobreescribe `intent.trace_id` y propaga explícitamente a `RiskDecisionV1` y `ExecutionReportV1`.
- **Contratos V1 Canónicos:** Siempre emite `RiskDecisionV1` (incluso con motor v0.4) y `ExecutionReportV1`.
- **Observabilidad:** Inyecta metadatos (`step_idx`, `bar_ts`, `engine_version`, `risk_version`) en `OrderIntent.meta`, `RiskDecisionV1.extra` y `ExecutionReportV1.extra`.

### `tools/run_live_integration_3C.py`

- **JSON Determinista:** Usa `json.dumps(..., sort_keys=True, separators=(',', ':'))` para generar `events.ndjson` y `run_meta.json` sin ambigüedades.

### Tests (`tests/test_live_loop_stepper_3C_smoke.py`)

- **`TestDeterminism`:** Verifica hash SHA256 idéntico para dos ejecuciones con mismo seed.
- **`TestTraceChain`:** Verifica propagación de `trace_id` a lo largo de la cadena Order->Risk->Execution.
- **`TestCanonicalRiskDecision`:** Verifica que siempre se emite `RiskDecisionV1`.
- **`TestObservability`:** Verifica presencia de campos `step_idx`, `engine_version`, etc.
- **`TestDeterministicJsonFile`:** Verifica `sort_keys=True` en output (sin espacios extra).

---

## 2. Verificación

| Verificación | Resultado |
|--------------|-----------|
| `pytest -q` | 11 passed (100%) ✅ |
| Runner Manual | Exit code 0 (lógico), events generados, hash estable. |
| Trace Propagation | OK |
| Determinismo Seed | OK (Hash events.ndjson idéntico) |

---

## 3. Commit

```
07dedb3 3C.5.2: DS hardening (deterministic JSON, trace chain, canonical RiskDecisionV1, observability, tests)
```

---

## 4. Artefactos

- [AG-3C-5-2_pytest.txt](AG-3C-5-2_pytest.txt)
- [AG-3C-5-2_run.txt](AG-3C-5-2_run.txt)
- [AG-3C-5-2_diff.patch](AG-3C-5-2_diff.patch)
- [AG-3C-5-2_last_commit.txt](AG-3C-5-2_last_commit.txt)
