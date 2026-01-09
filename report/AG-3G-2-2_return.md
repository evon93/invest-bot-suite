# AG-3G-2-2 Return Packet

**Ticket**: AG-3G-2-2 — Wire SQLiteIdempotencyStore into run_live_3E  
**Status**: ✅ PASS  
**Branch**: `feature/AG-3G-2-2_wire_sqlite_backend`  
**Commit**: `23056e7`

---

## Baseline

| Campo | Valor |
|-------|-------|
| Branch base | `feature/AG-3G-2-1_sqlite_idempotency_store` |
| HEAD base | `3646a54` |

---

## Cambios Realizados

### tools/run_live_3E.py

| Cambio | Descripción |
|--------|-------------|
| Imports | +`SQLiteIdempotencyStore`, `InMemoryIdempotencyStore`, `IdempotencyStore` |
| CLI arg | `--idempotency-backend {file,sqlite,memory}` (default=file) |
| Helper | `build_idempotency_store(run_dir, backend)` → IdempotencyStore |
| Wiring | `--resume/--run-dir` usan helper |

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| `tests/test_run_live_idempotency_backend.py` | 8 tests de wiring |

---

## Features

```bash
# Uso default (file - comportamiento existente)
python tools/run_live_3E.py --run-dir /tmp/run1

# SQLite backend
python tools/run_live_3E.py --run-dir /tmp/run1 --idempotency-backend sqlite

# Memory (no persistence)
python tools/run_live_3E.py --run-dir /tmp/run1 --idempotency-backend memory
```

---

## Tests

| Suite | Estado |
|-------|--------|
| pytest global | 454 passed, 10 skipped ✅ |
| wiring tests | 8 passed ✅ |

---

## AUDIT_SUMMARY

**Paths tocados**:

- `tools/run_live_3E.py` (M: +51 líneas)
- `tests/test_run_live_idempotency_backend.py` (A)
- `report/AG-3G-2-2_*.{md,txt,patch}` (A)

**Cambios clave**: CLI arg + helper para selección de idempotency backend.

**Default**: No cambiado (file).

**Resultado**: PASS.
