# AG-3D-3-1 Return Packet

## Resumen

Implementados bridge adapters para conectar LoopStepper con el bus in-memory.

**Commit**: `47876c9` — "3D.3: bridge adapters direct->bus + stepper bus mode"

## Discovery

| Componente | Path |
|------------|------|
| LoopStepper | `engine/loop_stepper.py` |
| PositionStoreSQLite | `state/position_store_sqlite.py` |
| Events V1 | `contracts/events_v1.py` |
| Bus | `bus/inmemory_bus.py` |

## Archivos Creados/Modificados

| Tipo | Archivo | Descripción |
|------|---------|-------------|
| [NEW] | `engine/bus_workers.py` | RiskWorker, ExecWorker, PositionStoreWorker, DrainWorker |
| [MODIFY] | `engine/loop_stepper.py` | Añadido `run_bus_mode()` |
| [NEW] | `tests/test_stepper_bus_mode_3D.py` | 8 tests |

## Diseño

### Topics

| Topic | Productor | Consumidor |
|-------|-----------|------------|
| `order_intent` | LoopStepper | RiskWorker |
| `risk_decision` | RiskWorker | ExecWorker |
| `execution_report` | ExecWorker | PositionStoreWorker |

### Workers

```
OrderIntent → [RiskWorker] → RiskDecision → [ExecWorker] → ExecutionReport → [PositionStoreWorker] → SQLite
```

- **RiskWorker**: Consume OrderIntentV1, evalúa con RiskManager v0.4, produce RiskDecisionV1
- **ExecWorker**: Consume RiskDecisionV1 (si allowed), simula fill, produce ExecutionReportV1
- **PositionStoreWorker**: Consume ExecutionReportV1, aplica fill a SQLite
- **DrainWorker**: Drena topic cuando no hay consumidor (previene deadlock)

### Bus Mode Flow

1. LoopStepper publica todos los OrderIntentV1 al bus
2. Loop drena colas iterativamente hasta vacío (max 100 iteraciones)
3. Detección de deadlock: si no hay progreso pero hay mensajes pendientes

## Invariantes Verificadas

| Invariante | Verificado en |
|------------|---------------|
| No deadlock | `test_bus_mode_terminates_no_deadlock` |
| No double consume | `test_each_intent_processed_once` |
| trace_id propagado | `test_trace_id_preserved_in_all_events` |
| SQLite actualizado | `test_sqlite_updated_with_fills` |

## Bug Corregido

`ExecWorker.__init__` usaba `intent_cache or {}` que fallaba con dict vacío (falsy). Cambiado a `intent_cache if intent_cache is not None else {}`.

## Tests

| Test | Resultado |
|------|-----------|
| `tests/test_stepper_bus_mode_3D.py` | 8 passed |
| Suite completa | 349 passed, 7 skipped |

## Evidencias

- `report/pytest_3D3_stepper_bus.txt`
- `report/AG-3D-3-1_pytest.txt`
- `report/AG-3D-3-1_diff.patch`
- `report/AG-3D-3-1_last_commit.txt`
