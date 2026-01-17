# ORCH_HANDOFF Post-H1 Close — 2026-01-17

## Estado del Repositorio

- **Branch**: main
- **HEAD**: f96d88b (H1.4 merged)
- **Fecha**: 2026-01-17
- **Pytest**: 747 passed, 11 skipped, 7 warnings

---

## Resumen Ejecutivo H1

La fase H1 establece las bases de **operabilidad y observabilidad** post-3O:

1. **Artifact Storage Policy** — Control de bloat en `report/`
2. **Exit Code Semantics** — Semántica clara para CI (0 = shutdown controlado)
3. **Adapter SIGTERM Tests** — Validación de checkpoint en señales
4. **CI Gate H1** — Workflow que gatee todos los cambios H1

---

## Cambios por Ticket

### H1.1: Artifact Storage Policy (581472f)

- **`.gitignore`**: Corregido para trackear `*_return.md`, `*_last_commit.txt`, `ORCH_HANDOFF_*.md`
- **`tools/report_artifact_policy.py`**: Herramienta de validación (~190 líneas)
- **`docs/policy_report_artifacts.md`**: Documentación de policy
- **`tests/test_report_policy_h1_1.py`**: 7 tests

### H1.2: Exit Code Semantics (44bd161)

- **`tools/run_live_3E.py`**: Exit code explícito (0=success/shutdown, 2=error)
- **`tests/test_exit_codes_h1.py`**: 5 tests (failure + shutdown)

### H1.3: Adapter SIGTERM Checkpoint (ed5c602)

- **`tests/test_adapter_sigterm_checkpoint_h1.py`**: 2 tests (SIGTERM + SIGINT en adapter-mode)
- Verificación de `checkpoint.json` tras señal

### H1.4: CI Gate (f96d88b)

- **`.github/workflows/h1_gate.yml`**: Workflow CI
  - Policy check: `python tools/report_artifact_policy.py --check`
  - Tests H1: exit_codes, adapter_sigterm, report_policy
  - Artifact upload: `report/AG-H1-*`

---

## CI / Workflows

| Workflow | Propósito | Estado |
|----------|-----------|--------|
| `h1_gate.yml` | Gate H1: policy + tests | ✅ Nuevo |
| `graceful_shutdown_3O.yml` | Tests shutdown directo/supervisor | Existente |

**Nota**: Todos los workflows son offline (`INVESTBOT_ALLOW_NETWORK=0`).

---

## Invariantes Respetadas

- ✅ **Determinismo**: seed42 en todos los tests
- ✅ **Offline**: Sin dependencias de red
- ✅ **Trazabilidad**: Return packets + handoffs trackados en git
- ✅ **Backward compatible**: Tests 3O2 siguen pasando

---

## Known Issues / Warnings

- 7 deprecation warnings de pandas (`is_datetime64tz_dtype`)
- ~200 archivos untracked en `report/` (return packets históricos no commiteados)

---

## Recomendaciones para H2

1. **Artifact cleanup**: Considerar commit batch de return packets históricos o cleanup
2. **Exit codes supervisor**: Extender validación en `supervisor_live_3E_3H.py`
3. **CI consolidation**: Evaluar unificar workflows H1 con other gates
4. **Pandas deprecation**: Migrar a `isinstance(dtype, pd.DatetimeTZDtype)`
