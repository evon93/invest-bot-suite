# AG-H2-2-1 Return Packet

## Metadata

| Campo | Valor |
|-------|-------|
| Ticket | AG-H2-2-1 |
| Objetivo | Eliminar DeprecationWarning de is_datetime64tz_dtype |
| Status | **PASS** |
| Fecha | 2026-01-18 |

## Baseline

- Branch: `main`
- HEAD: `c1a4962f5cd01ba2d92a26e251c7e0bd7097fb1e`

## Cambios realizados

- **Archivo**: `tests/test_ohlcv_loader.py`
- **5 ocurrencias** de `pd.api.types.is_datetime64tz_dtype(df["timestamp"])` reemplazadas por `isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)`
- Líneas afectadas: 23, 108, 122, 136, 149

## Verificación

| Test | Resultado |
|------|-----------|
| pytest test_ohlcv_loader.py | 10 passed, 1 skipped ✓ |
| pytest full | 747 passed, 11 skipped, 2 warnings ✓ |

## Artefactos generados

- `report/AG-H2-2-1_return.md`
- `report/AG-H2-2-1_last_commit.txt`
- `report/AG-H2-2-1_diff.txt`
- `report/AG-H2-2-1_pytest_ohlcv.txt`
- `report/AG-H2-2-1_pytest_full.txt`
- `report/AG-H2-2-1_rg_hits.txt`

## AUDIT_SUMMARY

- **Archivos modificados**: `tests/test_ohlcv_loader.py` (5 líneas)
- **Descripción**: Migración de API deprecada `is_datetime64tz_dtype` a `isinstance(dtype, pd.DatetimeTZDtype)`
- **Riesgos**: Ninguno. Cambio de patrón equivalente semánticamente.
