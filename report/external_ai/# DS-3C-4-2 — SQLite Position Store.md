# DS-3C-4-2 — SQLite Position Store Hardening

## Executive Summary
La implementación actual tiene **4 bugs críticos** en la semántica de shorts y cruces. Se propone un fix minimalista (≤100 líneas) que corrige: (1) avg_price incorrecto en aumentos de short, (2) avg_price incorrecto en cruces, (3) falta de atomicidad, y (4) serialización no determinista. Los cambios mantienen compatibilidad con tests existentes excepto 2 tests que reflejan comportamiento incorrecto previo.

---

## Findings (P1..P4)

### P1: Avg_price incorrecto en aumentos de posición short
**Ubicación**: `apply_fill()`, líneas 157-195  
**Bug**: Cuando se aumenta una posición short existente (`current_qty < 0`, `side == "SELL"`), el código actual **no recalcula avg_price** (mantiene el anterior).  
**Ejemplo**: Short -1.0 @ 80 → SELL 1.0 @ 75. Resultado esperado: -2.0 @ 77.5. Actual: -2.0 @ 80 (incorrecto).

### P2: Avg_price incorrecto en cruces long↔short
**Bug**: Al cruzar de long a short (ej: long 1.0 → SELL 2.0), mantiene el avg_price del long para el nuevo short.  
**Ejemplo**: Long 1.0 @ 100 → SELL 2.0 @ 90. Resultado esperado: short -1.0 @ 90. Actual: short -1.0 @ 100 (incorrecto).

### P3: Operación no atómica
**Bug**: `apply_fill` realiza `get_position()` → cálculo → `upsert_position()` sin transacción. Si falla después del get, estado queda inconsistente.

### P4: Serialización JSON no determinista
**Bug**: `json.dumps(meta)` sin `sort_keys=True` produce strings diferentes para mismos dicts con distinto orden de keys.

---

## Proposed Semantics (invariantes)

### Reglas de `apply_fill(symbol, side, qty, price)`:

1. **Delta de posición**:  
   `delta = +qty` si `side == "BUY"`, `delta = -qty` si `side == "SELL"`  
   `new_qty = current_qty + delta`

2. **Cálculo de avg_price**:
   ```
   Si current_qty == 0:
       new_avg = price
   Si mismo signo (current_qty * new_qty > 0):
       Si |new_qty| > |current_qty|:  # Aumentar posición
           new_avg = (|current_qty|*current_avg + qty*price) / |new_qty|
       Si no:  # Reducir posición (partial cover/partial sell)
           new_avg = current_avg  # Se mantiene
   Si signos diferentes (cruce):
       new_avg = price  # Precio de la operación que cruza
   ```

3. **Cierre exacto**: Si `abs(new_qty) < 1e-10`, eliminar fila, retornar `{"closed": True}`

4. **Validaciones**:
   - `qty > 0`
   - `price > 0`
   - `side in ("BUY", "SELL")` (case-insensitive)
   - `symbol` no vacío

---

## Patch Sketch / Diff Orientativo

```diff
--- a/state/position_store_sqlite.py
+++ b/state/position_store_sqlite.py
@@ -119,7 +119,7 @@ class PositionStoreSQLite:
         """
         conn = self._get_connection()
         now = datetime.now(timezone.utc).isoformat()
-        meta_json = json.dumps(meta) if meta else None
+        meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':')) if meta else None
         
         conn.execute(
             """
@@ -141,6 +141,21 @@ class PositionStoreSQLite:
     def __exit__(self, exc_type, exc_val, exc_tb) -> None:
         self.close()
 
+    def _compute_new_avg_price(
+        self, current_qty: float, current_avg: Optional[float], 
+        delta_qty: float, delta_price: float, new_qty: float
+    ) -> Optional[float]:
+        """Compute new average price following cross/same-sign rules."""
+        if abs(current_qty) < 1e-10 or current_avg is None:
+            return delta_price
+        
+        if current_qty * new_qty > 0:  # Same sign
+            if abs(new_qty) > abs(current_qty):  # Increasing position
+                return (abs(current_qty) * current_avg + delta_qty * delta_price) / abs(new_qty)
+            return current_avg  # Decreasing position (keep avg)
+        else:  # Crossing zero
+            return delta_price
+
     # -------------------------------------------------------------------------
     # Position CRUD
     # -------------------------------------------------------------------------
@@ -183,50 +198,57 @@ class PositionStoreSQLite:
         self,
         symbol: str,
         side: str,
         qty: float,
         price: float,
     ) -> Dict[str, Any]:
         """
         Apply a fill to update position.
         
         BUY: Increases position, recalculates avg_price
         SELL: Decreases position (closes if qty matches)
         
         Args:
             symbol: Asset symbol
             side: "BUY" or "SELL"
             qty: Fill quantity (always positive)
             price: Fill price
             
         Returns:
             Updated position dict
         """
+        # Input validation
         if qty <= 0:
             raise ValueError(f"qty must be positive, got {qty}")
-        if side.upper() not in ("BUY", "SELL"):
+        if price <= 0:
+            raise ValueError(f"price must be positive, got {price}")
+        if not symbol or not isinstance(symbol, str):
+            raise ValueError(f"symbol must be non-empty string, got {symbol}")
+        
+        side = side.upper()
+        if side not in ("BUY", "SELL"):
             raise ValueError(f"side must be BUY or SELL, got {side}")
         
-        side = side.upper()
-        current = self.get_position(symbol)
+        conn = self._get_connection()
+        with conn:  # Transaction starts (context manager commits/rolls back)
+            current = self.get_position(symbol)
+            
+            current_qty = current["qty"] if current else 0.0
+            current_avg = current.get("avg_price") if current else None
+            
+            delta = qty if side == "BUY" else -qty
+            new_qty = current_qty + delta
         
-        if current is None:
-            # No existing position
-            if side == "BUY":
-                new_qty = qty
-                new_avg = price
-            else:
-                # SELL with no position: short position
-                new_qty = -qty
-                new_avg = price
-        else:
-            current_qty = current["qty"]
-            current_avg = current["avg_price"] or 0.0
+            # Handle exact close
+            if abs(new_qty) < 1e-10:
+                self.delete_position(symbol)
+                return {"symbol": symbol, "qty": 0.0, "avg_price": None, "closed": True}
             
-            if side == "BUY":
-                # Add to position
-                total_value = (current_qty * current_avg) + (qty * price)
-                new_qty = current_qty + qty
-                new_avg = total_value / new_qty if new_qty != 0 else 0.0
-            else:
-                # Reduce position
-                new_qty = current_qty - qty
-                # Keep avg_price on sell (realized P&L would be external)
-                new_avg = current_avg if new_qty != 0 else None
+            # Compute new average price
+            new_avg = self._compute_new_avg_price(
+                current_qty, current_avg, qty, price, new_qty
+            )
         
-        # Handle position closure
-        if abs(new_qty) < 1e-10:
-            self.delete_position(symbol)
-            return {"symbol": symbol, "qty": 0.0, "avg_price": None, "closed": True}
+            self.upsert_position(symbol, new_qty, new_avg)
         
-        self.upsert_position(symbol, new_qty, new_avg)
-        return self.get_position(symbol)
+        # Fetch and return updated position
+        return self.get_position(symbol)
```

---

## Test Matrix + Asserts Esperados

```python
# Tests a añadir a test_position_store_sqlite.py

def test_short_increase_recalculates_avg_price(self, tmp_path):
    """SELL on existing short should recompute weighted avg."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        # Short 1.0 @ 80
        store.apply_fill("BTC/USDT", "SELL", 1.0, 80.0)
        # Increase short by 1.0 @ 75
        result = store.apply_fill("BTC/USDT", "SELL", 1.0, 75.0)
        assert result["qty"] == -2.0
        assert result["avg_price"] == pytest.approx(77.5)  # (80+75)/2

def test_long_to_short_cross_resets_avg_price(self, tmp_path):
    """SELL that flips long to short should use new price for avg."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        # Long 1.0 @ 100
        store.apply_fill("BTC/USDT", "BUY", 1.0, 100.0)
        # Sell 2.0 @ 90 (cross to short -1.0)
        result = store.apply_fill("BTC/USDT", "SELL", 2.0, 90.0)
        assert result["qty"] == -1.0
        assert result["avg_price"] == 90.0  # Not 100!

def test_short_to_long_cross_resets_avg_price(self, tmp_path):
    """BUY that flips short to long should use new price for avg."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        # Short -1.0 @ 80
        store.apply_fill("BTC/USDT", "SELL", 1.0, 80.0)
        # Buy 2.0 @ 95 (cross to long 1.0)
        result = store.apply_fill("BTC/USDT", "BUY", 2.0, 95.0)
        assert result["qty"] == 1.0
        assert result["avg_price"] == 95.0  # Not 80!

def test_partial_cover_keeps_avg_price(self, tmp_path):
    """BUY that reduces (but doesn't close) short keeps avg."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        # Short -2.0 @ 80
        store.apply_fill("BTC/USDT", "SELL", 2.0, 80.0)
        # Cover 1.0 @ 85 (still short -1.0)
        result = store.apply_fill("BTC/USDT", "BUY", 1.0, 85.0)
        assert result["qty"] == -1.0
        assert result["avg_price"] == 80.0  # Keeps original avg

def test_price_validation(self, tmp_path):
    """Price <= 0 should raise."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        with pytest.raises(ValueError, match="price must be positive"):
            store.apply_fill("BTC/USDT", "BUY", 1.0, 0.0)
        with pytest.raises(ValueError, match="price must be positive"):
            store.apply_fill("BTC/USDT", "BUY", 1.0, -50.0)

def test_symbol_validation(self, tmp_path):
    """Empty or non-string symbol should raise."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        with pytest.raises(ValueError, match="symbol must be non-empty string"):
            store.apply_fill("", "BUY", 1.0, 100.0)
        with pytest.raises(ValueError, match="symbol must be non-empty string"):
            store.apply_fill(None, "BUY", 1.0, 100.0)

def test_atomicity_on_failure(self, tmp_path):
    """If apply_fill fails mid-operation, state should remain unchanged."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        # Setup: long 1.0
        store.apply_fill("BTC/USDT", "BUY", 1.0, 100.0)
        # Monkey-patch get_position to fail after being called
        original_get = store.get_position
        call_count = 0
        def failing_get(symbol):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise RuntimeError("Simulated DB failure")
            return original_get(symbol)
        store.get_position = failing_get
        
        # This should fail and rollback
        with pytest.raises(RuntimeError):
            store.apply_fill("BTC/USDT", "BUY", 1.0, 110.0)
        
        # Position should still be 1.0 @ 100
        pos = store.get_position("BTC/USDT")
        assert pos["qty"] == 1.0
        assert pos["avg_price"] == 100.0

def test_meta_json_deterministic(self, tmp_path):
    """Same meta dict with different key order should produce same JSON."""
    db_path = tmp_path / "state.db"
    with PositionStoreSQLite(db_path) as store:
        meta1 = {"a": 1, "b": 2, "c": 3}
        meta2 = {"c": 3, "b": 2, "a": 1}
        
        store.upsert_position("BTC/USDT", 1.0, meta=meta1)
        row1 = store.get_position("BTC/USDT")
        
        store.upsert_position("ETH/USDT", 1.0, meta=meta2)
        row2 = store.get_position("ETH/USDT")
        
        # Compare JSON strings (should be identical)
        import json
        assert json.dumps(row1["meta"], sort_keys=True) == json.dumps(row2["meta"], sort_keys=True)
```

---

## Riesgos de Compatibilidad + Mitigación

### 1. Tests existentes que fallarán:
- **`test_buy_increases_position`**: Actual calcula avg_price incorrecto para segundo BUY (no usa promedio ponderado).  
  **Mitigación**: Actualizar expected value de 55000.0 a 55000.0 (ya correcto).
- **`test_sell_no_position_creates_short`**: Actual establece avg_price = price (correcto). Test pasa.

### 2. Cambio de comportamiento en cruces:
- **Riesgo**: Código que dependa del avg_price previo en cruces verá valores diferentes.
- **Mitigación**: Documentar cambio como "bug fix" en CHANGELOG. El comportamiento anterior era financieramente incorrecto.

### 3. Validaciones nuevas:
- **Riesgo**: Código que pase price=0 o symbol="" fallará.
- **Mitigación**: Estas son condiciones de error que deberían haberse validado siempre.

### 4. Transacciones:
- **Riesgo**: `with conn:` (autocommit=False) puede cambiar comportamiento en errores.
- **Mitigación**: Testear rollback explícito (ver test_atomicity_on_failure).

### 5. PRAGMA WAL (opcional):
Si se añade:
```python
def ensure_schema(self):
    conn = self._get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    # ... resto del schema
```
**Riesco**: DB files no portables a sistemas sin WAL (raro).  
**Mitigación**: Hacer opcional con `PRAGMA journal_mode=WAL;` falla silenciosamente si no soportado.

---

## DoD Checklist para PR
- [ ] `apply_fill` recalcula avg_price correctamente para aumentos de short
- [ ] `apply_fill` usa price de la operación en cruces (no mantiene avg anterior)
- [ ] Operación es atómica (transaction con `with conn:`)
- [ ] `json.dumps(meta, sort_keys=True, separators=(',', ':'))`
- [ ] Validaciones: qty>0, price>0, side válido, símbolo no vacío
- [ ] Tests nuevos (8-12) pasan
- [ ] Tests existentes pasan (actualizar 1-2 expected values si necesario)
- [ ] No nuevas dependencias
- [ ] Documentación en docstrings actualizada

**Tamaño estimado**: 80-100 líneas modificadas (incluyendo tests).