# AG-3D-5-1 Return Packet

## Resumen

Implementada recolección de métricas deterministas desde logs JSONL y script demo.

**Commit**: `a6c10e5` — "3D.5: deterministic run metrics + tests"

## Componentes

### 1. Engine & Logging

- [MOD] `engine/bus_workers.py`: Inyección de `jsonl_logger` y logging de eventos (Risk, Exec, Pos).
- [MOD] `engine/loop_stepper.py`: Paso de logger a workers.
- [NEW] `engine/run_metrics_3D5.py`: `collect_metrics_from_jsonl()` parsea logs sin timestamps.

### 2. Demo & Tools

- [NEW] `tools/run_metrics_3D5_demo.py`:
  - Ejecuta simulación bus mode con logging.
  - Genera `trace.jsonl` y `run_metrics.json`.
  - Muestra métricas en consola.

### 3. Tests

- [NEW] `tests/test_run_metrics_3D5.py`:
  - Verifica conteos exactos desde sample log.
  - Verifica determinismo de JSON output (sorted keys).

## Workflow de Métricas

1. `LoopStepper` genera eventos → JSONL con `structured_jsonl_logger`.
2. `collect_metrics_from_jsonl` lee JSONL line-by-line.
3. Acumula contadores por `{event_type, action}`.
4. Genera dict de métricas (sin timestamps).

## Evidencias

- `report/out_3D5_metrics/run_metrics.json`:

```json
{
  "drain_iterations": 1,
  "max_step_id": 20,
  "num_execution_reports": 3,
  "num_fills": 3,
  "num_order_intents": 3,
  "num_positions_updated": 3,
  "num_risk_allowed": 3,
  "num_risk_decisions_total": 3,
  "num_risk_rejected": 0,
  "unique_trace_ids": 3
}
```

- `report/pytest_3D5_metrics.txt`: 2 passed (tests métricas).
- `report/pytest_3D5_full.txt`: 358 passed (suite completa).

## Archivos Entregados

- `report/out_3D5_metrics/trace.jsonl`
- `report/out_3D5_metrics/run_metrics.json`
- `report/AG-3D-5-1_last_commit.txt`
