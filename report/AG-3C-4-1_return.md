# AG-3C-4-1 Return Packet — SQLite Position Store

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-4-1 (WSL + venv)  
**Rama:** `feature/3C_4_sqlite_state`  
**Estado:** ✅ COMPLETADO

---

## 1. Archivos Añadidos

| Archivo | Descripción |
|---------|-------------|
| `state/__init__.py` | Package init |
| `state/position_store_sqlite.py` | SQLite position store |
| `tests/test_position_store_sqlite.py` | 22 tests |

---

## 2. API Implementada

### `PositionStoreSQLite(db_path)`

```python
with PositionStoreSQLite("state.db") as store:
    store.upsert_position("BTC/USDT", 1.5, avg_price=50000.0)
    store.apply_fill("BTC/USDT", "BUY", 0.5, 55000.0)
    pos = store.get_position("BTC/USDT")
```

**Schema:**

```sql
positions(symbol TEXT PRIMARY KEY, qty REAL, avg_price REAL, updated_at TEXT, meta_json TEXT)
kv(key TEXT PRIMARY KEY, value TEXT)
```

**Métodos:**

| Método | Descripción |
|--------|-------------|
| `ensure_schema()` | Crea tablas (idempotente) |
| `get_position(symbol)` | Obtiene posición por símbolo |
| `upsert_position(symbol, qty, ...)` | Inserta/actualiza posición |
| `list_positions()` | Lista todas las posiciones |
| `delete_position(symbol)` | Elimina posición |
| `apply_fill(symbol, side, qty, price)` | Aplica fill (recalcula avg_price) |
| `set_kv(key, value)` / `get_kv(key)` | Key-value store |

---

## 3. Tests

| Suite | Tests | Descripción |
|-------|-------|-------------|
| TestEnsureSchema | 3 | Idempotencia, context manager |
| TestPositionCRUD | 9 | upsert/get/list/delete/meta |
| TestApplyFill | 8 | BUY/SELL, avg recalc, close |
| TestKeyValueStore | 4 | set/get/delete KV |

**pytest total:** 294 passed, 7 skipped

---

## 4. Commit

```
391eeb8 3C.4: add sqlite position store + tests
```

---

## 5. Artefactos

- [AG-3C-4-1_pytest.txt](AG-3C-4-1_pytest.txt)
- [AG-3C-4-1_diff.patch](AG-3C-4-1_diff.patch)
- [AG-3C-4-1_last_commit.txt](AG-3C-4-1_last_commit.txt)

---

## 6. Notas

- **Sin integración en runner** — CLI stub `--state-db` se deja para ticket 3C.5
- **stdlib only** — Usa solo `sqlite3`, sin dependencias externas
- **Idempotente** — `ensure_schema()` seguro de llamar múltiples veces
