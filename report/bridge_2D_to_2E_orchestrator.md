# 2D Parameter Robustness — Informe de Traspaso para Orchestrator

**Fecha:** 2025-12-27  
**Rama:** `feature/2D_param_robustness`  
**Commits:** `af969e8` → `f663e18` (9 commits)

---

## Resumen Ejecutivo

- ✅ **Contrato 2D implementado**: YAML + spec + validator + tests
- ✅ **Runner funcional**: `tools/run_robustness_2D.py` con CLI
- ✅ **Gates por modo**: `quick` (sanity) vs `full` (quality)
- ✅ **CI workflow**: `.github/workflows/robustness_quick.yml`
- ✅ **114 tests pasan** (77 originales + 37 nuevos para 2D)
- ⚠️ **Limitación conocida**: ~50% escenarios con 0 trades en full (señal sintética débil)

---

## Artefactos Clave

| Path | Descripción |
|------|-------------|
| `configs/robustness_2D.yaml` | Contrato YAML para runner |
| `report/robustness_2D_spec.md` | Especificación técnica |
| `tools/run_robustness_2D.py` | Runner CLI |
| `tools/validate_robustness_2D_config.py` | Validator de config |
| `.github/workflows/robustness_quick.yml` | CI workflow |
| `report/external_ai/2D_02_2.1/*.pdf` | PDFs externos normalizados |

---

## Cómo Ejecutar

### Quick Mode (sanity check)
```bash
# PowerShell
python tools/run_robustness_2D.py --mode quick --max-scenarios 20

# WSL
source .venv/bin/activate
python tools/run_robustness_2D.py --mode quick
```

### Full Mode (quality gate)
```bash
python tools/run_robustness_2D.py --mode full --max-scenarios 100
```

### Outputs
```
report/robustness_2D/
├── results.csv       # Resultados por escenario
├── summary.md        # Resumen con top-10
├── run_meta.json     # Metadatos (pass_rate, gates_profile, etc.)
└── errors.jsonl      # Errores si los hay
```

---

## Gates Activos

| Modo | Gate | Valor |
|------|------|-------|
| **quick** | max_drawdown_absolute | -0.50 (muy laxo) |
| **quick** | min_trades | 0 (permite 0 trades) |
| **quick** | min_sharpe/cagr | NO APLICA |
| **full** | max_drawdown_absolute | -0.15 |
| **full** | min_sharpe | 0.3 |
| **full** | min_cagr | 0.05 |
| **full** | min_trades | 1 |

---

## Interpretación Resultados Actuales

| Modo | Pass Rate | Nota |
|------|-----------|------|
| **quick** | 100% | ✅ Sanity OK (0 errores, candidate aplicado) |
| **full** | ~10-20% | ⚠️ Quality gate estricto, muchos fallan sharpe/cagr |

**Causa raíz:** La señal sintética (`generate_synthetic_prices`) es demasiado débil/aleatoria, resultando en ~50% escenarios con 0 trades.

---

## Riesgos Abiertos

1. **50% escenarios con 0 trades** — señal no genera suficientes oportunidades
2. **Pass rate full bajo** — gates pueden ser demasiado estrictos para datos sintéticos
3. **Sin rejection reasons stats** — difícil diagnosticar por qué no se abre posición
4. **Workflow `robustness_full` no existe** — solo quick está en CI

---

## Next Steps (Backlog Priorizado)

| # | Acción | Impacto |
|---|--------|---------|
| 1 | **Mejorar señal/dataset** — usar datos reales o señal más agresiva | ALTO |
| 2 | **Añadir workflow `robustness_full`** — dispatch manual, max_scenarios=100 | MEDIO |
| 3 | **Agregar rejection_reasons_stats** — instrumentar backtester | MEDIO |
| 4 | **Calibrar gates full** — ajustar thresholds si procede tras mejora señal | BAJO |
| 5 | **PR a main** — merge feature/2D_param_robustness cuando estabilice | FINAL |

---

## Commits de Referencia

```
f663e18 docs(report): add AG-2D-03-3.7A return artifacts
21cba10 ci: add robustness_quick workflow + gitignore report/runs
d071b78 docs(report): add AG-2D-03-3.4A return artifacts
9adb5bd feat(runner): gates by mode (quick=sanity, full=quality) + num_trades metric
34a6df4 docs(report): add AG-2D-03-3.2A return artifacts
2801f47 fix(runner): extract_params_dotted handles params_dotted and nested params
32a1196 docs(report): add AG-2D-03-3.1 return artifacts
3cc98c2 2D: robustness runner + smoke tests (103 tests pass)
af969e8 2D: robustness contract (YAML+spec+validator+tests+PDFs)
```

---

## Validación Rápida

```bash
# Pytest
python -m pytest -q
# => 114 passed

# Validator
python tools/validate_robustness_2D_config.py
# => VALIDATION PASSED

# Quick smoke
python tools/run_robustness_2D.py --mode quick --max-scenarios 2
# => pass_rate 100%
```
