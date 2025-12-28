# RiskManager v0.5 — Especificación del bloque `risk_decision`
Plan 1C · Paso B · Fecha lógica: 2025-12-01

Este documento define la estructura del bloque `risk_decision`, el orden de evaluación de reglas de riesgo dentro de `RiskManagerV05.filter_signal`, y los casos mínimos de test de integración que deben implementarse en `tests/test_risk_decision_v0_5.py`.

Se apoya en:
- Fase 1A (contrato público de RiskManager v0.4).
- Fase 1B (diseño de guardrails avanzados: DD global, stop-loss ATR, límites/Kelly, etc.).
- Implementación parcial actual de `risk_manager_v0_5.py` (helpers de DD y ATR ya existentes).
- Informe de revisión `report/risk_v0_5_review_20251201.md` y tests extendidos v0.5.

---

## 1. Objetivo del bloque `risk_decision`

El objetivo de `risk_decision` es concentrar en una estructura única la decisión de riesgo resultante de combinar:
- Límites de posición y exposición (lógica heredada de v0.4).
- Guardrail de Drawdown (DD) global sobre la curva de equity.
- Stops ATR por posición (por ticker/símbolo).
- Reglas de Kelly y recortes de tamaño por límites de capital.
- Otros posibles motivos futuros (liquidez, volatilidad, overrides por activo, etc.).

`risk_decision` sirve como:
1. Punto único de lectura para el backtester/ejecutor.
2. Registro trazable del “por qué” de cada decisión de riesgo.
3. Capa de unificación entre la lógica antigua (v0.4) y las extensiones v0.5.

---

## 2. Estructura de `risk_decision`

### 2.1. Campos requeridos

Se define `risk_decision` como un diccionario con los siguientes campos:

- `allow_new_trades: bool`
  - Indica si se permite abrir nuevas posiciones.

- `force_close_positions: bool`
  - Indica si se debe forzar el cierre de posiciones abiertas.

- `size_multiplier: float`
  - Rango: `0.0 <= size_multiplier <= 1.0`.
  - Factor global aplicado a tamaños de posición.

- `stop_signals: list[str]`
  - Lista de tickers cuya posición debe cerrarse por activación de stop ATR.

- `reasons: list[str]`
  - Lista de motivos (etiquetas) que han influido en la decisión.

### 2.2. Valores por defecto

```python
risk_decision = {
    "allow_new_trades": True,
    "force_close_positions": False,
    "size_multiplier": 1.0,
    "stop_signals": [],
    "reasons": [],
}
```

---

## 3. Orden de evaluación en `RiskManagerV05.filter_signal`

El orden obligatorio es:

1. **Límites de posición (v0.4)**  
2. **Drawdown (DD) global**  
3. **Stop-loss ATR por posición**  
4. **Reglas antiguas (Kelly y recortes)**  
5. **Sincronización final con `annotated_signal`**

---

### 3.1. Etapa 1 — Límites de posición

- Usar la lógica existente en v0.4.
- Si se violan límites:
  - `risk_decision["allow_new_trades"] = False`
  - Añadir `"position_limits"` a `risk_decision["reasons"]`.

---

### 3.2. Etapa 2 — Guardrail de Drawdown (DD) global

Inputs:
- `equity_curve: list[float]`
- `dd_cfg` con:
  - `max_dd_soft`
  - `max_dd_hard`
  - `size_multiplier_soft`

Helpers existentes:
- `compute_drawdown`
- `eval_dd_guardrail`

Estados y efectos:

#### `state == "normal"`
- Tamaño normal.
- No añadir motivos.

#### `state == "risk_off_light"`
- `size_multiplier = min(size_multiplier, size_multiplier_soft)`
- Añadir `"dd_soft"` a razones.

#### `state == "hard_stop"`
- `allow_new_trades = False`
- `force_close_positions = True`
- `size_multiplier = 0.0`
- Motivo `"dd_hard"`.

---

### 3.3. Etapa 3 — Stop-loss ATR por posición

Inputs:
- `atr_ctx[ticker] = { "atr", "entry_price", "side", "atr_multiplier", "min_stop_pct" }`
- `last_prices[ticker]`

Si el stop se activa:
- Añadir ticker a `stop_signals`
- Añadir `"stop_loss_atr"` una sola vez a `reasons`  

No modifica directamente `allow_new_trades`.

---

### 3.4. Etapa 4 — Reglas antiguas (Kelly)

- Mantener funcionamiento de v0.4.
- Si Kelly limita tamaño:
  - Añadir `"kelly_cap:{asset}"` a razones.

---

### 3.5. Etapa 5 — Sincronización final

- `allow = risk_decision["allow_new_trades"]`
- `annotated_signal["risk_allow"] = allow`
- `annotated_signal["risk_reasons"]` debe contener todos los motivos de `risk_decision["reasons"]`
- Añadir:
  ```python
  annotated_signal["risk_decision"] = risk_decision
  ```

---

## 4. Tests de integración `test_risk_decision_v0_5.py`

Los tests deben validar coherencia entre:

- `allow`
- `annotated["risk_allow"]`
- `annotated["risk_decision"]`

### Casos mínimos:

1. **test_decision_normal**
2. **test_decision_dd_soft**
3. **test_decision_dd_hard**
4. **test_decision_atr_stop**
5. **test_decision_limits_and_kelly**

Cada test debe:
- Crear `RiskManagerV05` con config mínima.
- Generar `signal`, `current_weights`, y contextos:
  - `equity_curve`
  - `dd_cfg`
  - `atr_ctx`
- Ejecutar `.filter_signal(...)`
- Validar campos del bloque `risk_decision`.

---

## 5. Requisitos adicionales

- Mantener v0.4 intacto.
- Respetar contratos event-driven.
- Respetar API definida en Fase 1A.
- Ser compatible con DD, ATR y tests extendidos v0.5.

Fin de la especificación.
