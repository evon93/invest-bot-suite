# AG-3D-4-1 Return Packet

## Resumen

Implementado JSONL trace logging + cache-miss fail-fast en ExecWorker.

**Commit**: `e120a20` — "3D.4: jsonl trace logging + cache-miss fail-fast + tests"

## Archivos Creados/Modificados

| Tipo | Archivo | Descripción |
|------|---------|-------------|
| [NEW] | `engine/structured_jsonl_logger.py` | Logger JSONL sin timestamps |
| [MOD] | `engine/loop_stepper.py` | Wire logging en `run_bus_mode()` |
| [MOD] | `engine/bus_workers.py` | ExecWorker cache-miss fail-fast |
| [NEW] | `tests/test_trace_id_propagation.py` | 2 tests propagación trace_id |
| [NEW] | `tests/test_exec_worker_cache_miss.py` | 5 tests cache-miss |
| [NEW] | `tools/generate_sample_jsonl_3D4.py` | Script para generar sample |

## Cambios Clave

### 1. Logger JSONL Estructurado

```python
log_event(
    logger,
    trace_id="...",
    event_type="OrderIntentV1",
    step_id=10,
    action="publish",
    topic="order_intent",
    extra={...},
)
```

- **Sin timestamps** (determinístico)
- Cada línea tiene: `trace_id`, `event_type`, `step_id`, `action`
- Output en `report/3D4_logs_sample.jsonl`

### 2. ExecWorker Cache-Miss Fail-Fast

**Antes**: Defaults peligrosos (`qty=1.0`, `price=100.0`)  
**Después**: `ValueError` explícito con trace_id + ref_order_event_id

Orden de validación optimizado:

1. symbol (REQUIRED)
2. side (BUY/SELL)
3. qty (> 0)
4. price (limit_price → notional/qty → meta.bar_close)

### 3. Bar Close en Intent Cache

LoopStepper ahora añade `meta.bar_close` al cachear intents para que ExecWorker tenga precio válido.

## Tests

| Test File | Passed |
|-----------|--------|
| `test_trace_id_propagation.py` | 2 |
| `test_exec_worker_cache_miss.py` | 5 |
| **Suite completa** | 356 |

## Evidencias

- `report/pytest_3D4_trace.txt`
- `report/pytest_3D4_cache_miss.txt`
- `report/pytest_3D4_full.txt`
- `report/3D4_logs_sample.jsonl`
- `report/AG-3D-4-1_diff.patch`
- `report/AG-3D-4-1_last_commit.txt`

## Sample JSONL (sin timestamps)

```json
{"action":"publish","event_type":"OrderIntentV1","extra":{"event_id":"bdd640fb-...","symbol":"BTC-USD"},"step_id":2,"topic":"order_intent","trace_id":"23b8c1e9-..."}
{"action":"complete","event_type":"BusModeDone","extra":{"drain_iterations":1,"published":1},"step_id":10,"trace_id":"SYSTEM"}
```
