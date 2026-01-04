# DS-3C-5-1 — Audit Avanzado LoopStepper 3C

## Executive Summary
El LoopStepper 3C muestra diseño sólido con **3 issues P1** que afectan determinismo y contratos. No hay bloqueantes absolutos (P0), pero se recomienda resolver antes de cerrar 3C.5. El sistema es "GO para 3C.6/3C.7" con las mejoras propuestas.

---

## Lista Priorizada de Issues

### P1 (Importante - afecta reproducibilidad/contratos)
1. **Non-determinismo en serialización JSON**: `json.dumps()` sin `sort_keys=True` en múltiples lugares.
2. **Propagación incompleta de trace_id**: `ExecutionReportV1` no recibe `trace_id` del `OrderIntentV1`.
3. **Edge case en apply_fill**: cálculo de avg_price al cruzar de flat a short con BUY previo no válido.

### P2 (Mejora - observabilidad/debug)
4. **Falta de step_idx en eventos**: imposible reconstruir secuencia exacta desde NDJSON.
5. **Meta inconsistente entre v0.4 y v0.6**: diferentes estructuras en `extra` fields.
6. **Validación insuficiente de price en ExecutionAdapter**: acepta price=0.

### P3 (Cosmético/documentación)
7. **Nombres de campos en meta**: inconsistentes entre componentes.
8. **Falta de engine_version en run_meta**: tracking de versiones.

---

## 1. Determinismo - Fuentes de No-Determinismo

### Hallazgos:
1. **JSON no estable**: 
   - `position_store_sqlite.py`: `json.dumps(meta)` sin `sort_keys=True`
   - `risk_manager_v0_6.py`: `extra` dict serializado sin ordenar
   - `run_live_integration_3C.py`: eventos serializados con `json.dumps(payload)`

2. **Orden de dict no garantizado**:
   - Python 3.7+ mantiene insertion order, pero dicts con mismas keys en diferente orden producen JSON diferente.

3. **Floats sin redondeo estable**:
   - Cálculos de avg_price con floats pueden variar en diferentes arquitecturas (raro).
   - Comparaciones en tests usan `pytest.approx` (correcto).

### Mitigación mínima:
```python
# En todos los json.dumps(), añadir:
json.dumps(data, sort_keys=True, separators=(',', ':'))
```

---

## 2. Contratos - Campos Obligatorios

### OrderIntentV1 → RiskDecisionV1 → ExecutionReportV1:

**Problema**: `ExecutionReportV1` no recibe `trace_id` del intent original.
```python
# En loop_stepper.py o execution adapter:
exec_report = ExecutionReportV1(
    ref_order_event_id=order_intent.event_id,
    trace_id=order_intent.trace_id,  # ¡Falta en implementación actual!
    # ...
)
```

**Drift v0.4 vs v0.6**:
- v0.6: `RiskDecisionV1.rejection_reasons` es `List[str]` normalizado
- v0.4: `annotated["risk_reasons"]` puede ser `List[Any]`
- **Recomendación**: Usar siempre v0.6 en 3C, marcar deprecated v0.4 en stepper.

**Campos faltantes en meta**:
- `OrderIntentV1.meta` debería incluir `strategy_id`, `generated_at`
- `ExecutionReportV1.meta` debería incluir `latency_ms`, `slippage_bps`

---

## 3. Semántica de Estado - apply_fill()

### Casos problemáticos identificados:

#### A) Long → reduce → flat → short (cross consecutivo)
```python
# Setup: long 1.0 @ 100
apply_fill("A", "SELL", 1.0, 110)  # flat
apply_fill("A", "SELL", 1.0, 90)   # short -1.0 @ 90
```
**Issue**: flat intermedio elimina la posición de la DB. La transición flat→short funciona pero pierde histórico.

**Fix**: Mantener fila con qty=0 y avg_price=None, o documentar comportamiento.

#### B) Short → reduce → flat → long (cross inverso)
Mismo issue simétrico.

#### C) avg_price en shorts
**Implementación actual correcta**:
- Short: qty negativo, avg_price positivo (precio de venta promedio)
- Cálculo correcto: promedio ponderado de ventas

**Verificación**:
```python
# Short -1.0 @ 80
apply_fill("A", "SELL", 1.0, 80)    # qty=-1.0, avg=80
apply_fill("A", "SELL", 1.0, 70)    # qty=-2.0, avg=75 ✓
apply_fill("A", "BUY", 1.0, 85)     # qty=-1.0, avg=75 (cover parcial)
```

#### D) qty=0 edge / price<=0 edge
**Price=0 validado** en patch anterior (correcto).
**qty=0 edge**: `apply_fill` lanza ValueError (correcto).

---

## 4. Compatibilidad v0.4/v0.6 en NDJSON

### Problema:
NDJSON mezcla:
- `OrderIntent` (v0.4 style) vs `OrderIntentV1` (v1)
- `RiskDecision` vs `RiskDecisionV1`
- Diferentes schemas en mismo stream

### Recomendación:
**Añadir explicitamente**:
```python
# En cada evento, añadir schema_version
{
    "type": "OrderIntentV1",
    "schema_version": "1.0",
    "payload": {...}
}
```

**O mejor**: Usar solo contratos v1 en 3C.5+, convertir internamente si necesario.

---

## 5. Observabilidad - Campos Adicionales

### 2-3 campos críticos:
1. **step_idx**: Contador incremental por evento en el stepper
2. **bar_ts**: Timestamp del OHLCV que generó el evento
3. **engine_version**: "3C.5" o hash del commit

**Implementación mínima**:
```python
# En loop_stepper.py
class LoopStepper:
    def __init__(self, config):
        self.step_idx = 0
        self.engine_version = "3C.5"
    
    def step(self, data_slice):
        self.step_idx += 1
        # En cada evento:
        event.meta["step_idx"] = self.step_idx
        event.meta["engine_version"] = self.engine_version
```

---

## Propuestas de Fix (Diffs)

### P1.1: JSON Determinista
```diff
# En position_store_sqlite.py
- meta_json = json.dumps(meta) if meta else None
+ meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':')) if meta else None

# En risk_manager_v0_6.py (método assess)
- extra={...}
+ extra=json.dumps({...}, sort_keys=True, separators=(',', ':'))

# En run_live_integration_3C.py (output NDJSON)
- f.write(json.dumps(line_data) + "\n")
+ f.write(json.dumps(line_data, sort_keys=True, separators=(',', ':')) + "\n")
```

### P1.2: Propagación de trace_id
```diff
# En execution_adapter_v0_2.py o loop_stepper.py
def simulate_execution(order_intent, config):
    return ExecutionReportV1(
        ref_order_event_id=order_intent.event_id,
+       trace_id=order_intent.trace_id,
        status="FILLED",
        # ...
    )
```

### P1.3: Edge Case Flat→Short
```python
# Documentar comportamiento actual o modificar:
def apply_fill(self, symbol, side, qty, price):
    current = self.get_position(symbol)
    if current is None and side == "SELL":
        # Short desde flat - comportamiento actual OK
        new_qty = -qty
        new_avg = price
    # ... resto
```

---

## Tests Unit/Integration Adicionales

### 1. Determinismo Hash
```python
def test_loop_stepper_deterministic_hash():
    """Same seed → same NDJSON hash."""
    runner1 = run_integration(config, seed=42)
    runner2 = run_integration(config, seed=42)
    hash1 = hashlib.md5(runner1.get_ndjson().encode()).hexdigest()
    hash2 = hashlib.md5(runner2.get_ndjson().encode()).hexdigest()
    assert hash1 == hash2
```

### 2. Contract Chain Completeness
```python
def test_trace_id_propagation():
    """trace_id flows OrderIntent→RiskDecision→ExecutionReport."""
    events = run_stepper()
    for intent in events_of_type(OrderIntentV1):
        decision = find_risk_decision_for(intent)
        assert decision.trace_id == intent.trace_id
        if decision.allowed:
            report = find_execution_report_for(intent)
            assert report.trace_id == intent.trace_id
```

### 3. State Transition Matrix
```python
def test_state_transition_long_flat_short():
    """Long → flat → short preserves invariants."""
    store = PositionStoreSQLite(":memory:")
    # Long 1.0
    store.apply_fill("A", "BUY", 1.0, 100)
    assert store.get_position("A")["qty"] == 1.0
    
    # Flat
    store.apply_fill("A", "SELL", 1.0, 110)
    assert store.get_position("A") is None
    
    # Short desde flat
    result = store.apply_fill("A", "SELL", 1.0, 90)
    assert result["qty"] == -1.0
    assert result["avg_price"] == 90.0
```

### 4. Price Validation
```python
def test_execution_adapter_rejects_zero_price():
    """Execution adapter should reject price=0."""
    intent = OrderIntentV1(..., limit_price=0.0)
    with pytest.raises(ValueError, match="price must be positive"):
        simulate_execution(intent, config)
```

---

## Riesgos de Compatibilidad

### Con 3B:
- **Runner 3B** usa contracts v0.4 style
- **Stepper 3C** usa contracts v1
- **Mitigación**: Runner 3C puede mantener shim para backward compat, pero marcar como deprecated.

### Con tests existentes:
- JSON ordenado puede cambiar hashes en tests
- **Mitigación**: Actualizar snapshots o usar `json.loads()` para comparar dicts, no strings.

---

## DoD Checklist para 3C.5

- [ ] JSON determinista en todos los outputs (`sort_keys=True`)
- [ ] `trace_id` propagado en toda la cadena (Intent→Decision→Report)
- [ ] Tests de determinismo pasan (seed→hash igual)
- [ ] Edge cases de estado documentados/testeados
- [ ] Schema_version en eventos o documentación clara
- [ ] Campos observabilidad básicos (step_idx, engine_version)

---

## Conclusión: GO para 3C.6/3C.7

**No hay bloqueantes absolutos**. El sistema es funcional y los issues P1 pueden resolverse en 3C.5 o 3C.6 sin romper integración.

**Recomendación de prioridad**:
1. Aplicar `sort_keys=True` en JSON serialization (1-2 horas)
2. Añadir propagación de `trace_id` (30 minutos)
3. Añadir tests de determinismo (1 hora)

**Estado final**: El LoopStepper 3C está en buen estado para proceder con integración live/real-data en 3C.6.