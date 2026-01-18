# AG-2J-1-2 Canonical E2E Synth Runner

## Veredicto

- **Estado**: PASS
- **Runner**: `tools/run_e2e_2J.py`
- **Strict Validation**: PASSED (0 Errors, 0 Warnings en `configs/risk_rules_prod.yaml`)

## Cambios Realizados

1. **Nuevo Runner**: Implementado `tools/run_e2e_2J.py` que orquesta la ejecución secuencial en WSL:
    - Calibration (2B) -> `report/runs/2J_e2e_synth`
    - Freeze (2H) -> `configs/best_params_2H.json`
    - Render (2I) -> `configs/risk_rules_prod.yaml`
    - Validate (Strict) -> Falla si Errors>0/Warnings>0
    - Dashboard (2I) -> `report/dashboard_2J/`
    - Robustness (2D) -> `validate_robustness_2D_config.py`

2. **Fix en Freeze Tool**: Se modificó `tools/freeze_topk_2H.py` para excluir columnas de metadatos (`combo_id`, `score_*`) de la detección de parámetros. Esto evita que claves inválidas contaminen el JSON de configuración y causen errores en el paso de Render.

## Ejecución

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_e2e_2J.py --outdir report/runs/2J_e2e_synth" > report/AG-2J-1-2_run.txt 2>&1
```

## Artefactos

Ver `AG-2J-1-2_tree.txt` para detalles.

- `configs/risk_rules_prod.yaml`: Configuración final lista para producción.
- `report/runs/2J_e2e_synth/`: Resultados de calibración.
- `configs/best_params_2H.json`: Parámetros seleccionados (overlay).
- `report/dashboard_2J/index.html`: Dashboard generado.

## Commit

`2J.1: add canonical E2E synth runner (strict validation)`
