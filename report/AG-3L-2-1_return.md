# AG-3L-2-1 Return Packet

## Baseline

- **Branch base**: feature/AG-3L-1-1_loop_stepper_feed
- **HEAD base**: c46aaecb6fb986319200c4e32c070ff30fa2a7ab

## Objetivo

Añadir soporte de CCXT como dependencia opcional para desarrollo local, con tests gated que no corren en CI.

## Cambios Realizados

### requirements-ccxt.txt (nuevo)

- Pin: `ccxt==4.4.54`
- Instrucciones de uso en comentarios

### tests/test_ccxt_market_data_real_gated_3L2.py (nuevo)

- Tests gated que requieren:
  - ccxt instalado (`pytest.importorskip`)
  - `INVESTBOT_ALLOW_NETWORK=1`
  - `INVESTBOT_CCXT_EXCHANGE` y `INVESTBOT_CCXT_SYMBOL`
- Logs solo presencia/ausencia de variables, nunca valores
- 2 tests: fetch real y adapter integration

### tests/test_ccxt_market_data_mock_parity_3L2.py (nuevo)

- Tests offline (sin ccxt)
- Validan schema parity entre MockOHLCVClient y formato CCXT real
- 9 tests de normalización, tipos y orden

### README.md

- Sección "🔌 CCXT opcional (local)" con instrucciones

## Pytest

```
695 passed, 11 skipped, 7 warnings in 45.01s
```

Ver: `report/pytest_3L2_ccxt_optional.txt`

## Comportamiento Skip

Los tests gated se saltan automáticamente en CI/offline:

- `test_ccxt_market_data_real_gated_3L2.py`: 1 skipped (falta ALLOW_NETWORK)
- Parity tests: 9 passed (no requieren ccxt)

## AUDIT_SUMMARY

### Ficheros Nuevos

- `requirements-ccxt.txt` (dependencia opcional, NO en CI)
- `tests/test_ccxt_market_data_real_gated_3L2.py`
- `tests/test_ccxt_market_data_mock_parity_3L2.py`

### Ficheros Modificados

- `README.md` (sección CCXT opcional añadida)

### Descripción

- CCXT es dependencia opcional instalable por separado
- Tests gated solo corren con variables de entorno configuradas
- CI no requiere cambios (tests se saltan automáticamente)

### Riesgos/TODOs

- Verificar pin de ccxt periódicamente (versión 4.4.54 actual)
- Considerar añadir smoke test real con CCXT como workflow manual
