# Bridge Report: 2B → 2E (Full Calibration Gate Useful)

**Fecha**: 2025-12-28  
**Branch origen**: `feature/2B_risk_calibration`  
**Branch destino**: `feature/2E_full_gate_useful`  
**Commit**: `0611785`

---

## Problema

En 2B, el runner de calibración ejecutaba todas las combinaciones pero **no detectaba escenarios inactivos** (0 trades). Esto causaba **false negatives**:
- Combinaciones con `num_trades=0` aparecían como "OK" cuando en realidad no generaban actividad.
- El 66.7% de las combinaciones en full mode producían 0 trades debido a `kelly.cap_factor < 0.7`.

---

## Solución 2E

### 1. Semántica ACTIVE/INACTIVE
- `is_active = num_trades > 0`
- Columnas de diagnóstico (fallback): `rejection_other=1` cuando `num_trades=0`

### 2. Activity Gate
Evalúa si hay suficientes escenarios activos:
```yaml
profiles.full.activity_gate:
  min_active_n: 20           # mínimo de escenarios con trades
  min_active_rate: 0.60      # mínimo 60% activos
  min_active_pass_rate: 0.70 # de los activos, 70% deben pasar quality
```

Si `active_n < min_active_n` AND `active_rate < min_active_rate` → `insufficient_activity=true`

### 3. Quality Gate
Aplicado solo a escenarios activos:
```yaml
profiles.full.quality_gate:
  min_trades: 1
  min_sharpe: 0.3
  min_cagr: 0.05
  max_drawdown_absolute: -0.25
```

### 4. Flag --strict-gate
- Default: exit 0 siempre, artefactos generados, `gate_passed` en meta
- Con `--strict-gate --mode full`: exit 1 si gate falla

---

## Rutas y Comandos

### Archivos modificados
- `configs/risk_calibration_2B.yaml` — profiles con gates
- `tools/run_calibration_2B.py` — columnas, lógica gates, flag
- `tests/test_calibration_runner_2B.py` — 5 tests

### Comandos reproducibles
```bash
# Quick (sin gates)
python tools/run_calibration_2B.py --mode quick

# Full (con gates, silencioso)
python tools/run_calibration_2B.py --mode full

# Full estricto (exit 1 si gate falla)
python tools/run_calibration_2B.py --mode full --strict-gate

# Verificar
python -m pytest tests/test_calibration_runner_2B.py -v
```

### Output esperado (full mode)
```
GATE full: FAIL | active_n=13 active_rate=32.50% active_pass_rate=100.00% reasons=[insufficient_activity]
```

---

## Artefactos

- `report/AG-2E-2-1_return.md` — reporte de implementación
- `report/AG-2E-1-2-extract_return.md` — análisis de 0-trade
- `report/out_2E_2_1_full_smoke/run_meta.json` — ejemplo con campos de gate
