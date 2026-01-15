# Return Packet — AG-2B-1-5

**Ticket**: AG-2B-1-5 — Métricas de closed_trades en calibración  
**Fecha**: 2025-12-23T20:05

## Cambios Realizados

### [run_calibration_2B.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_calibration_2B.py)

**Función `run_single_backtest`** (L134-157):
```python
# --- Métricas de closed_trades (win_rate, PnL) ---
ct = bt.closed_trades
closed_count = len(ct)
wins = [t["realized_pnl"] for t in ct if t["realized_pnl"] > 0]
losses = [t["realized_pnl"] for t in ct if t["realized_pnl"] < 0]

metrics["closed_trades_count"] = closed_count
metrics["wins_count"] = len(wins)
metrics["losses_count"] = len(losses)
metrics["win_rate"] = len(wins) / closed_count if closed_count > 0 else 0.0
metrics["gross_pnl"] = sum(t["realized_pnl"] for t in ct)
metrics["avg_win"] = sum(wins) / len(wins) if wins else 0.0
metrics["avg_loss"] = sum(losses) / len(losses) if losses else 0.0
```

**CSV Headers** (L252-258):
- Añadidas 7 columnas: `closed_trades_count`, `wins_count`, `losses_count`, `win_rate`, `gross_pnl`, `avg_win`, `avg_loss`

## Verificación

```
pytest -q → 56 passed ✅
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42 → 3 ok, 0 errors ✅
```

**Artifacts en `report/calibration_2B/`**:
- `results.csv` — incluye nuevas columnas
- `summary.md`, `topk.json`, `run_meta.json`, `run_log.txt`

## Artefactos DoD

- [x] `report/AG-2B-1-5_return.md` (este archivo)
- [x] `report/AG-2B-1-5_diff.patch`
- [x] `report/AG-2B-1-5_pytest.txt`
- [x] `report/AG-2B-1-5_run.txt`
