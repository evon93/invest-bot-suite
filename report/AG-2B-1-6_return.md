# Return Packet — AG-2B-1-6

**Ticket**: AG-2B-1-6 — Consolidar commit Paso 1  
**Fecha**: 2025-12-23T20:09

## Commit Realizado

```
23d301a 2B.1: closed_trades + win_rate metrics for calibration
```

**28 archivos**, 1041 inserciones, 25 eliminaciones

### Archivos principales:
- `backtest_initial.py` — closed_trades, _avg_cost, instrumentación _rebalance
- `tests/test_backtester_closed_trades.py` — 4 tests nuevos
- `tools/run_calibration_2B.py` — métricas win_rate, gross_pnl, etc.

## Push

⚠️ Push falló por permisos SSH (`Permission denied (publickey)`).
El commit está en el repo local. Push manual requerido:

```bash
git push origin feature/2B_risk_calibration
```

## Comando Reproducible

```bash
# Verificar estado
git log -1 --oneline
# → 23d301a 2B.1: closed_trades + win_rate metrics for calibration

# Ejecutar calibración
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```

## Artefactos DoD

- [x] `report/AG-2B-1-6_return.md` (este archivo)
- [x] `report/AG-2B-1-6_last_commit.txt`
- [x] `report/AG-2B-1-6_status.txt`
