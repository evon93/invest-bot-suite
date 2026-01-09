# AG-3G-2-1 Return Packet

**Ticket**: AG-3G-2-1 — SQLite Idempotency Store (WAL + INSERT OR IGNORE)  
**Status**: ✅ PASS  
**Branch**: `feature/AG-3G-2-1_sqlite_idempotency_store`  
**Commit**: `6a4b35e AG-3G-2-1: sqlite idempotency store (WAL) + tests`

---

## Baseline

| Campo | Valor |
|-------|-------|
| Branch inicial | `main` |
| HEAD inicial | `741365d` |

---

## Cambios Realizados

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `engine/idempotency.py` | +`SQLiteIdempotencyStore` (~100 líneas) |

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| `tests/test_idempotency_store_sqlite.py` | 14 tests unitarios |

---

## Implementación

### SQLiteIdempotencyStore

- **WAL mode**: `PRAGMA journal_mode=WAL` para concurrencia
- **Synchronous**: NORMAL (configurable a FULL)
- **Atomicidad**: `INSERT OR IGNORE` + PRIMARY KEY
- **Thread-safe**: `threading.Lock()` interno
- **Métodos**: `mark_once(key)` → bool, `contains(key)`, `size()`, `close()`

### Default No Cambiado

- `run_live_3E.py` sigue usando `FileIdempotencyStore`
- SQLite queda disponible para futuro wiring

---

## Tests

| Suite | Estado |
|-------|--------|
| pytest global | 446 passed, 10 skipped ✅ |
| test_idempotency_store_sqlite.py | 14 passed ✅ |

### Cobertura Tests SQLite

- Basic: first/second insert, multiple keys
- Persistence: across instances, crash recovery
- Concurrency: N threads same key (exactly 1 True)
- WAL: mode verification
- Edge cases: empty/unicode/long keys

---

## AUDIT_SUMMARY

**Paths tocados**:

- `engine/idempotency.py` (M: +103 líneas)
- `tests/test_idempotency_store_sqlite.py` (A)
- `report/AG-3G-2-1_*.{md,txt,patch}` (A)

**Cambios clave**: SQLiteIdempotencyStore con WAL, INSERT OR IGNORE, thread-safe.

**Riesgos**: Ninguno (default no cambiado, solo nuevos tests).

**Resultado**: PASS.
