# AG-3G-2-2 Notes

## Decisiones

### 1. Helper Puro

- `build_idempotency_store(run_dir, backend)` es una función pura
- Facilita testing y reutilización
- Mantiene main() limpio

### 2. Default No Cambiado

- `--idempotency-backend` default = "file"
- Comportamiento actual preservado 100%
- Solo cambia si se especifica explícitamente

### 3. Paths de Artefactos

- file: `{run_dir}/idempotency_keys.jsonl` (existente)
- sqlite: `{run_dir}/idempotency.db` (nuevo)
- memory: no crea archivos

### 4. Error Handling

- Backend desconocido → ValueError con mensaje claro
- Consistente con el patrón existente

## Tests Añadidos

- `test_run_live_idempotency_backend.py`: 8 tests
  - sqlite: create DB, persistence
  - file: create JSONL, persistence
  - memory: no persistence
  - unknown backend: raises
  - CLI: default=file, sqlite selectable
