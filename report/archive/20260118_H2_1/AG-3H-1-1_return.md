# AG-3H-1-1 Return Packet

## Objetivo

Implementar observability granular per-message/per-step en el loop con:

- Latencias por etapa: strategy, risk, exec, position
- Contadores por tipo de evento + outcomes
- Etiquetado con run_id + step_id + trace_id
- Determinismo con --seed 42 --clock simulated

## Baseline

- **Branch**: main
- **HEAD antes**: ac0ffc9
- **Fecha**: 2026-01-10

## Diseño Tiempo/Determinismo

**Clock determinista**: `time_provider.now_ns() / 1e9` en modo simulated.
En este modo, el time_provider está fijo y las latencias son 0.0 (ya que no avanza automáticamente).

**Campos por stage event**:

- `stage`: nombre de la etapa (strategy, risk, exec, position)
- `step_id`: contador monotónico por run
- `trace_id`: trace_id del mensaje o synthetic para batches
- `t_start`, `t_end`, `dt`: tiempos deterministas
- `outcome`: ok | rejected | error
- `reason`: opcional para rejected/error

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `engine/metrics_collector.py` | +`record_stage()`, +`get_stage_events()`, +`_stage_events/latencies/outcomes`, snapshot_summary ampliado |
| `engine/loop_stepper.py` | +parámetro `metrics_collector` en run_bus_mode(), instrumentación por stage |
| `tools/run_live_3E.py` | wiring de metrics_collector al stepper, escritura de stage events |
| `tests/test_loop_stepper_metrics_granular.py` | [NEW] 8 tests: files, stages, determinism, noop, record_stage |

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest -q | **PASS** (490 passed, 10 skipped) |
| tests granulares | **8/8 PASS** |
| smoke local | **OK** (3 intents, 6 stage events) |

## Artefactos Smoke (report/out_3H1_smoke/)

- `metrics.ndjson`: 6 líneas (3 strategy + 1 risk + 1 exec + 1 position)
- `metrics_summary.json`: incluye stages_by_name, outcomes_by_stage, stage_events_count

**Ejemplo metrics_summary.json (extracto)**:

```json
{
  "stages_by_name": {
    "strategy": {"count": 3, "p50_ms": 0.0, "p95_ms": 0.0},
    "risk": {"count": 1, "p50_ms": 0.0, "p95_ms": 0.0},
    "exec": {"count": 1, "p50_ms": 0.0, "p95_ms": 0.0},
    "position": {"count": 1, "p50_ms": 0.0, "p95_ms": 0.0}
  },
  "outcomes_by_stage": {
    "strategy": {"ok": 3},
    "risk": {"ok": 1},
    "exec": {"ok": 1},
    "position": {"ok": 1}
  },
  "stage_events_count": 6
}
```

## DOD Status: **PASS**

- [x] pytest -q PASS
- [x] smoke local genera métricas granulares
- [x] determinismo garantizado por test
- [x] no cambios fuera de scope

## Próximos pasos (3H.2+)

- 3H.2: Rotación/compactación de métricas
- 3H.3: Dashboard
- 3H.4: Supervisor
