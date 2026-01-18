# AG-3H-2-1 Return Packet

## Objetivo

Implementar rotación/compactación controlada de metrics.ndjson para runs 24/7.

## Baseline

- **Branch**: main
- **HEAD antes**: ccbb2e8
- **Fecha**: 2026-01-10

## Diseño

### Parámetros de rotación

- `--metrics-rotate-max-mb <int>`: Max MB antes de rotar (None = disabled)
- `--metrics-rotate-max-lines <int>`: Max líneas antes de rotar (None = disabled)

### Semántica

- **Default**: Rotación deshabilitada (backward compatible)
- **Rotación atómica**: close+flush → rename a `.N` → reopen
- **Naming**: `metrics.ndjson.1`, `.2`, `.3`, ... (N incrementa)
- **Check interval**: Cada 100 writes por defecto; cada write si max_lines < 100

### metrics_summary.json

El summary **NO se resetea** por rotación. Sigue reflejando el **total acumulado** del collector desde el inicio del proceso. Esto permite:

- Obtener métricas agregadas sin parsear todos los archivos rotados
- Determinismo: el summary es el mismo independientemente de cuántas rotaciones hubo

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `engine/metrics_collector.py` | MetricsWriter con rotación: rotate_max_mb/lines, contadores, _should_rotate(), _rotate(),_find_next_rotation_suffix() |
| `tools/run_live_3E.py` | +flags --metrics-rotate-max-mb/lines, wiring a build_metrics |
| `tests/test_metrics_rotation.py` | [NEW] 9 tests: disabled by default, by lines, naming, no data loss |

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest -q | **PASS** (499 passed, 10 skipped) |
| tests rotación | **9/9 PASS** |
| smoke con rotación | **OK** (3 archivos: .ndjson, .1, .2) |

## Artefactos Smoke (report/out_3H2_rotation_smoke/)

```
metrics.ndjson      (128 bytes) - archivo actual
metrics.ndjson.1    (443 bytes) - rotado
metrics.ndjson.2    (388 bytes) - rotado
metrics_summary.json (861 bytes) - agregados totales
```

## DOD Status: **PASS**

- [x] pytest -q PASS
- [x] Rotación funciona solo cuando se habilita
- [x] Evidencias de rotación (.1, .2) y conteos correctos
- [x] No data loss verificado por tests
