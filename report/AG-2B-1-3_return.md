# Return Packet — AG-2B-1-3

**Ticket**: AG-2B-1-3 — Instrumentar closed_trades con PnL  
**Fecha**: 2025-12-23T19:40

## Cambios Realizados

### [backtest_initial.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/backtest_initial.py) — `_rebalance()` L145-205

**Lógica añadida** (antes de actualizar `self.positions`):

```python
prev_shares = self.positions.get(asset, 0)
shares_delta = target_shares - prev_shares

# --- Tracking de avg_cost y closed_trades (long-only) ---
if shares_delta > 0:
    # Compra: apertura o scale-in
    if prev_shares == 0:
        self._avg_cost[asset] = price
    else:
        # Scale-in: avg_cost ponderado
        total_cost = self._avg_cost[asset] * prev_shares + price * shares_delta
        self._avg_cost[asset] = total_cost / target_shares
        
elif shares_delta < 0 and prev_shares > 0:
    # Venta: cierre parcial o total
    closed_qty = min(abs(shares_delta), prev_shares)
    entry_cost = self._avg_cost[asset]
    realized_pnl = (price - entry_cost) * closed_qty
    
    self.closed_trades.append({
        "date": date,
        "asset": asset,
        "qty": closed_qty,
        "entry_cost": entry_cost,
        "exit_price": price,
        "realized_pnl": realized_pnl,
    })
    
    if target_shares == 0:
        self._avg_cost[asset] = 0.0
```

**Notas**:
- Sistema asume **long-only** (shares >= 0)
- `self.trades` no modificado (mismo formato)
- `self.closed_trades` contiene trades cerrados con PnL

## Verificación

```
pytest -q → 52 passed in 0.46s
```

## Artefactos DoD

- [x] `report/AG-2B-1-3_return.md` (este archivo)
- [x] `report/AG-2B-1-3_diff.patch`
- [x] `report/AG-2B-1-3_pytest.txt`
