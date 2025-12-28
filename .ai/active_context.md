# Active Context — invest-bot-suite

- **Proyecto**: invest-bot-suite
- **Rama actual**: `main`
- **Última actualización**: 2025-12-26

## Estado actual: 2C completado

- **HEAD**: `3c3d74b` (H0: renormalize line endings)
- **Fase**: 2C completada + EOL hygiene done
- **Tests**: 77 passed
- **Validador**: 0 errors, 0 warnings

## Cómo ejecutar tests

```powershell
# Forma recomendada en Windows
python -m pytest -q

# Validar configuración de riesgo
python tools/validate_risk_config.py --config risk_rules.yaml
```

## Herramientas 2C añadidas

| Tool | Propósito |
|------|-----------|
| `tools/best_params_schema_2C.py` | Schema + selector topk |
| `tools/build_best_params_2C.py` | Builder CLI |
| `tools/apply_calibration_topk.py` | Apply params a YAML |

## Configs generados

- `configs/best_params_2C.json` — Parámetros calibrados
- `risk_rules_candidate.yaml` — Candidato (ya promovido)

## Próximo paso: 2D

Ver `bridge_2C_to_2D_report.md` para roadmap.
