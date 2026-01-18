# AG-3B-2-2 Return Packet — OHLCV Loader Hardening

## Resumen

Se ha "endurecido" (harden) el `ohlcv_loader.py` para soportar patrones de datos reales y garantizar la integridad temporal necesaria para el runner.

## Mejoras Implementadas

- **Soporte Epoch Automático**: Infiere unidades (s, ms, us, ns) basado en la magnitud del timestamp numérico.
- **Contrato UTC Estricto**: `pd.to_datetime(..., utc=True)` forzado. Tests validan `datetime64[ns, UTC]`.
- **Aliases Ampliados**: Soporte para `Open`, `open_price`, `High`, `Timestamp`, etc. manteniéndose case-insensitive.
- **Micro-Tests**: Verificación de patrones de consumo iterativo (`itertuples`) y operaciones vectorizadas (`rolling`) típicas del bucle de simulación.

## Verificación

- **Pytest**: `tests/test_ohlcv_loader.py` (10 passed, 1 skipped).
- **Cobertura**:
  - Epochs en s, ms, us.
  - Strings con offset de zona horaria (e.g. `-05:00`).
  - Integridad de atributos en `itertuples`.

## Archivos Entregados

- `data_adapters/ohlcv_loader.py`: Código actualizado.
- `tests/test_ohlcv_loader.py`: Tests expandidos.
- `report/AG-3B-2-2_diff.patch`: Diff del hardening.
