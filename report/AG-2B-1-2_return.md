# Return Packet — AG-2B-1-2

**Ticket**: AG-2B-1-2 — Estructuras para closed_trades  
**Fecha**: 2025-12-23T19:35

## Cambios Realizados

### [backtest_initial.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/backtest_initial.py)

**Import añadido** (L12):
```python
from collections import defaultdict
```

**Estructuras añadidas en `__init__`** (L83-L84):
```python
self.closed_trades: List[Dict] = []  # Trades cerrados con PnL
self._avg_cost: Dict[str, float] = defaultdict(float)  # Coste medio por asset
```

## Verificación

```
pytest -q → 52 passed in 2.23s
```

✅ `self.trades` no modificado, compatibilidad mantenida.

## Artefactos DoD

- [x] `report/AG-2B-1-2_return.md` (este archivo)
- [x] `report/AG-2B-1-2_diff.patch`
- [x] `report/AG-2B-1-2_pytest.txt`
