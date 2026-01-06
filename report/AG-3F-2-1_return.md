# AG-3F-2-1: Retry/Backoff + Idempotency — Return Packet

**Ticket**: AG-3F-2-1  
**Rama**: `feature/3F_2_retry_idempotency`  
**Fecha**: 2026-01-06

---

## Resumen de Cambios

Implementación de retry/backoff determinista e idempotencia para el camino de ejecución en `ExecWorker`.

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| [engine/retry_policy.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/retry_policy.py) | `RetryPolicy` con backoff exponencial + jitter hash determinista |
| [engine/idempotency.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/idempotency.py) | `InMemoryIdempotencyStore` con TTL + `now_fn` inyectable |
| [tests/test_retry_policy_3F2.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_retry_policy_3F2.py) | 10 tests para RetryPolicy |
| [tests/test_idempotency_3F2.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_idempotency_3F2.py) | 9 tests para IdempotencyStore |
| [tests/test_retry_idempotency_integration_3F2.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_retry_idempotency_integration_3F2.py) | 5 tests de integración con FlakyAdapter |

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| [engine/bus_workers.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/bus_workers.py) | Integración de retry + idempotency en `ExecWorker._process_one()` |

---

## **Punto Real de Ejecución**

- **Archivo**: `engine/bus_workers.py`
- **Línea**: ~277 (ahora ~290 tras cambios)
- **Función**: `ExecWorker._process_one()`
- **Llamada**: `self._adapter.submit(...)`

---

## Política de Retry

```python
RetryPolicy(
    max_attempts=3,        # Máximo intentos
    base_delay_ms=100,     # Delay base
    max_delay_ms=5000,     # Cap máximo
    multiplier=2.0,        # Exponential backoff
    jitter_mode="hash"     # Determinista via sha256
)
```

**Generación de op_key**:

```python
op_key = f"exec:{decision.ref_order_event_id}"
```

- `ref_order_event_id` ya es UUID determinista generado por `_gen_uuid()`

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_retry_policy_3F2.py tests/test_idempotency_3F2.py -v` | 19 passed |
| `pytest tests/test_retry_idempotency_integration_3F2.py -v` | 5 passed |
| `pytest -q` | **410 passed**, 7 skipped |

---

## DoD Verificado

- [x] `pytest -q` PASS (410 passed, +24 nuevos)
- [x] Retry policy determinista (jitter via hash, sleep inyectable)
- [x] Duplicados bloqueados (idempotency key estable)
- [x] No deps nuevas
- [x] No sleeps reales en tests

---

## Artefactos Generados

- `report/pytest_3F2_retry_idempotency.txt`
- `report/pytest_3F2_integration.txt`
- `report/AG-3F-2-1_pytest.txt`
- `report/AG-3F-2-1_diff.patch`
- `report/AG-3F-2-1_return.md` (este archivo)
