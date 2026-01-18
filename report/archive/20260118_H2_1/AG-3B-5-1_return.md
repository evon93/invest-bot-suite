# AG-3B-5-1 Return Packet — Integrated Runner 3B.5

## Resumen

Se ha implementado el runner integrado `tools/run_live_integration_3B.py` que conecta todos los componentes de la fase 3B (Loader, Strategy, Execution) con el Risk Manager existente (vía shim).

## Arquitectura

1. **Data Adapter**: Carga OHLCV (csv/parquet).
2. **Strategy Engine v0.7**: Genera `OrderIntent` (Signal).
3. **Risk Shim**: Adapta `OrderIntent` -> `dict` (compatibilidad RiskManager v0.4) y devuelve `RiskDecision`.
4. **Execution Adapter v0.2**: Simula `ExecutionReport` (Slippage/Latency) si el riesgo lo permite.
5. **Event Log**: Serializa la secuencia completa a `NDJSON`.

## Verificación

- **Smoke Test**: `tests/test_run_live_integration_3B.py` (Passed).
- **Flujo Validado**: Se verificó la generación de eventos de los tres tipos (`OrderIntent`, `RiskDecision`, `ExecutionReport`) en una simulación con datos sintéticos.

## Archivos Entregados

- `tools/run_live_integration_3B.py`: Código del runner.
- `tests/test_run_live_integration_3B.py`: Tests de integración.
- `report/AG-3B-5-1_diff.patch`: Diff del commit.
