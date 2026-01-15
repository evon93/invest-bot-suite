# AG-3F-4-1: Crash Recovery v0 — Return Packet

**Ticket**: AG-3F-4-1  
**Rama**: `feature/3F_4_crash_recovery_v0`  
**Fecha**: 2026-01-07

---

## Resumen

Implementación de crash recovery v0 con checkpoint atómico y file-backed idempotency store.

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| [engine/checkpoint.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/checkpoint.py) | `Checkpoint` dataclass con `save_atomic()` (tmp+rename) |
| [tests/test_checkpoint_atomic_write_3F4.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_checkpoint_atomic_write_3F4.py) | 9 tests de checkpoint y FileIdempotencyStore |
| [tests/test_crash_recovery_resume_no_duplicates_3F4.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_crash_recovery_resume_no_duplicates_3F4.py) | 4 tests de crash/resume sin duplicados |

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| [engine/idempotency.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/idempotency.py) | +`FileIdempotencyStore` con JSONL append-only |

---

## Formatos de Archivo

### checkpoint.json

```json
{
  "run_id": "run_20260107_192400",
  "last_processed_idx": 6,
  "processed_count": 7,
  "updated_at": "2026-01-07T19:25:00Z"
}
```

### idempotency_keys.jsonl

```jsonl
{"key": "exec:intent-001"}
{"key": "exec:intent-002"}
{"key": "exec:intent-003"}
```

---

## Comandos para Reproducir Crash/Recovery

```bash
# Primera ejecución (con crash simulado)
python tools/run_live_3E.py --run-dir report/runs/my_run

# Reanudar tras crash
python tools/run_live_3E.py --resume report/runs/my_run
```

> **Nota**: Los argumentos `--run-dir` y `--resume` no están integrados en run_live_3E.py aún.
> La lógica de checkpoint/idempotency está implementada y probada unitariamente.

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_checkpoint_*.py tests/test_crash_recovery_*.py -v` | 13 passed |
| `pytest -q` | **432 passed**, 10 skipped |

---

## DoD Verificado

- [x] `pytest -q` PASS (432 passed, +13 nuevos)
- [x] Test de resume demuestra 0 duplicados tras crash/restart
- [x] Checkpoint atómico (tmp+rename)
- [x] FileIdempotencyStore con persistencia JSONL

---

## Artefactos Generados

- `report/pytest_3F4_checkpoint.txt`
- `report/AG-3F-4-1_pytest.txt`
- `report/AG-3F-4-1_diff.patch`
- `report/AG-3F-4-1_return.md` (este archivo)
