# AG-3F-3-1: Real-ish Adapter Gated — Return Packet

**Ticket**: AG-3F-3-1  
**Rama**: `feature/3F_3_realish_adapter_gated`  
**Fecha**: 2026-01-07

---

## Resumen de Cambios

Implementación de `SimulatedRealtimeAdapter` que simula condiciones de exchange reales (latencias, fallos transitorios) de forma determinista y sin requerir secrets.

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| [engine/exchange_adapter.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/exchange_adapter.py) | +`SimulatedRealtimeAdapter`, +`TransientNetworkError` |
| [engine/runtime_config.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/runtime_config.py) | `realish` no requiere secrets |
| [engine/bus_workers.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/bus_workers.py) | `TransientNetworkError` en lista retryable |
| [tools/run_live_3E.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_live_3E.py) | +`--exchange realish` option |

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| [tests/test_realish_adapter_gating_3F3.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_realish_adapter_gating_3F3.py) | 9 tests de gating (siempre pasan) |
| [tests/test_realish_adapter_integration_3F3.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_realish_adapter_integration_3F3.py) | 3 tests integration (SKIP sin env var) |

---

## Dónde se Enchufa el Adapter

1. **CLI**: `tools/run_live_3E.py --exchange realish`
2. **Env var**: `INVESTBOT_EXCHANGE_KIND=realish`
3. **Pipeline**: `LoopStepper.run_bus_mode()` → `ExecWorker` → `adapter.submit()`

---

## Activation Flags

| Flag | Comportamiento |
|------|----------------|
| `--exchange paper` | PaperExchangeAdapter (default, determinista) |
| `--exchange stub` | StubNetworkExchangeAdapter (latencia simulada) |
| `--exchange realish` | SimulatedRealtimeAdapter (fallos + latencia) |

---

## Tests SKIP Conditions

| Test | Condición SKIP |
|------|----------------|
| `test_realish_full_pipeline_with_bus` | Sin `INVESTBOT_TEST_INTEGRATION=1` |
| `test_realish_with_idempotency` | Sin `INVESTBOT_TEST_INTEGRATION=1` |
| `test_skip_message` | Sin `INVESTBOT_TEST_INTEGRATION=1` |

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_realish_adapter_gating_3F3.py tests/test_realish_adapter_integration_3F3.py -v` | 9 passed, 3 skipped |
| `pytest -q` | **419 passed**, 10 skipped |

---

## DoD Verificado

- [x] `pytest -q` PASS sin network ni secrets
- [x] Gating tests PASS (9/9)
- [x] Integration tests SKIP sin env var (3 skipped)
- [x] Adapter integrado con retry/idempotency (TransientNetworkError retryable)

---

## Artefactos Generados

- `report/pytest_3F3_gating.txt`
- `report/AG-3F-3-1_pytest.txt`
- `report/AG-3F-3-1_diff.patch`
- `report/AG-3F-3-1_return.md` (este archivo)
