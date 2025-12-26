# Paso 0B — Diagnóstico backtester (invest-bot-suite)

## Entorno
- Sistema: WSL Ubuntu 24.04 sobre Windows 11
- Python: 3.12.3 (según \`python --version\`)
- Rama: orchestrator-v2
- Venv: .venv activado

## Resultado tests `test_backtest_deepseek.py`
- Resumen pytest (`report/pytest_20251124_backtest_0B_summary.txt`):
  - Número total de tests: 6
  - Tests que fallan:
    - test_metrics_calculation
    - test_metrics_after_crash
    - test_rebalance_frequency
    - test_zero_prices
- Logs detallados:
  - test_metrics_calculation → `report/pytest_20251124_0B_test_metrics_calculation.txt`
  - test_metrics_after_crash → `report/pytest_20251124_0B_test_metrics_after_crash.txt`
  - test_rebalance_frequency → `report/pytest_20251124_0B_test_rebalance_frequency.txt`
  - test_zero_prices → `report/pytest_20251124_0B_test_zero_prices.txt`

## Observaciones preliminares
- test_metrics_calculation:
  - Espera: -0.5 < max_drawdown < 0 y -0.5 < cagr < 2.0.
  - Resultado actual: metrics['max_drawdown'] = nan (warning por división inválida en `calculate_metrics` cuando el valor inicial del portfolio es 0).
- test_metrics_after_crash:
  - Espera: max_drawdown <= -0.35 y cagr < 0 en un escenario con crash -40%.
  - Resultado actual: metrics['max_drawdown'] = nan (mismo problema de robustez en métricas ante valor inicial 0 o serie degenerada).
- test_rebalance_frequency:
  - Espera: al menos 3 días de rebalanceo en 100 días, con intervalos medios entre 25 y 35 días.
  - Resultado actual: backtester.trades queda vacío; no se genera ningún rebalanceo con los datos sintéticos actuales.
- test_zero_prices:
  - Espera: portfolio.iloc[-1]['value'] > 0 aunque haya precios 0 y negativos.
  - Resultado actual: el valor final del portfolio es 0.0; la lógica no maneja explícitamente precios 0/negativos ni garantiza supervivencia del portfolio.

## Archivos relevantes
- Tests:
  - `tests/test_backtest_deepseek.py`
  - Snapshot: `report/test_backtest_deepseek_snapshot_0B.py`
- Backtester:
  - Implementación activa: `backtest_initial.py`
  - Backup previo: `backtest_initial.py.bak_0A`
- Logs y entorno:
  - `report/pytest_20251124_backtest_0B_summary.txt`
  - `report/pytest_20251124_0B_test_metrics_calculation.txt`
  - `report/pytest_20251124_0B_test_metrics_after_crash.txt`
  - `report/pytest_20251124_0B_test_rebalance_frequency.txt`
  - `report/pytest_20251124_0B_test_zero_prices.txt`
  - `report/env_20251121.json`
