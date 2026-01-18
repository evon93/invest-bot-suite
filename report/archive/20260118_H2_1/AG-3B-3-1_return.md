# AG-3B-3-1 Return Packet — Strategy Engine v0.7 (SMA Crossover)

## Resumen

Implementado el motor de estrategia `StrategyEngine v0.7` que consume datos OHLCV y emite eventos `OrderIntent` (Signal -> Order) basados en cruces de medias móviles (SMA Crossover).

## Componentes

- **Strategy Engine**: `strategy_engine/strategy_v0_7.py`. Función pura `generate_order_intents`.
  - Input: DataFrame (OHLCV), params (dict), ticker, timestamp de corte (`asof_ts`).
  - Output: Lista de `OrderIntent`.
  - Lógica: Golden Cross (Buy), Death Cross (Sell).
- **Contrato**: Reutilizado `OrderIntent` de `contracts/event_messages.py`.
- **Tests**: `tests/test_strategy_v0_7.py`.
  - Cobertura: Buy signal, Sell signal, No signal, Warmup insuficiente, Time-travel slicing.

## Verificación

- **Pytest**: `tests/test_strategy_v0_7.py` (5 passed).
- **Determinismo**: La estrategia es puramente funcional y determinista basada en el input.

## Archivos Entregados

- `strategy_engine/strategy_v0_7.py`: Implementación.
- `tests/test_strategy_v0_7.py`: Tests unitarios.
- `report/AG-3B-3-1_diff.patch`: Diff del commit.
