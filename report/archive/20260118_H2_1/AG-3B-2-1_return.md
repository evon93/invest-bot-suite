# AG-3B-2-1 Return Packet — OHLCV Loader (v0)

## Resumen

Se ha implementado el módulo `data_adapters/ohlcv_loader.py` para la carga normalizada de datos OHLCV desde CSV (y Parquet si las dependencias existen).

## Características

- **Normalización**: Convierte alias comunes (`Date`, `Vol`, `Open`, etc.) a estándar (`timestamp`, `open`, `high`, `low`, `close`, `volume`).
- **Validación Strict**:
  - Timestamps UTC y monotónicos.
  - Sin duplicados ni NaNs en columnas requeridas.
- **Detección de Gaps**: Reporta (warning) saltos mayores a 1.5x la mediana del intervalo.
- **Offline / Sin dependencias nuevas**: Parquet soportado pero opcional (skip en tests si falta engine).

## Verificación

- **Pytest**: `tests/test_ohlcv_loader.py` (5 passed, 1 skipped).
- **Parquet**: Test skippeado correctamente al no detectar `pyarrow`/`fastparquet` en entorno minimal.

## Archivos Entregados

- `data_adapters/ohlcv_loader.py`: Implementación.
- `tests/test_ohlcv_loader.py`: Test suite.
- `report/AG-3B-2-1_diff.patch`: Diff del commit.
