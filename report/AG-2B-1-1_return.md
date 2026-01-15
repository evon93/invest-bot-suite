# Return Packet — AG-2B-1-1

**Ticket**: AG-2B-1-1 — Inspección `backtest_initial.py` para instrumentación closed_trades  
**Fecha**: 2025-12-23T19:10

## Path del Archivo

```
backtest_initial.py   (raíz del repo)
```

---

## A) class SimpleBacktester

**Líneas**: L64-L230

```python
class SimpleBacktester:
    """Backtester con rebalanceo mensual; acepta Series o DataFrame."""
```

---

## B) __init__ — Estructuras actuales

**Líneas**: L67-L96

```python
def __init__(
    self, prices: Union[pd.Series, pd.DataFrame], initial_capital: float = 10_000
):
    # Normalizar formato
    if isinstance(prices, pd.Series):
        self.prices = prices.to_frame(name=prices.name or "ASSET")
        self.single_asset = True
    else:
        self.prices = prices
        self.single_asset = False

    # Estado
    self.initial_capital = initial_capital
    self.portfolio_value: List[float] = [initial_capital]
    self.positions: Dict[str, float] = {c: 0.0 for c in self.prices.columns}
    self.trades: List[Dict] = []                         # ← AQUÍ: lista de trades
    
    # Precios efectivos (último precio válido > 0 visto)
    self.last_valid_prices: Dict[str, float] = {}

    # Pesos objetivo
    if self.single_asset:
        self.target_weights = {self.prices.columns[0]: 1.0}
    else:
        self.target_weights = {
            "ETF": 0.60,
            "CRYPTO_BTC": 0.08,
            "CRYPTO_ETH": 0.04,
            "BONDS": 0.28,
        }
```

**Estructuras clave:**
| Campo | Tipo | Uso |
|-------|------|-----|
| `self.positions` | `Dict[str, float]` | Acciones actuales por asset |
| `self.trades` | `List[Dict]` | Log de trades (append) |
| `self.portfolio_value` | `List[float]` | Equity curve |
| `self.last_valid_prices` | `Dict[str, float]` | Último precio válido |

---

## C) run() — Loop principal

**Líneas**: L175-L230

```python
def run(self, risk_manager=None) -> pd.DataFrame:
    if self.prices.empty:
        return pd.DataFrame()

    first_date = self.prices.index[0]
    
    # Inicializar precios válidos
    for asset in self.prices.columns:
        p = self.prices.loc[first_date, asset]
        if p > 0:
            self.last_valid_prices[asset] = p

    # Rebalanceo inicial: SOLO si es día hábil
    if first_date.weekday() < 5:
        self._rebalance(first_date, risk_manager)

    records: List[Dict] = []
    self.portfolio_value = [] 

    for date in self.prices.index:           # ← LOOP POR DÍA
        # 1. Actualizar precios efectivos
        for asset in self.prices.columns:    # ← LOOP POR ASSET (interno)
            p = self.prices.loc[date, asset]
            if p > 0:
                self.last_valid_prices[asset] = p
        
        # 2. Calcular valor del portafolio
        pv = sum(
            self.positions.get(a, 0) * self.last_valid_prices.get(a, 0)
            for a in self.prices.columns
        )
        ...
        # 3. Lógica de Rebalanceo (llama a _rebalance)
```

---

## D) self.trades.append({...}) — Registro de trades

**Líneas**: L163-L170 (dentro de `_rebalance`)

```python
                self.trades.append(
                    {
                        "date": date,
                        "asset": asset,
                        "shares": shares_delta,
                        "price": price,
                    }
                )
```

**Observación**: El trade actual NO incluye campos de `closed_trade` (entry_price, exit_price, pnl, etc.). Solo registra el delta de shares.

---

## E) shares_delta y actualización de posición/caja

**Líneas**: L142-L170 (dentro de `_rebalance`)

```python
        for asset, delta in deltas.items():
            # Usar precio efectivo
            price = self.last_valid_prices.get(asset, 0)
            if price <= 0:
                continue  # No podemos operar sin precio válido

            target_val = self.target_weights.get(asset, 0) * nav
            target_shares = target_val / price
            shares_delta = target_shares - self.positions.get(asset, 0)  # ← CÁLCULO
            
            # Registrar trade si hay cambio...
            if shares_delta != 0 or abs(delta) < 0.01:
                # Actualizar posición solo si cambia
                if shares_delta != 0:
                    self.positions[asset] = target_shares              # ← UPDATE POSICIÓN
                
                # Siempre registrar en el log de trades
                self.trades.append(...)
```

**Observación**: No hay "caja" explícita (cash tracking). El sistema es fully-invested y usa `nav` calculado desde `portfolio_value`.

---

## F) Funciones helper para fills/ejecución

| Función | Líneas | Descripción |
|---------|--------|-------------|
| `_current_weights()` | L101-L108 | Calcula pesos actuales desde posiciones |
| `_rebalance()` | L110-L170 | Ejecuta rebalanceo: calcula deltas, filtra por RiskManager, actualiza posiciones, registra trades |

**No hay** función separada de `execute_fill()` o similar. Todo se hace inline en `_rebalance()`.

---

## Puntos clave para instrumentación de closed_trades

1. **Lugar para detectar "cierre"**: L150-L158 dentro del loop de `_rebalance`
   ```python
   shares_delta = target_shares - self.positions.get(asset, 0)
   ```
   - Si `shares_delta < 0` → reducción de posición (venta parcial/total)
   - Si `self.positions[asset] > 0` y `target_shares == 0` → cierre completo

2. **Información disponible en ese punto**:
   - `asset`, `date`, `price` (exit price)
   - `self.positions[asset]` (shares antes del cambio)
   - `shares_delta` (cantidad vendida)
   - **Falta**: `entry_price` (no se guarda actualmente)

3. **Cambio sugerido para 1.2/1.3**:
   - Agregar `self.open_positions: Dict[str, Dict]` con `{asset: {shares, entry_price, entry_date}}`
   - En L158 (antes de actualizar), si `shares_delta < 0`, calcular PnL y agregar a `self.closed_trades`
