# Active Context â€” invest-bot-suite

- **Proyecto**: invest-bot-suite
- **Rama actual**: `main`
- **Ãšltima actualizaciÃ³n**: 2025-12-30

## Estado actual: 2E-3.3 + 7.2 mergeados

- **HEAD**: `8fb7db3` (report: add 2E-3.3 gate semantics evidence)
- **Fase**: 2E Phase completado + 7.2 CLI polish
- **Tests**: 132 passed
- **Validador**: 0 errors, 0 warnings

## PRs Mergeados Recientemente

| PR | Commit | DescripciÃ³n |
|----|--------|-------------|
| #11 | 073b643 | 7.2: CLI full_demo alias + tests |
| #12 | e3fb90d | 2E-3.3: gate semantics fix (OR logic + granular reasons) |
| (direct) | 8fb7db3 | Evidence artifacts commit |

## Features 2E Implementadas

### Gate Evaluation (2E-3.3)

- Thresholds independientes (OR logic): `active_n`, `active_rate`, `inactive_rate`, `active_pass_rate`
- `gate_fail_reasons` granulares en `run_meta.json`
- `--strict-gate` flag para exit code 1 en CI

### YAML Profiles (2E-3.4)

- `configs/risk_calibration_2B.yaml` contiene perfiles: `quick`, `full_demo`, `full`
- `--profile` flag en CLI para selecciÃ³n explÃ­cita
- `--mode full_demo` como alias de `--mode full --profile full_demo`

### Inactive Instrumentation (2E-4)

- `is_active`, `rejection_*` flags en CSV
- `risk_reject_reasons_topk` en meta

## CÃ³mo ejecutar tests

```powershell
python -m pytest -q
python tools/validate_risk_config.py --config risk_rules.yaml
```

## PrÃ³ximo paso

Ver backlog en `registro_de_estado_invest_bot.md`.
## [2025-12-30] Estado actual (post 2B-3.3)

- Branch: main (origin/main)
- Head: 831710e (report pack) + bc15e5a (código)
- 2E gate: integrado (activity stats + rejection reasons presentes en out_2E_*).
- 2B calibration: grid ya discrimina overrides por effective_config_hash y, además, discrimina métricas con scenario determinista.

Evidencia:
- report/AG-2B-3-3-8_return.md
- report/out_2B_3_3_grid_discriminates_20251230/

Notas:
- El dataset sintético default no activaba triggers de riesgo; por eso las métricas eran idénticas.
- Usar: python tools/run_calibration_2B.py --mode full --max-combinations 24 --scenario sensitivity --output-dir <dir>
## [2025-12-30] Estado actual (post 2B-3.3)

- Branch: main (origin/main)
- Head: 831710e (report pack) + bc15e5a (código)
- 2E gate: integrado (activity stats + rejection reasons presentes en out_2E_*).
- 2B calibration: grid ya discrimina overrides por effective_config_hash y, además, discrimina métricas con scenario determinista.

Evidencia:
- report/AG-2B-3-3-8_return.md
- report/out_2B_3_3_grid_discriminates_20251230/

Notas:
- El dataset sintético default no activaba triggers de riesgo; por eso las métricas eran idénticas.
- Usar: python tools/run_calibration_2B.py --mode full --max-combinations 24 --scenario sensitivity --output-dir <dir>
