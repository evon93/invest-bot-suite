# AG-2J-1-1 E2E Synthetic Pipeline Results

## Veredicto

- **Estado**: PASS
- **Duración**: ~7s (Calibration) + ~1s (Frozen/Dash/Validate)
- **Output Dir**: `report/out_2J_1_1_demo_final`

## Ejecución

Se ejecutó el pipeline completo en WSL (Python 3.12.3) concatenando las siguientes etapas:

1. **Calibration**: `run_calibration_2B.py` (`mode=full_demo`).
    - GATE: PASS (100% active rate).
2. **Freeze**: `freeze_topk_2H.py`.
    - Generó `best_config.json` y `topk_explicit.json`.
3. **Dashboard**: `build_dashboard.py`.
    - Generó `index.html` y `summary.json`.
4. **Validate**: `validate_risk_config.py`.
    - Resultados: 0 Errors, 6 Warnings (missing sections en partial config).

## Comandos

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && (python tools/run_calibration_2B.py --mode full_demo --output-dir report/out_2J_1_1_demo_final && python tools/freeze_topk_2H.py --results-agg report/out_2J_1_1_demo_final/results_agg.csv --out-config report/out_2J_1_1_demo_final/best_config.json --out-report report/out_2J_1_1_demo_final/topk_explicit.json && python tools/build_dashboard.py --run-dir report/out_2J_1_1_demo_final --out report/out_2J_1_1_demo_final && python tools/validate_risk_config.py -c report/out_2J_1_1_demo_final/best_config.json) > report/AG-2J-1-1_run.txt 2>&1"
```

## Artefactos Generados

Ver `AG-2J-1-1_tree.txt` para listado completo.

- `results.csv` / `results_agg.csv`
- `best_config.json`
- `index.html` (Dashboard)
- `run_log.txt`
