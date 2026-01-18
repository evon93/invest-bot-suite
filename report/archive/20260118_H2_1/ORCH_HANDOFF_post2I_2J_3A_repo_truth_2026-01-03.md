# Orchestrator Handoff: Post-Pulse 2J & 3A

**Date**: 2026-01-03
**Scope**: Phase 2J (E2E Pipeline) + Phase 3A (Paper Trading Loop)
**Target**: Orchestrator (Ivan)

## 1. Repo Truth

- **Branch**: `main`
- **HEAD**: `e96ad18` (3A.5: bridge 3A to 3B (docs))
- **Status**: Clean (except uncommited reports).
- **Python**: 3.12.x (Standardized via `fc02e41`).

## 2. Executive Summary

Se ha completado la **Fase 2J**, entregando un pipeline canónico (`tools/run_e2e_2J.py`) que orquesta calibración, freeze, renderizado y validación de riesgo.
Se ha completado la **Fase 3A**, entregando la infraestructura de simulación (`tools/run_paper_loop_3A.py`) basada en contratos de eventos y observabilidad básica.

El sistema está listo para iniciar la **Fase 3B** (Integración Live/Real Data) sobre una base sólida y testada en CI.

## 3. Commit Manifest (2J + 3A)

| ID | Hash | Message | Feature |
|----|------|---------|---------|
| **3A.5** | `e96ad18` | bridge 3A to 3B (docs) | Cierre de fase 3A, docs finales. |
| **3A.3.2** | `95745b2` | harden rejection reason aggregation + alias | Hardening observability (aliases, P95). |
| **3A.3** | `f3e8f57` | observability metrics (drawdown...) | Métricas financieras y operativas. |
| **3A.2** | `a17e9df` | paper trading loop simulator (events+metrics) | Runner de simulación 3A. |
| **3A.1** | `24beab7` | event-driven contracts v1 (+ docs/tests) | Definición `OrderIntent`, `RiskDecision`. |
| **2J.5** | `0bf352c` | bridge 2J to 3A (docs) | Cierre de fase 2J. |
| **2J.4** | `fc02e41` | standardize python 3.12 version policy | Política de versiones. |
| **2J.3** | `b06edb6` | add e2e_smoke workflow for canonical runner | CI GitHub Actions. |
| **2J.1** | `2769633` | add canonical E2E synth runner | Script `run_e2e_2J.py` + strict validation. |

## 4. Cómo Reproducir (WSL + .venv)

### 4.1. E2E Pipeline (2J)

Ejecuta todo el ciclo (Calibration -> Validation -> Dashboard).

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_e2e_2J.py --mode quick"
```

*Artifacts*: `report/out_2J_e2e_run/`

### 4.2. Paper Trading Loop (3A)

Ejecuta el simulador con señales de ejemplo.

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_paper_loop_3A.py --signals examples/signals_3A.ndjson --risk-config configs/risk_rules_prod.yaml --outdir report/runs/3A_handover_test"
```

*Artifacts*: `report/runs/3A_handover_test/metrics.json`

### 4.3. Tests

```bash
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && pytest -q"
```

## 5. Riesgos y Pendientes

- **Data Real**: 3A funciona con señales sintéticas (`examples/signals_3A.ndjson`). No hay adaptador de precios live aún.
- **Reason Semantics**: `rejected_by_reason` agrupa strings. Si el upstream cambia los mensajes de error, las métricas pueden fragmentarse.
- **Latencia Artificial**: La latencia reportada es simulada por el mock. La latencia real de red/broker no se mide aún.

## 6. Propuesta Fase 3B (Live Integration)

1. **Data Adapter**: Implementar ingestión de precios históricos/live (CSV/API).
2. **Strategy Engine Wiring**: Conectar el generador de señales real al bus de eventos `OrderIntent`.
3. **Real Execution Adapter**: Implementar `Exchange` stub más realista o conector IBKR/CCXT.
4. **E2E Smoke 3B**: Test de integración que cubra Data -> Signal -> Risk -> Execution.

## 7. Verificación de Estado

```bash
$> git status -sb
## main...origin/main [ahead 25]
?? report/ORCH_HANDOFF_post2I_2J_3A_repo_truth_2026-01-03.md
```
