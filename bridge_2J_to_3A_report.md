# Bridge Report: Phase 2J to 3A

**Date**: 2026-01-03
**Status**: 2J COMPLETE
**Current Head**: `0bf352c` (2J.5: bridge 2J to 3A (docs))
**Branch**: `main`

## 1. Estado Actual (Phase 2J Complete)

La fase 2J ("Synthetic E2E Pipeline") ha establecido un ciclo completo de ejecución y validación de riesgo sintético, conectando Calibración (2B) → Freeze (2H) → Render (2I) → Validate → Dashboard.

### Adiciones Clave en 2J

1. **Runner Canónico**: `tools/run_e2e_2J.py`.
    - Script único que orquesta todo el pipeline.
    - Garantiza reproducibilidad (seed 42 por defecto).
2. **Validación Estricta**:
    - El pipeline falla si `validate_risk_config.py` reporta **cualquier** Error o Warning en la configuración de producción.
    - Se asegura que `configs/risk_rules_prod.yaml` es 100% compliant.
3. **Provenance & Audit**:
    - `configs/risk_rules_prod.yaml` incluye cabeceras con SHAs de base (`risk_rules.yaml`) y overlay (`best_params_2H.json`).
    - `report/topk_freeze_2H.json` guarda la traza de selección.
4. **CI Smoke Test**:
    - Workflow `.github/workflows/e2e_smoke_2J.yml` ejecuta el runner en cada push/PR para evitar regresiones.
5. **Política Python 3.12**:
    - Estandarizado Python 3.12.x para desarrollo local (WSL) y CI.

## 2. Ejecución Local (Windows/WSL)

El método canónico de ejecución es via WSL para garantizar paridad con CI.

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_e2e_2J.py --outdir report/runs/2J_e2e_synth"
```

### Outputs Esperados

Tras una ejecución exitosa (`PASS`), se generan:

- `configs/risk_rules_prod.yaml`: Configuración final de riesgo.
- `configs/best_params_2H.json`: Parámetros congelados (TOP-1).
- `report/dashboard_2J/index.html`: Dashboard visual estático.
- `report/runs/2J_e2e_synth/`: Logs y CSVs de la calibración.

## 3. Checklist Previo a 3A (Orchestrator Real-Time)

La fase 3A iniciará la orquestación en tiempo real ("Paper Trading / Live Loop").

- [ ] **Contratos Event-Driven**: Definir eventos `MarketData`, `RiskCheck` para el bucle en vivo.
- [ ] **Wiring Paper Loop**: Conectar `SimpleBacktester` (o nuevo `LiveRunner`) a feeds simulados.
- [ ] **Observabilidad**: Logs estructurados para latencia y healthchecks.
- [ ] **Inyección de Config**: Cargar `risk_rules_prod.yaml` al inicio del proceso 3A.

## 4. Referencias

- **Runner Source**: [tools/run_e2e_2J.py](tools/run_e2e_2J.py)
- **CI Workflow**: [.github/workflows/e2e_smoke_2J.yml](.github/workflows/e2e_smoke_2J.yml)
- **Decision Log**: `.ai/decisions_log.md` (Política Python 3.12)
