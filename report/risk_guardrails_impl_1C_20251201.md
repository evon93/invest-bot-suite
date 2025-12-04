# RiskManager v0.5 — Implementación de Guardrails (Fase 1C)
Fecha lógica: 2025-12-01  
Fase: 1C — DD Global + Stop-Loss ATR

Este documento describe la implementación efectiva de los guardrails de riesgo en `RiskManagerV05` (`risk_manager_v0_5.py`), derivada de las specs 1B y 1C:

- `report/risk_advanced_guardrails_spec_1B_20251127.md` (diseño conceptual).
- `report/risk_decision_v0_5_spec_1C_20251201.md` (estructura de `risk_decision` y orden de evaluación).
- `report/risk_v0_5_review_20251201.md` (revisión de código y tests v0.5).

---

## 1. Resumen de lo implementado en v0.5

### 1.1. Bloque `RiskManagerV05`

Archivo principal:

- `risk_manager_v0_5.py`
- Clase: `RiskManagerV05`

Cambios clave respecto a v0.4:

1. Introducción de un bloque de decisión unificado:

   ```python
   risk_decision = {
       "allow_new_trades": True,
       "force_close_positions": False,
       "size_multiplier": 1.0,
       "stop_signals": [],
       "reasons": [],
   }
   ```

2. Encadenado explícito de guardrails:

   Orden de evaluación en `filter_signal`:

   1. Límites de posición (v0.4).
   2. Guardrail de Drawdown (DD) global.
   3. Stop-loss ATR por posición.
   4. Regla de tamaño por Kelly (v0.4) con motivos integrados.
   5. Sincronización final con `annotated_signal` (`risk_allow`, `risk_reasons`, `risk_decision`).

3. Compatibilidad:

   - Se mantiene el contrato público `(allow, annotated_signal)`.
   - El comportamiento sin guardrails activos es equivalente a v0.4.
   - `RiskManagerV05` es opt-in (activable vía wiring en backtester / config).

---

## 2. Guardrail de Drawdown (DD) global

### 2.1. Lógica

Funciones:

- `compute_drawdown(equity_curve: list[float]) -> Dict[str, Any]`
- `eval_dd_guardrail(dd_value: float, cfg: Dict[str, Any]) -> Dict[str, Any]`

Flujo:

1. A partir de una curva `equity_curve`, se calcula:
   - `max_dd` en `[0, 1]`.
   - Índices de `peak_idx` y `trough_idx` asociados.

2. Con el valor de DD (`dd_value`) y la config `dd_cfg`:

   ```python
   dd_cfg = {
       "max_dd_soft": float,
       "max_dd_hard": float,
       "size_multiplier_soft": float,
   }
   ```

   `eval_dd_guardrail` devuelve un dict:

   ```python
   {
       "state": "normal" | "risk_off_light" | "hard_stop",
       "allow_new_trades": bool,
       "size_multiplier": float,
       "hard_stop": bool,
   }
   ```

### 2.2. Estados y efectos sobre `risk_decision`

Integración en `filter_signal`:

- Si `state == "normal"`:
  - Sin cambios en `risk_decision`.

- Si `state == "risk_off_light"`:
  - `risk_decision["size_multiplier"] = min(size_multiplier, size_multiplier_soft)`
  - Añade motivo `"dd_soft"`.

- Si `state == "hard_stop"`:
  - `risk_decision["allow_new_trades"] = False`
  - `risk_decision["force_close_positions"] = True`
  - `risk_decision["size_multiplier"] = 0.0`
  - `allow = False`
  - Añade motivo `"dd_hard"`.

El guardrail de DD actúa como capa global sobre el resto de reglas.

---

## 3. Guardrail de Stop-Loss basado en ATR

### 3.1. Lógica

Funciones:

- `compute_atr_stop(entry_price, atr, side, cfg) -> float | None`
- `is_stop_triggered(side, stop_price, last_price) -> bool`

Inputs esperados por ticker (`atr_ctx`):

```python
atr_ctx = {
    "TICKER": {
        "entry_price": float,
        "atr": float | None,
        "side": "long" | "short",
        "atr_multiplier": float,
        "min_stop_pct": float,
        "last_price": float,  # opcional, también puede venir vía last_prices
    },
    ...
}
```

Config mínima usada:

- `atr_multiplier`: múltiplo de ATR (ej. `2.5`).
- `min_stop_pct`: % mínimo del precio (ej. `0.02` → 2%).

Reglas:

1. Se calcula una distancia de stop:

   - Distancia mínima porcentual: `price * min_stop_pct`.
   - Distancia ATR: `atr_multiplier * atr` (si ATR válido).
   - Se usa `max(dist_atr, dist_min_pct)` si ATR es válido; si no, solo el mínimo porcentual.

2. Dirección:

   - `side == "long"` → `stop_price = entry_price - distance`
   - `side == "short"` → `stop_price = entry_price + distance`

3. Disparo del stop:

   - Long → disparo si `last_price <= stop_price`.
   - Short → disparo si `last_price >= stop_price`.

### 3.2. Efecto sobre `risk_decision`

En `filter_signal`:

- Si se dispara un stop ATR para un ticker `T`:
  - `risk_decision["stop_signals"].append(T)` (si no está).
  - `risk_decision["reasons"]` incluye `"stop_loss_atr"`.

Este guardrail **no bloquea globalmente** nuevas operaciones por sí mismo; se limita a indicar posiciones que deben cerrarse / recortarse en el ejecutor.

---

## 4. Campos de `risk_rules.yaml` utilizados

Aunque la implementación actual usa defaults robustos si faltan campos, los bloques esperados son:

```yaml
position_limits:
  max_single_asset_pct: 0.10
  max_crypto_pct: 0.30
  max_altcoin_pct: 0.05

major_cryptos:
  - CRYPTO_BTC
  - CRYPTO_ETH

kelly:
  cap_factor: 0.5
  crypto_overrides:
    high_vol: 0.3
    med_vol: 0.4
    low_vol: 0.5
  percentile_thresholds:
    low: 0.5
    high: 0.8

liquidity_filter:
  min_volume_usd: 10000000

dd_guardrail:        # (nomenclatura orientativa)
  max_dd_soft: 0.05
  max_dd_hard: 0.10
  size_multiplier_soft: 0.5

atr_stop:           # (estructura lógica; wiring vía atr_ctx)
  default_atr_multiplier: 2.5
  default_min_stop_pct: 0.02
```

En la versión actual, DD y ATR se configuran principalmente vía kwargs (`dd_cfg`, `atr_ctx`), simulando el wiring futuro desde config centralizada.

---

## 5. Integración con `backtest_initial.py` (wiring mínimo 1C.8)

Archivo:

- `backtest_initial.py`
- Clase: `SimpleBacktester`

Cambios relevantes:

1. Import de `RiskManagerV05` y `os`.
2. Wiring opcional en el bloque `if __name__ == "__main__":`:

   ```python
   rm = None
   rm_version = os.getenv("RISK_MANAGER_VERSION", "none").lower()

   if rm_version == "v0_5":
       rules_path = Path("risk_rules.yaml")
       try:
           rm = RiskManagerV05(rules_path)
           logger.info("Usando RiskManagerV05 con reglas desde %s", rules_path)
       except FileNotFoundError:
           logger.warning(
               "No se encontró %s; se continúa SIN gestor de riesgo.", rules_path
           )
           rm = None

   bt = SimpleBacktester(prices)
   result = bt.run(risk_manager=rm)
   ```

3. El backtester pasa `risk_manager` a `run`, que a su vez lo entrega a `_rebalance`:

   - La curva de equity se mantiene en `self.portfolio_value`.
   - Para E2E futuros, se puede construir `equity_curve` y `dd_cfg` para alimentar DD.
   - `atr_ctx` y `last_prices` se pueden derivar de posiciones y precios en tests más avanzados.

---

## 6. Estados de riesgo y comportamiento esperado

Estados principales combinados:

1. **Estado normal (DD < soft, sin stops ATR, sin límites violados):**
   - `allow_new_trades = True`
   - `force_close_positions = False`
   - `size_multiplier = 1.0`
   - `stop_signals = []`
   - `reasons` vacío o con motivos informativos.

2. **Estado risk_off_light (DD en zona soft):**
   - `allow_new_trades = True`
   - `force_close_positions = False`
   - `size_multiplier < 1.0` (p.ej. 0.5)
   - `reasons` contiene `"dd_soft"`.

3. **Estado hard_stop (DD >= hard):**
   - `allow_new_trades = False`
   - `force_close_positions = True`
   - `size_multiplier = 0.0`
   - `reasons` contiene `"dd_hard"`.

4. **Stop ATR activado para una posición:**
   - `stop_signals` contiene el ticker afectado.
   - `reasons` contiene `"stop_loss_atr"`.
   - No fuerza por sí solo `hard_stop` global.

5. **Límites y Kelly:**
   - Violación de límites → `"position_limits"` y `allow_new_trades = False`.
   - Kelly cap por activo → motivo `"kelly_cap:<asset>"`.

---

## 7. Relación con la spec 1B y el roadmap futuro

- La spec 1B definió guardrails objetivo y estados de riesgo.
- La Fase 1C ha implementado:
  - DD global con estados `"normal" | "risk_off_light" | "hard_stop"`.
  - Stop-loss ATR por posición con `stop_signals`.
  - Bloque `risk_decision` como agregador de motivos y acciones.

Pendiente para fases 1D+:

- Integración completa event-driven (topics Kafka/Redis).
- Wiring de DD y ATR desde config central (`risk_rules.yaml` / engine config).
- Métricas online: ratio de tiempos en cada estado, % de señales bloqueadas por tipo de guardrail.
- Tests E2E dedicados (`test_backtest_risk_v0_5.py`) con escenarios de mercado más ricos.

---

## 8. Resumen final

RiskManager v0.5 aporta:

- Guardrails explícitos de DD global y stop-loss ATR.
- Un punto de decisión unificado (`risk_decision`) que simplifica la auditoría.
- Compatibilidad con la API de v0.4 y wiring opcional en el backtester.

La suite de tests actual (`pytest -q`) se mantiene en verde tras su integración, y se han añadido tests específicos para DD, ATR y `risk_decision`, descritos en la matriz de tests de v0.5 (ver `report/risk_tests_matrix_v0_5_1C_20251201.md`).
