# Return Packet — AG-2B-3-3C

**Ticket**: AG-2B-3-3C — score_formula + runner smoke test  
**Fecha**: 2025-12-23T21:38

## Paso 3.3: score_formula

**Snippet** (configs/risk_calibration_2B.yaml L78):
```yaml
formula: "1.0*sharpe_ratio + 0.5*cagr - 1.5*abs(max_drawdown)"
```

**Cambio en** `compute_score()` — ahora incluye:
```python
"win_rate": float(row.get("win_rate", 0) or 0),
"gross_pnl": float(row.get("gross_pnl", 0) or 0),
"atr_stop_count": int(row.get("atr_stop_count", 0) or 0),
"hard_stop_trigger_count": int(row.get("hard_stop_trigger_count", 0) or 0),
"pct_time_hard_stop": float(row.get("pct_time_hard_stop", 0) or 0),
```

**Compatibilidad**: La fórmula actual no usa nuevas métricas → comportamiento sin cambios. Si se actualiza la fórmula, las métricas están disponibles.

## Paso 4.1: runner smoke test

**Archivo creado**: `tests/test_calibration_runner_2B.py`

**CLI añadido**: `--output-dir` (prioridad: CLI > YAML > default)

**Test verifica**:
- 5 artefactos existen
- results.csv tiene columnas nuevas
- topk.json es JSON válido
- run_meta.json tiene campos requeridos

## Bug corregido

`run_meta.json` usaba `output_dir_rel` que ya no existía cuando se usaba `--output-dir`. Corregido a `output_dir`.

## Comando Reproducible

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
# Con output dir custom:
python tools/run_calibration_2B.py --mode quick --max-combinations 2 --seed 42 --output-dir /tmp/test_output
```

## output.dir

```
report/calibration_2B (default)
o CLI --output-dir
```

## Verificación

```
pytest -q → 57 passed ✅
smoke test → 3 ok, 0 errors ✅
```

## Artefactos DoD

- [x] `report/AG-2B-3-3C_return.md` (este archivo)
- [x] `report/AG-2B-3-3C_diff.patch`
- [x] `report/AG-2B-3-3C_pytest.txt`
- [x] `report/AG-2B-3-3C_run.txt`
