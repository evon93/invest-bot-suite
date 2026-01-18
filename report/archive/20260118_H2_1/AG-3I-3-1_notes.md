# AG-3I-3-1 Notes - Audit Window Findings

## Naming de Rotación

Confirmado que la rotación usa sufijos numéricos: `metrics.ndjson.1`, `metrics.ndjson.2`, etc.
El sufijo más alto = más reciente. Esto se respeta en el cleanup.

## Protecciones Implementadas

1. **No borra `metrics.ndjson` activo**: El método `_cleanup_rotated()` solo busca `metrics.ndjson.*` (con sufijo), y el glob excluye el fichero activo.

2. **No borra sufijos no numéricos**: El cleanup solo considera ficheros con sufijo `.isdigit()`, así que `metrics.ndjson.backup` o similares no se tocan.

3. **Best-effort**: Errores en borrado individual se ignoran (try/except por fichero).

## Out-of-Scope Findings (no implementados)

1. **Retención por tamaño total**: Podría añadirse `--metrics-rotate-max-total-mb` para limpiar hasta alcanzar un tope de bytes agregado. Requeriría sumar tamaños de rotados.

2. **Retención por edad**: Podría añadirse `--metrics-rotate-max-age-days` para limpiar ficheros de más de N días. Requeriría stat() de mtime.

Ninguna acción requerida para este ticket.
