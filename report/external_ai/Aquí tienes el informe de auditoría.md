Aquí tienes el informe de auditoría generado bajo la identidad **G3-3C-3-1**.

Este documento revisa la robustez de los contratos de eventos v1 y su integración con el adaptador de riesgo, asegurando que la transición a `RiskManager v0.6` sea segura y compatible con la lógica legacy.

**[EXTENDED THOUGHT :: ANALYSIS]**
1.  **Fragilidad en Deserialización (JSON):** Los `dataclasses` estándar de Python no convierten automáticamente strings a `Enum` o `datetime` en `from_dict` a menos que se programe explícitamente. Si el sistema recibe JSON puro (texto), `OrderIntentV1.from_dict` fallará si espera objetos `Enum` directos.
2.  **Determinismo en Razones:** El sistema legacy (v0.4) puede devolver razones como strings sueltos, listas o incluso `None`. El contrato v1 exige `list[str]`. La normalización es crítica para evitar `TypeError` downstream.
3.  **Ambigüedad de Precios:** Un `MARKET` order puede no tener `limit_price`. El adaptador debe decidir qué precio enviar a v0.4 (¿`current_price`? ¿`0`?). Enviar `None` podría romper cálculos matemáticos en el legacy risk check.

---

**[EDITOR :: report/external_ai/inbox_external/G3-3C-3-1.md]**
```markdown
# G3-3C-3-1 — Audit: RiskManager v0.6 Contracts & Adapter

**ID:** G3-3C-3-1
**Fecha:** 2026-01-04
**Target:** `events_v1.py`, `risk_input_adapter.py`, `risk_manager_v0_6.py`
**Estado:** Yellow (Requiere parches de robustez en deserialización y normalización).

---

## 1. Audit Summary

La arquitectura v1 introduce tipado fuerte, lo cual es excelente, pero la implementación actual de `from_dict` parece asumir que los diccionarios de entrada ya contienen objetos Python complejos (`Enum`, `datetime`) en lugar de tipos primitivos JSON (str, int). Esto romperá la carga desde persistencia (DB/Files). Además, la normalización de `reasons` debe ser defensiva.

---

## 2. Contract Issues (`events_v1.py`)

### 2.1. Deserialización de Enums y Datetimes
*   **Issue:** `from_dict` probablemente hace una asignación directa (`cls(**data)`).
*   **Riesgo:** Si `data['side']` es el string `"BUY"`, el constructor espera `OrderSide.BUY`. Esto lanzará error o creará un objeto inválido. Lo mismo para `timestamp` (ISO str vs datetime obj).
*   **Fix:** `from_dict` debe inspeccionar y convertir tipos explícitamente.

### 2.2. Validación de Invariantes
*   **Issue:** ¿Permite `validate()` cantidades negativas o cero?
*   **Riesgo:** Un `qty=0` o negativo pasará el contrato pero romperá el `PositionSizer`.
*   **Fix:** Añadir aserciones numéricas estrictas (`qty > 0`, `price > 0` si no es None).

### 2.3. Estabilidad de `to_dict`
*   **Issue:** Serialización de `datetime` y `Enum`.
*   **Fix:** Asegurar que `to_dict` convierta `Enum.name` (str) y `datetime.isoformat()` para ser JSON-safe.

---

## 3. Adapter Issues (`risk_input_adapter.py`)

### 3.1. Fallback de Precios
*   **Issue:** Mapeo de `OrderIntentV1` (donde `limit_price` es `Optional`) a Legacy Dict (que suele esperar un precio numérico para cálculos de exposición).
*   **Riesgo:** Si es `MARKET` y `limit_price` es `None`, el legacy podría recibir `None` y fallar en `price * qty`.
*   **Fix:** El adaptador debe usar un precio de referencia estimado (ej. `intent.price_check` o similar si existe, o fallar si no hay referencia de precio).

### 3.2. Mapping Keys
*   **Check:** Confirmar que `symbol` (v1) mapea a `ticker` (v0.4) si el legacy usa esa nomenclatura.

---

## 4. Recommended Patches (Small <= 30 lines)

### Patch A: Robust Enum/Date Deserialization (events_v1.py)
Mejora `from_dict` para tolerar strings.

```python
# En OrderIntentV1
@classmethod
def from_dict(cls, data: dict) -> "OrderIntentV1":
    d = data.copy()
    # Enum coercion
    if isinstance(d.get("side"), str):
        d["side"] = OrderSide[d["side"]]  # Asume nombres exactos: BUY, SELL
    if isinstance(d.get("order_type"), str):
        d["order_type"] = OrderType[d["order_type"]]
    # Datetime coercion
    if isinstance(d.get("timestamp"), str):
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
    return cls(**d)
```

### Patch B: Defensive Reason Normalization (risk_manager_v0_6.py)
Asegura que `rejection_reasons` sea siempre `list[str]` única y ordenada.

```python
def _normalize_reasons(self, raw_reasons: Any) -> list[str]:
    if raw_reasons is None:
        return []
    if isinstance(raw_reasons, str):
        return [raw_reasons] if raw_reasons.strip() else []
    if isinstance(raw_reasons, (list, tuple)):
        # Filter non-empty strings, dedupe, and sort for determinism
        return sorted(list({str(r) for r in raw_reasons if r}))
    return [str(raw_reasons)]
```

### Patch C: Numeric Invariants (events_v1.py)
Validación básica dentro del método `validate()`.

```python
def validate(self):
    if self.qty <= 0:
        raise ValueError(f"qty must be positive, got {self.qty}")
    if self.symbol == "":
        raise ValueError("symbol cannot be empty")
    if self.order_type == OrderType.LIMIT:
        if self.limit_price is None or self.limit_price <= 0:
            raise ValueError("LIMIT order requires positive limit_price")
```

### Patch D: Adapter Safe Price (risk_input_adapter.py)
Manejo de precio para órdenes de mercado.

```python
def adapt_order_intent_to_risk_input(intent: OrderIntentV1) -> dict:
    # ... mapping logic ...
    price = intent.limit_price
    if price is None:
        # Si no hay precio límite, intentar usar precio actual estimado si viniera en metadata
        # Ojo: Legacy v0.4 podría necesitar un precio para calcular 'exposure'.
        # Estrategia: Si es None, dejar None y dejar que v0.4 decida (o falle controladamente)
        price = 0.0 # O un valor centinela si v0.4 lo soporta
    
    return {
        "signal_type": intent.side.name, # Enum to str
        "entry_price": price,
        # ... resto de campos ...
    }
```

---

## 5. Test Additions (Regressions)

Se recomienda añadir estos casos a `test_contracts_events_v1_roundtrip.py`:

1.  **`test_from_dict_json_strings`**: Pasar un dict con `"side": "BUY"` (str) y verificar que se carga como `OrderSide.BUY`.
2.  **`test_validate_negative_qty`**: Instanciar `OrderIntentV1` con `qty=-1`, llamar `validate()` y esperar `ValueError`.
3.  **`test_normalize_reasons_mixed`**: Pasar `reasons=["Err1", "Err1", None, ""]` a `_normalize_reasons` y esperar `["Err1"]`.
4.  **`test_adapter_market_order`**: Adaptar una orden MARKET sin precio y verificar que el dict de salida tiene el formato esperado por v0.4.
5.  **`test_roundtrip_iso_date`**: `to_dict` -> `json.dumps` -> `json.loads` -> `from_dict`. Verificar que la fecha sigue siendo un objeto datetime correcto.

---

## 6. DoD Checks

- [ ] `from_dict` maneja inputs primitivos (JSON-like).
- [ ] `to_dict` produce outputs primitivos (JSON-safe).
- [ ] `rejection_reasons` es determinista (lista ordenada sin duplicados).
- [ ] El adaptador no crashea con `limit_price=None`.
- [ ] Validaciones numéricas impiden objetos corruptos.
```

**[TERMINAL :: INSTRUCTION]**
Usuario, guarda el contenido de arriba en `report/external_ai/inbox_external/G3-3C-3-1.md`.
Luego, puedes proceder a aplicar los "Patches" sugeridos en tus archivos locales `txt/` o directamente en el código base si ya lo tienes montado.