# AG-2B-3-3-8 Return Packet — Sensitivity Harness

## Resultado

✅ Grid con `--scenario sensitivity` produce **variación observable** en métricas.

## Evidencia: 24 Combos con Sensibilidad

| combo_id | dd_hard | score | pct_hard_stop | risk_rejects |
|----------|---------|-------|---------------|--------------|
| ffae19fec604 | 0.10 | 0.274 | 71.4% | dd_hard:5 |
| 0576d1c2bfe6 | 0.10 | 0.274 | 71.4% | dd_hard:5 |
| 2411a44ce582 | 0.10 | 0.274 | 71.4% | dd_hard:5 |
| 9daf5a15114e | **0.15** | **0.346** | **57.1%** | dd_hard:4,dd_soft:1 |
| 671ea044ad47 | **0.15** | **0.346** | **57.1%** | dd_hard:4,dd_soft:1 |
| 1b221ec79489 | **0.15** | **0.346** | **57.1%** | dd_hard:4,dd_soft:1 |

**Discriminación confirmada**:

- Score: 0.274 (dd_hard=10%) vs 0.346 (dd_hard=15%)
- pct_time_hard_stop: 71.4% vs 57.1%

## Cambios Implementados

### `tools/run_calibration_2B.py`

- `generate_sensitivity_prices()`: precios con regímenes de vol (crash phase)
- `--scenario {default,sensitivity}` CLI flag
- Scenario parameter wiring through `run_calibration` → `run_single_backtest`

### `tests/test_calibration_2B_grid_discriminates.py` (nuevo)

- `TestSensitivityScenario`: verifica que precios tienen drawdown
- `TestGridDiscriminates`: verifica variación de scores/hashes

## Tests

- 141 passed, 1 skipped

## Commit

**`bc15e5a`** — `2B: add deterministic sensitivity harness for calibration grid discrimination`

## Uso

```powershell
python tools/run_calibration_2B.py `
  --mode full `
  --max-combinations 24 `
  --scenario sensitivity `
  --output-dir report/out_sensitivity_test
```
