# DS-3C-4-1: SQLite Position Store Audit

## Executive Summary
El módulo `position_store_sqlite.py` implementa correctamente un almacén de posiciones con sqlite3 (stdlib), mostrando diseño limpio y test coverage robusto. Se identifican oportunidades en: (1) semántica de cruce long↔short, (2) atomicidad de operaciones complejas, (3) estabilidad numérica, y (4) casos edge adicionales. Se recomienda adoptar **Opción A (soportar shorts)** con ajustes en cálculo de avg_price durante cruces.

---

## Findings (severidad)

### P1: Semántica de cruce long↔short ambigua
**Ubicación**: `apply_fill()`, líneas 157-195
**Descripción**: Al cruzar de long a short (ej: long 1.0 → SELL 2.0), el código actual mantiene el `avg_price` del long para la nueva posición short, lo cual es incorrecto financieramente. El avg_price del short debe ser el precio de la operación que abre el short.
**Impacto**: Cálculo incorrecto de P&L y márgenes si se usara para risk management.

### P2: Falta transacciones atómicas en operaciones multi-step
**Ubicación**: `apply_fill()` (select → cálculo → upsert)
**Descripción**: Entre el `get_position()` y el `upsert_position()` hay ventana de race condition. En concurrencia (aunque baja en este stage), podría perderse updates.
**Impacto**: Estado inconsistente bajo carga concurrente.

### P3: Validación insuficiente de inputs
**Ubicación**: `apply_fill()`, solo valida qty>0 y side∈{BUY,SELL}
**Descripción**: No valida price>0, símbolo no vacío, side case-insensitive consistente.
**Impacto**: Posibles estados corruptos por datos inválidos.

### P4: Serialización JSON no determinista
**Ubicación**: `upsert_position()`, línea 127: `json.dumps(meta)`
**Descripción**: Sin `sort_keys=True`, dicts con mismas keys en distinto orden producen strings diferentes, afectando comparaciones en tests.
**Impacto**: Tests frágiles, hashes no reproducibles.

---

## Proposed Semantics (Opción A + recomendaciones)

### Decisión: **Soportar shorts (qty negativa)**
**Justificación**:
1. El código ya soporta shorts (test `test_sell_no_position_creates_short` pasa).
2. Más realista para simulación/backtesting.
3. Cruces long↔short son eventos válidos en trading.

### Invariantes actualizados:

| Estado | Qty | Avg_price | Notas |
|--------|-----|-----------|-------|
| Flat | 0.0 | None | Posición removida de DB o qty=0 |
| Long | >0 | >0 | Precio promedio ponderado de compras |
| Short | <0 | >0 | Precio promedio ponderado de ventas |

### Reglas para `apply_fill(symbol, side, qty, price)`:

1. **BUY aumenta long/disminuye short**:
   - Si posición actual long: avg_price = promedio ponderado (ya OK)
   - Si posición actual short y qty ≤ |current_qty|: avg_price se mantiene (cubrir parcial)
   - Si posición actual short y qty > |current_qty|: **CRUCE** → nuevo avg_price = price (abrir long)

2. **SELL aumenta short/disminuye long**:
   - Si posición actual short: avg_price = promedio ponderado de ventas (FALTA)
   - Si posición actual long y qty ≤ current_qty: avg_price se mantiene (vender parcial)
   - Si posición actual long y qty > current_qty: **CRUCE** → nuevo avg_price = price (abrir short)

3. **Cálculo promedio ponderado para aumentar posición** (mismo signo):
   ```
   new_avg = (abs(current_qty)*current_avg + qty*price) / abs(new_qty)
   ```
   Usar `abs()` para que funcione tanto para longs como shorts.

4. **Cierre exacto (qty → 0)**: avg_price = None, marca `closed:true`.

### Pseudocódigo propuesto para `apply_fill`:

```python
current = self.get_position(symbol)
current_qty = current["qty"] if current else 0.0
current_avg = current["avg_price"] if current else None

# Delta basado en side
delta = qty if side == "BUY" else -qty
new_qty = current_qty + delta

# Casos especiales
if abs(new_qty) < 1e-10:  # cierre exacto
    self.delete_position(symbol)
    return {"symbol": symbol, "qty": 0.0, "avg_price": None, "closed": True}

# Determinación de nuevo avg_price
if current_qty == 0:  # posición nueva
    new_avg = price
elif current_qty * new_qty > 0:  # mismo signo (aumentar o reducir)
    if abs(new_qty) > abs(current_qty):  # aumentar posición
        new_avg = (abs(current_qty)*current_avg + qty*price) / abs(new_qty)
    else:  # reducir posición
        new_avg = current_avg  # mantener avg existente
else:  # cruce de signo (long↔short)
    new_avg = price  # nuevo precio promedio es el de la operación que cruza

self.upsert_position(symbol, new_qty, new_avg)
return self.get_position(symbol)
```

---

## Test Matrix (16+ casos)

| # | Caso | Setup | Acción | Expected invariants | DB rows after |
|---|------|-------|--------|-------------------|---------------|
| 1 | Fresh DB schema | new tmp DB | ensure_schema() x3 | Tables exist | 0 positions, 0 kv |
| 2 | Upsert básico | empty | upsert("A", 1.0, 100) | qty=1, avg=100 | 1 row |
| 3 | Upsert con meta | empty | upsert("A", 1.0, meta={"s":"SMA"}) | meta intacta | meta_json almacenado |
| 4 | Get inexistente | empty | get("B") | None | 0 rows |
| 5 | List multiple | A=1, B=2 | list_positions() | 2 items, ordenados | 2 rows |
| 6 | Delete existente | A=1 | delete("A") | True, get→None | 0 rows |
| 7 | Delete inexistente | empty | delete("X") | False | 0 rows |
| 8 | Flat → Long | empty | apply_fill("A", "BUY", 1, 100) | qty=1, avg=100 | 1 row |
| 9 | Long → +Long | A=1@100 | apply_fill("A", "BUY", 2, 120) | qty=3, avg=113.333 | 1 row |
|10 | Long → -Long (parcial) | A=3@113.333 | apply_fill("A", "SELL", 1, 130) | qty=2, avg=113.333 | 1 row |
|11 | Long → Flat (exact) | A=2@113.333 | apply_fill("A", "SELL", 2, 140) | qty=0, closed=True | 0 rows |
|12 | Long → Short (cruce) | A=1@100 | apply_fill("A", "SELL", 2, 90) | qty=-1, avg=90 | 1 row (short) |
|13 | Flat → Short | empty | apply_fill("A", "SELL", 1, 80) | qty=-1, avg=80 | 1 row |
|14 | Short → +Short | A=-1@80 | apply_fill("A", "SELL", 1, 75) | qty=-2, avg=77.5 | 1 row |
|15 | Short → -Short (cubrir) | A=-2@77.5 | apply_fill("A", "BUY", 1, 85) | qty=-1, avg=77.5 | 1 row |
|16 | Short → Flat (exact) | A=-1@77.5 | apply_fill("A", "BUY", 1, 90) | qty=0, closed=True | 0 rows |
|17 | Short → Long (cruce) | A=-1@77.5 | apply_fill("A", "BUY", 2, 95) | qty=1, avg=95 | 1 row |
|18 | Invalid qty=0 | empty | apply_fill("A", "BUY", 0, 100) | ValueError | 0 rows |
|19 | Invalid qty<0 | empty | apply_fill("A", "BUY", -1, 100) | ValueError | 0 rows |
|20 | Invalid side | empty | apply_fill("A", "HOLD", 1, 100) | ValueError | 0 rows |
|21 | Invalid price=0 | empty | apply_fill("A", "BUY", 1, 0) | ValueError (si se agrega validación) | - |
|22 | KV set/get | empty | set_kv("k","v"), get_kv("k") | "v" | 1 kv row |
|23 | KV update | k="v1" | set_kv("k","v2") | "v2" | 1 kv row |
|24 | KV delete | k="v" | delete_kv("k") | True, get→None | 0 kv rows |

---

## Micro-Patches (5 mejoras ≤30 líneas)

### 1. Validación mejorada de inputs
```python
# En apply_fill, después de validar side
if price <= 0:
    raise ValueError(f"price must be positive, got {price}")
if not symbol or not isinstance(symbol, str):
    raise ValueError(f"symbol must be non-empty string, got {symbol}")
```

### 2. Context manager para transacciones
```python
def _transaction(self):
    """Context manager for atomic operations."""
    conn = self._get_connection()
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise

# Uso en apply_fill:
with self._transaction() as conn:
    # operaciones con conn.execute
```

### 3. Serialización JSON estable
```python
# En upsert_position
meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':')) if meta else None
```

### 4. Cálculo de avg_price en función helper
```python
def _compute_new_avg(self, current_qty, current_avg, delta_qty, delta_price, new_qty):
    """Compute new average price for position update."""
    if current_qty == 0 or current_avg is None:
        return delta_price
    if current_qty * new_qty > 0:  # same sign
        if abs(new_qty) > abs(current_qty):  # increasing
            return (abs(current_qty)*current_avg + abs(delta_qty)*delta_price) / abs(new_qty)
        else:  # decreasing
            return current_avg
    else:  # crossing
        return delta_price
```

### 5. WAL mode para mejor concurrencia
```python
def ensure_schema(self):
    conn = self._get_connection()
    # Enable WAL for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
    conn.executescript(self.SCHEMA_SQL)
    conn.commit()
```

---

## Risks & Non-goals

### Risks
1. **Precisión floating-point**: Cálculos repetidos podrían acumular error. Usar `math.isclose` en tests.
2. **Concurrencia limitada**: SQLite con WAL soporta un writer múltiples readers, pero no alta concurrencia.
3. **Migración de schema**: Cambios futuros en schema requerirán migración manual.

### Non-goals
1. **Distributed locking**: No necesario para single-process bot.
2. **Audit trail completo**: Solo estado actual, no histórico de fills.
3. **ACID full isolation**: SQLite garantiza atomicidad pero isolation depende de uso.
4. **Performance ultra alta**: Optimizado para simulación, no HFT.

---

## DoD Checklist

### Semántica y funcionalidad
- [ ] `apply_fill` calcula avg_price correctamente en cruces long↔short
- [ ] Shorts soportados con avg_price positivo y cálculos consistentes
- [ ] Cierre exacto retorna `closed:true` y elimina fila
- [ ] Validaciones: qty>0, price>0, side∈{BUY,SELL}, símbolo no vacío

### Robustez
- [ ] Transacciones usadas en `apply_fill` (atomicidad)
- [ ] WAL mode habilitado (opcional pero recomendado)
- [ ] JSON estable con `sort_keys=True`
- [ ] Tests cubren matriz de 16+ casos

### Calidad código
- [ ] No nuevas dependencias
- [ ] Funciones helper para lógica compleja (ej: `_compute_new_avg`)
- [ ] Error messages claros
- [ ] Docstrings actualizados

### Tests
- [ ] Todos los tests P0-P2 pasan
- [ ] Tests de cruce long↔short añadidos
- [ ] Tests de atomicidad (ej: rollback on error)
- [ ] Tests con floats usando `pytest.approx`

### Integración
- [ ] Compatible con eventos `ExecutionReport` de 3B/3C
- [ ] Método `apply_fill_from_execution_report(exec_report)` opcional
- [ ] Bridge documentado en `report/bridge_3C4_to_3C5.md`

---

**Nota final**: La implementación actual es sólida y las mejoras propuestas son incrementales. Priorizar: (1) fix cruce avg_price, (2) transacciones, (3) tests adicionales.