# AG-3G-2-1 Notes

## Decisiones de Diseño

### 1. Ubicación

- Añadido en `engine/idempotency.py` junto a las otras implementaciones
- Mantiene coherencia con el repo

### 2. WAL Mode

- `PRAGMA journal_mode=WAL` para mejor concurrencia read/write
- `PRAGMA synchronous=NORMAL` como default (buen balance entre seguridad y performance)
- Configurable vía parámetro `synchronous="FULL"` si se necesita más durabilidad

### 3. Atomicidad

- `INSERT OR IGNORE` con PRIMARY KEY garantiza first-writer-wins
- `cursor.rowcount == 1` indica si fue primera inserción (True) o duplicado (False)
- No hay race conditions gracias a la atomicidad de SQLite

### 4. Thread Safety

- `threading.Lock()` interno para serializar acceso
- `check_same_thread=False` permite uso multi-thread
- `isolation_level=None` (autocommit) evita problemas de transacciones largas

### 5. Default No Cambiado

- El wiring actual en `run_live_3E.py` sigue usando `FileIdempotencyStore`
- SQLiteIdempotencyStore queda disponible como opción para futuro wiring
- NO se cambió el default para evitar drift (según ticket)

## Pendiente para Wiring (fuera de scope este ticket)

- Añadir opción CLI `--idempotency-backend sqlite|file|memory`
- Si `--run-dir`: usar `run_dir/idempotency.db` en lugar de `.jsonl`
- Documentar en README/help

## Tests Añadidos

- `test_idempotency_store_sqlite.py`: 14 tests
  - Basic: first/second insert, multiple keys, contains
  - Persistence: across instances, crash recovery
  - Concurrency: same key (exactly 1 True), different keys (all True)
  - WAL: verify mode enabled, synchronous NORMAL
  - Edge cases: empty key, unicode, very long key, size accuracy
