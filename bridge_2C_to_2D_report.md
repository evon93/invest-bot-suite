# Bridge Report: 2C → 2D

**Fecha:** 2025-12-26  
**Autor:** Antigravity  
**Rama:** `main`  
**HEAD:** `3c3d74b`

---

## Resumen de Fase 2C

### Objetivo cumplido

Aplicar los mejores parámetros de calibración (de `report/calibration_2B/topk.json`) a `risk_rules.yaml` de forma automatizada, validada y trazable.

### Implementaciones principales

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| Schema/Selector | `tools/best_params_schema_2C.py` | Validación de topk.json + selección determinista |
| Builder CLI | `tools/build_best_params_2C.py` | Genera `configs/best_params_2C.json` |
| Apply CLI | `tools/apply_calibration_topk.py` | Aplica params a risk_rules.yaml |
| Tests | `tests/test_best_params_2C.py` | 12 tests para schema/builder |
| Tests | `tests/test_apply_calibration_topk_2C.py` | 8 tests para apply tool |
| Conftest | `tests/conftest.py` | Fix pytest import path (Windows) |

### Parámetros aplicados

| Path | Valor original | Valor calibrado |
|------|----------------|-----------------|
| `stop_loss.atr_multiplier` | 2.5 | **2.0** |
| `max_drawdown.hard_limit_pct` | 0.08 | **0.1** |
| `kelly.cap_factor` | 0.50 | **0.7** |

---

## Artefactos clave

### Configuración generada
- `configs/best_params_2C.json` — Parámetros seleccionados con metadata
- `risk_rules_candidate.yaml` — Config candidata (promovida a risk_rules.yaml)

### Reports de fase 2C
| Report | Contenido |
|--------|-----------|
| `report/AG-2C-4-1A_return.md` | Schema + builder implementation |
| `report/AG-2C-5-1A_return.md` | Apply tool + candidate + patch |
| `report/AG-2C-6-1A_return.md` | Validación + idempotencia |
| `report/AG-2C-7-1A_return.md` | Promoción a risk_rules.yaml |
| `report/AG-2C-10-2A_return.md` | Fix pytest conftest |

### Hygiene EOL
| Report | Contenido |
|--------|-----------|
| `report/AG-H0-13-2RENORM_return.md` | Renormalización EOL (48 archivos) |
| `report/AG-H0-13-2MERGE_return.md` | Merge a main |

---

## Commits relevantes

| Hash | Mensaje |
|------|---------|
| `c48c6b6` | 2C: baseline evidence |
| `c494dc9` | 2C: best_params contract + validator + tests |
| `f0e3120` | 2C: apply best params (candidate + patch) |
| `5c90685` | 2C: promote calibrated risk_rules |
| `3c3d74b` | H0: renormalize line endings (LF) |

---

## Known pitfalls

### Windows: pytest entrypoint vs module

```powershell
# ❌ Puede fallar en Windows (path issues con .venv)
pytest -q

# ✅ Forma recomendada
python -m pytest -q
```

El `tests/conftest.py` añade el repo root a `sys.path`, pero el entrypoint `pytest.exe` puede tener problemas con PowerShell y el directorio `.venv`.

---

## Siguientes pasos: Fase 2D

### 1. Runner/Backtests ampliados
- Ejecutar backtests con los nuevos parámetros calibrados
- Comparar métricas antes/después de calibración
- Validar que no hay regresión en performance

### 2. Criterios de selección mejorados
- Considerar métricas adicionales en el scoring (win_rate, pct_time_hard_stop)
- Implementar validación cruzada temporal (out-of-sample)
- Añadir circuit breakers más sofisticados

### 3. Reporting automatizado
- Dashboard de comparación de parámetros
- Alertas si las métricas calibradas están fuera de rangos esperados
- Integración con CI para validar parámetros en cada PR

### 4. Deploy/Producción
- Definir proceso de promoción de parámetros a producción
- Rollback automático si hay anomalías
- Logging de decisiones del risk manager con nuevos params

---

## Estado de tests

```
77 passed in ~1.3s
validate_risk_config: 0 errors, 0 warnings
```
