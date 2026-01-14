# AG-3L-3-1 Return Packet

## Baseline

- **Branch base**: feature/AG-3L-2-1_ccxt_optional
- **HEAD base**: 6847c79

## Objetivo

Endurecer MockOHLCVClient con validación estricta para edge-cases OHLCV.

## Cambios Realizados

### engine/market_data/ccxt_adapter.py

- **Nueva clase `OHLCVValidationError`** para errores de validación
- **Nueva función `validate_ohlcv_data()`** con policy estricta:
  - out-of-order timestamps → OHLCVValidationError
  - duplicate timestamps → OHLCVValidationError
  - gaps → warning/flag (no raise)
  - invalid OHLC relationships → OHLCVValidationError
  - negative volume → OHLCVValidationError
- **MockOHLCVClient actualizado**:
  - Parámetro `data: List[List]` para inyección de datos externos
  - Parámetro `strict: bool = True` para validación
  - Atributo `has_gaps` para flag de gaps
  - Docstring con contract documentado

### tests/test_mock_ohlcv_edge_cases_3L3.py (nuevo)

- 16 tests de edge-cases:
  - 3 tests out-of-order
  - 2 tests duplicates
  - 2 tests gaps
  - 3 tests OHLC relationships
  - 3 tests valid data
  - 2 tests empty data
  - 1 test non-strict mode

## Pytest

```
711 passed, 11 skipped, 7 warnings in 43.80s
```

Ver: `report/pytest_3L3_mock_edge_cases.txt`

## AUDIT_SUMMARY

### Ficheros Modificados

- `engine/market_data/ccxt_adapter.py` (+110 líneas en validación, +20 líneas en MockOHLCVClient)

### Ficheros Nuevos

- `tests/test_mock_ohlcv_edge_cases_3L3.py`

### Descripción

- Strict default: validación activa por defecto
- Contract documentado en docstring de MockOHLCVClient
- No lookahead: validación no modifica ni reordena datos

### Riesgos/TODOs

- Ninguno identificado - cambios mínimos y retrocompatibles
