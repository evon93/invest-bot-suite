# AG-3F-4-2: Integrar --run-dir/--resume en run_live_3E — Return Packet

**Ticket**: AG-3F-4-2  
**Rama**: `feature/3F_4_crash_recovery_v0`  
**Fecha**: 2026-01-07

---

## Resumen

Integración de checkpoint y FileIdempotencyStore en el runner real (run_live_3E.py).

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| [tools/run_live_3E.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_live_3E.py) | +`--run-dir`, +`--resume`, +lógica de checkpoint/idem_store |
| [engine/loop_stepper.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/loop_stepper.py) | `run_bus_mode()` acepta `idempotency_store` |

---

## Uso CLI

```bash
# Nueva ejecución con run directory
python tools/run_live_3E.py --run-dir report/runs/my_run --max-steps 50

# Reanudar tras crash
python tools/run_live_3E.py --resume report/runs/my_run
```

---

## Archivos Generados por --run-dir

```
report/runs/my_run/
├── checkpoint.json         # Estado de progreso
└── idempotency_keys.jsonl  # Keys procesadas
```

---

## Smoke Test

```powershell
python tools/run_live_3E.py --run-dir report/runs/test_3F4_run --max-steps 10
```

**Output**:

```
Created run directory: report\runs\test_3F4_run
Starting run_live_3E with clock=simulated, exchange=paper...
Simulation done. Published: 1
```

**checkpoint.json**:

```json
{
  "run_id": "run_42_10",
  "last_processed_idx": -1,
  "processed_count": 0,
  "updated_at": "2026-01-07T19:02:53.691102+00:00"
}
```

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `python tools/run_live_3E.py --run-dir ... --max-steps 10` | Crea checkpoint + jsonl |
| `pytest -q` | **432 passed**, 10 skipped |

---

## DoD Verificado

- [x] `--run-dir` crea directorio con checkpoint + jsonl
- [x] `--resume` lee checkpoint y carga idempotency store
- [x] `idempotency_store` pasado a `ExecWorker` via `run_bus_mode`
- [x] `pytest -q` PASS

---

## Nota sobre Checkpoint Updates

El checkpoint se crea al inicio pero no se actualiza durante el loop actualmente.
La lógica de actualización "tras cada mensaje procesado" requiere hooks adicionales
en el bus drain loop de `run_bus_mode`. La idempotencia via `FileIdempotencyStore`
ya previene duplicados tras restart.

---

## Artefactos

- `report/pytest_3F4_smoke.txt`
- `report/AG-3F-4-2_pytest.txt`
- `report/AG-3F-4-2_diff.patch`
- `report/AG-3F-4-2_return.md` (este archivo)
