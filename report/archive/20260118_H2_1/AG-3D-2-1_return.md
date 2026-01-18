# AG-3D-2-1 Return Packet

## Resumen

Implementado bus abstraction in-memory determinista para eventos V1.

**Commit**: `43e6e01` — "3D.2: in-memory bus abstraction + tests"

## Diseño

### Seq: Global vs Per-Topic

**Decisión**: `seq` global monotónico (no per-topic).

**Razón**: Permite total ordering de eventos entre topics. Un consumidor puede reconstruir el orden exacto de todos los eventos en el sistema, útil para replay y debugging.

### Sin Timestamps

- No se incluyen timestamps en el envelope
- Garantiza determinismo para CI/testing
- Los componentes que necesiten tiempo lo obtienen externamente

## Archivos Creados

| Archivo | Descripción |
|---------|-------------|
| `bus/__init__.py` | Exports del módulo |
| `bus/bus_base.py` | `BusEnvelope` (dataclass frozen) + `BusBase` (Protocol) |
| `bus/inmemory_bus.py` | `InMemoryBus` con FIFO per-topic, seq global |
| `tests/test_inmemory_bus_roundtrip.py` | 17 tests |

## API

```python
from bus import InMemoryBus, BusEnvelope

bus = InMemoryBus()

# Publish
env = bus.publish(
    topic="order_intent",
    event_type="OrderIntentV1",
    trace_id="T-0001",
    payload={"qty": 10, "side": "buy"},
)

# Poll (FIFO, removes from queue)
events = bus.poll("order_intent", max_items=1)

# Size
pending = bus.size("order_intent")
```

## Tests

| Archivo | Resultado |
|---------|-----------|
| `tests/test_inmemory_bus_roundtrip.py` | 17 passed |
| Suite completa | 341 passed, 7 skipped |

## Notas de Determinismo

| Aspecto | Implementación |
|---------|----------------|
| Timestamps | No incluidos en envelope |
| Random | No usado |
| Seq ordering | Global monotónico, predecible |
| FIFO | Determinista via deque |

## Evidencias

- `report/pytest_3D2_bus.txt`
- `report/AG-3D-2-1_diff.patch`
- `report/AG-3D-2-1_pytest.txt`
- `report/AG-3D-2-1_last_commit.txt`
