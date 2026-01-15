# Return Packet — AG-2B-1-4

**Ticket**: AG-2B-1-4 — Test unitario closed_trades  
**Fecha**: 2025-12-23T19:47

## Archivo Creado

### [test_backtester_closed_trades.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_backtester_closed_trades.py)

**4 tests**:

| Test | Escenario | Verificación |
|------|-----------|--------------|
| `test_closed_trade_profit` | Compra 100, vende 110 | `realized_pnl = +100` |
| `test_closed_trade_loss` | Compra 100, vende 90 | `realized_pnl = -100` |
| `test_scale_in_updates_avg_cost` | Compra 5 @ 100, 5 @ 120 | `avg_cost` entre 100-120 |
| `test_partial_close` | Compra 10, vende 5 | `qty = 5`, `pnl = 50` |

## Snippet Principal

```python
def test_closed_trade_profit(self):
    dates = pd.date_range("2024-01-02", periods=2, freq="D")
    prices = pd.DataFrame({"AAA": [100.0, 110.0]}, index=dates)
    
    bt = SimpleBacktester(prices, initial_capital=1000)
    bt.target_weights = {"AAA": 1.0}
    bt.last_valid_prices["AAA"] = 100.0
    bt.portfolio_value = [1000.0]
    
    bt._rebalance(dates[0])  # Compra 10 shares
    
    bt.target_weights = {"AAA": 0.0}
    bt.last_valid_prices["AAA"] = 110.0
    bt.portfolio_value.append(1100.0)
    bt._rebalance(dates[1])  # Vende 10 shares
    
    assert len(bt.closed_trades) == 1
    assert bt.closed_trades[0]["realized_pnl"] == pytest.approx(100.0)
```

## Verificación

```
pytest tests/test_backtester_closed_trades.py -v → 4 passed
pytest -q (global) → 56 passed
```

## Artefactos DoD

- [x] `report/AG-2B-1-4_return.md` (este archivo)
- [x] `report/AG-2B-1-4_diff.patch`
