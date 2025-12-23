# Return Packet — AG-2B-2-1B

**Ticket**: AG-2B-2-1B — risk_decision por tick + contadores ATR/hard_stop  
**Fecha**: 2025-12-23T21:15

## Inspección Callsite

**Archivo**: [backtest_initial.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/backtest_initial.py)  
**Líneas**: L132-L148 (dentro de `_rebalance`)

```python
allow, annotated = risk_manager.filter_signal(
    {"deltas": deltas, "assets": list(self.prices.columns)},
    current_w,
    nav,
    equity_curve=equity_curve,
    dd_cfg=dd_cfg,
    atr_ctx={},
    last_prices=self.last_valid_prices,
)

# Capturar risk_decision para métricas (ruta 2.2)
risk_decision = annotated.get("risk_decision", {})
self.risk_events.append({
    "date": date,
    "risk_decision": risk_decision,
})
```

## Ruta Tomada

**Ruta 2.2** (preferida): `annotated["risk_decision"]` ya existía en el retorno de `filter_signal`.

**Razón**: No fue necesario modificar `RiskManagerV05` (fallback 2.3). Los tests existentes confirman que `annotated["risk_decision"]` contiene:
- `reasons` (incluye `"dd_hard"`, `"stop_loss_atr"`)
- `force_close_positions`, `stop_signals`

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `backtest_initial.py` | +`self.risk_events` en `__init__`, captura `risk_decision` en `_rebalance` |
| `tools/run_calibration_2B.py` | +contadores ATR/hard_stop en `run_single_backtest`, +4 columnas CSV |

## Comando Reproducible

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```

## output.dir y Artefactos

```
output.dir = report/calibration_2B
```

**results.csv nuevas columnas**:
- `atr_stop_count`
- `hard_stop_trigger_count`
- `pct_time_hard_stop`
- `missing_risk_events`

## Verificación

```
pytest -q → 56 passed ✅
smoke test → 3 ok, 0 errors ✅
```

## Artefactos DoD

- [x] `report/AG-2B-2-1B_return.md` (este archivo)
- [x] `report/AG-2B-2-1B_diff.patch`
- [x] `report/AG-2B-2-1B_pytest.txt`
- [x] `report/AG-2B-2-1B_run.txt`
