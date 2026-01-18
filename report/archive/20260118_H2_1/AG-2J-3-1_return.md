# AG-2J-3-1 CI Workflow: E2E Smoke 2J

## Veredicto

- **Estado**: IMPLEMENTED (CI only)
- **Workflow**: `.github/workflows/e2e_smoke_2J.yml`
- **Trigger**: Push (main) / PR (*) / Dispatch

## Descripción

Se ha añadido un workflow de GitHub Actions que ejecuta el runner canónico `tools/run_e2e_2J.py` sobre Ubuntu/Python 3.12.

### Pasos Clave

1. **Setup**: Python 3.12 + deps (requirements.txt).
2. **Execution**: `python tools/run_e2e_2J.py --outdir report/runs/2J_e2e_synth_ci --seed 42`.
    - El runner falla automáticamente si la validación de config (`validate_risk_config.py`) reporta Errors > 0 o Warnings > 0.
3. **Verification**: Scripts `bash` adicionales para comprobar exsitencia de:
    - `results_agg.csv`
    - `risk_rules_prod.yaml`
    - `index.html` (Dashboard)
4. **Artifacts Upload**: Se suben 3 paquetes de artifactor (Calibration, Configs, Dashboard) para inspección en caso de fallo.

## Artefactos Entregados

- `.github/workflows/e2e_smoke_2J.yml`
- `report/AG-2J-3-1_diff.patch`
- `report/AG-2J-3-1_last_commit.txt`
