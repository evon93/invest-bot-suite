# Notas sobre el Snapshot AG-H1-0-2B

## Anomalía 1: Estructura de directorios

El prompt original asumía la existencia de una carpeta `src/`. El análisis revela que `src/` no existe o está vacía.
El código fuente principal se encuentra distribuido en:

- Raíz (`.`)
- `engine/`
- `bus/`
- `strategy_engine/`
- `adapters/`

Estos han sido categorizados como `other` en los reportes de buckets.
Para futuros cálculos de métricas, se recomienda definir `src` como la suma de estas carpetas.

## Anomalía 2: Peso del directorio `report/`

Se detectaron archivos `.patch` masivos que distorsionan las métricas de líneas físicas totales:

- `report/AG-2D-02-2A_diff.patch`: 174k líneas
- `report/AG-3O-2-2_diff.patch`: 82k líneas

Estos archivos deberían ser excluidos de conteos habituales de "Codebase size" o movidos a almacenamiento externo/ignorado si no son críticos para auditoría histórica inmediata.
