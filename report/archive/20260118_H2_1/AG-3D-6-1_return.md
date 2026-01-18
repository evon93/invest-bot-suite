# AG-3D-6-1 Return Packet

## Resumen

Consolidado el runner canónico para 3D (CI-safe) con determinismo y test de coherencia (smoke test).

**Commit**: `edf0f45` — "3D.6: canonical runner + smoke test"

## Componentes Entregados

### 1. Canonical Runner (`tools/run_3D_canonical.py`)

- **CLI**: `--outdir`, `--seed`, `--max-steps`, `--risk-rules`, `--strict-risk-config`, `--num-signals`.
- **Salida**: Genera `trace.jsonl`, `run_metrics.json`, `run_meta.json`.
- **Determinismo**: Control de seed para OHLCV sintético y UUIDs. Sin timestamps en logs.
- **Fail-fast**: Exit code > 0 si configuración de riesgo falla (con `--strict-risk-config`).

### 2. Smoke Test (`tests/test_3D_canonical_smoke.py`)

- Verifica ejecución exitosa del runner (subprocess).
- Valida existencia de artefactos.
- **Coherencia**: Comprueba que `intents == risk_decisions` y `allowed == reports == fills`.
- **Audit**: Escanea logs y meta para asegurar ausencia de timestamps (requisito CI determinista).

## Evidencias

- `report/out_3D6_canon/run_metrics.json`:

```json
{
  "drain_iterations": 1,
  "max_step_id": 50,
  "num_execution_reports": 11,
  "num_fills": 11,
  "num_order_intents": 11,
  "num_risk_allowed": 11,
  "num_risk_decisions_total": 11,
  "unique_trace_ids": 11
}
```

- `report/pytest_3D6_smoke.txt`: 2 passed (smoke test + strict mode check).
- `report/pytest_3D6_full.txt`: 360 passed (suite completa).

## Archivos

- `report/out_3D6_canon/*` (trace, meta, metrics, db)
- `report/AG-3D-6-1_last_commit.txt`
