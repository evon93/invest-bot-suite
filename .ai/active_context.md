# Active Context — invest-bot-suite

- **Proyecto**: invest-bot-suite
- **Rama actual**: `main`
- **Última actualización**: 2025-12-30

## Estado actual: 2E-3.3 + 7.2 mergeados

- **HEAD**: `8fb7db3` (report: add 2E-3.3 gate semantics evidence)
- **Fase**: 2E Phase completado + 7.2 CLI polish
- **Tests**: 132 passed
- **Validador**: 0 errors, 0 warnings

## PRs Mergeados Recientemente

| PR | Commit | Descripción |
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
- `--profile` flag en CLI para selección explícita
- `--mode full_demo` como alias de `--mode full --profile full_demo`

### Inactive Instrumentation (2E-4)

- `is_active`, `rejection_*` flags en CSV
- `risk_reject_reasons_topk` en meta

## Cómo ejecutar tests

```powershell
python -m pytest -q
python tools/validate_risk_config.py --config risk_rules.yaml
```

## Próximo paso

Ver backlog en `registro_de_estado_invest_bot.md`.
