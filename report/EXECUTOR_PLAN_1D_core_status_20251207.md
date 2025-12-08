# EXECUTOR · PLAN 1D.core — Estado final (RiskManager v0.5)

**Fecha:** 2025-12-07  
**Rama de trabajo:** `feature/1D_riskmanager_v0_5_hardening`  
**Commit HEAD 1D.core:** `d2b55c1 1D.core: RiskManager v0.5 hardening (DD/ATR/Kelly wiring)`

---

## 1. Contexto y objetivo de 1D.core

- Punto de partida (1C):
  - RiskManager v0.5 con guardrails de max drawdown global, stop-loss ATR y Kelly sizing integrados.
  - Suite de tests v0.5 verde (DD, ATR, decision, extended).
  - Auditoría multi-IA 1C en `audit/audit_1C_v0_5/*` y reports `report/risk_1C_*`.
- Objetivo 1D.core:
  - Endurecer y clarificar la lógica de riesgo v0.5.
  - Asegurar que el backtester pasa un `risk_ctx` consistente a `risk_manager.filter_signal(...)`.
  - Añadir manejo robusto de casos borde (NaN, contexto de ATR faltante, etc.).
  - Mantener compatibilidad con 1C y con la API pública de `filter_signal` (contrato (allow, annotated)).

---

## 2. Cambios principales en código

### 2.1 backtest_initial.py

- `_rebalance(...)` ahora construye y pasa un contexto de riesgo ampliado a `risk_manager.filter_signal(...)`:

  - `signal`:
    - `deltas` por activo (`target_weight - current_weight`).
    - `assets` (lista de tickers).
  - `current_weights`: pesos actuales de cartera.
  - `nav_eur`: NAV robusto (fallback a `initial_capital` cuando procede).
  - `equity_curve`: curva de NAV utilizada por el guardrail de DD global.
  - `dd_cfg`: parámetros de guardrail DD obtenidos de configuración (no hardcodeados).
  - `atr_ctx`: contexto por ticker para stop-loss ATR (entry_price, atr, side, multiplicadores y mínimos).
  - `last_prices`: últimos precios efectivos por activo.

- Semántica de rebalanceo:
  - Si `filter_signal(...)` devuelve `allow=False`, se registran las razones de riesgo y se aborta el rebalanceo.

### 2.2 risk_manager_v0_5.py

- `filter_signal(...)` consolida la decisión de riesgo en un flujo único, con orden de prioridad:

  1. **Límites de posición (v0.4)** y chequeos de liquidez.
  2. **Guardrail de max drawdown (DD) global**:
     - Usa `compute_drawdown(equity_curve)` y `eval_dd_guardrail(dd_value, dd_cfg)`.
     - Estados: `"normal"`, `"risk_off_light"`, `"hard_stop"`.
     - En `risk_off_light` se reduce `size_multiplier`.
     - En `hard_stop`:
       - `allow_new_trades = False`
       - `force_close_positions = True`
       - `size_multiplier = 0.0`
  3. **Stop-loss ATR por posición**:
     - Recorre `atr_ctx` por ticker.
     - Calcula `stop_price` vía `compute_atr_stop(...)`.
     - Marca tickers con stop activado en `risk_decision["stop_signals"]`.
  4. **Kelly sizing / cap de posición**:
     - Usa `nav_eur` y volatilidad estimada por activo.
     - Limita tamaño máximo por activo.
     - Ajusta deltas y añade razones `kelly_cap:*`.
  5. Sincronización final con la señal anotada:
     - `annotated["risk_allow"]`
     - `annotated["risk_reasons"]`
     - `annotated["risk_decision"]` (estructura unificada).

- Manejo robusto de contexto faltante / corrupto:

  - **DD**:
    - Si `equity_curve` está vacía o solo contiene valores inválidos, el guardrail DD se salta de forma segura.
    - Se marcan flags tipo `dd_skipped` en `risk_decision` / `annotated` y se añaden razones específicas.
  - **ATR**:
    - Si `atr_ctx` no tiene datos suficientes o faltan precios, el guardrail ATR se salta de forma segura.
    - Se marcan flags tipo `atr_skipped` y razones asociadas.
  - Se evita lanzar excepciones en estos casos; el sistema degrada a un modo “safe” y se apoya en logging/warnings.

- Helpers clave:

  - `compute_drawdown(equity_curve)`:
    - Filtra valores no válidos.
    - Devuelve `max_dd` y los índices de pico/foso.
    - Marca el caso de “sin datos utilizables” con un flag específico.
  - `eval_dd_guardrail(dd_value, dd_cfg)`:
    - Aplica umbrales soft/hard y multiplicadores definidos en configuración.
  - `compute_atr_stop(entry_price, atr, side, cfg)`:
    - Normaliza el `side` (long/short).
    - Aplica mínimos/máximos razonables de distancia del stop.
    - Devuelve `None` cuando el stop resultante no es válido.

### 2.3 risk_rules.yaml

- Se ha alineado la sección de max drawdown con el diseño 1D:

  - Umbrales soft/hard expresados como fracción (p.ej. 0.05, 0.10).
  - Multiplicadores de tamaño asociados (p.ej. `size_multiplier_soft`).

- Se han organizado bloques coherentes para:

  - Guardrail de drawdown global.
  - Stop-loss ATR (parámetros por defecto, mínimos/máximos, comportamiento ante datos faltantes).
  - Límites de exposición por activo/sector.
  - Parámetros de Kelly y posibles overrides.

- El fichero está preparado para actuar como “fuente única de verdad” para la configuración de guardrails v0.5.

### 2.4 tests/test_risk_v0_5_extended.py

- Se han añadido/ajustado tests para cubrir:

  - Comportamiento de DD con curvas vacías o con valores inválidos (flags de “DD saltado”).
  - Comportamiento de ATR cuando falta contexto (`atr_ctx` vacío, atr nulo, precios incompletos).
  - Casos donde DD entra en `risk_off_light` y `hard_stop`, y cómo interactúa con el resto de guardrails.
  - Escenarios donde Kelly limita tamaño adicionalmente, manteniendo la prioridad de DD/ATR y límites de posición.

---

## 3. Artefactos de tests y auditoría 1D

- Baseline 1D antes de cambios:
  - `report/pytest_1D_before.txt`
  - `report/pytest_1D_before_raw_first_try.txt`
- Resultado final 1D.core:
  - `report/pytest_20251207_1d_core.txt` → `47 passed in 10.86s`.
  - `report/pytest_1D_core_after.txt` → salida final de pytest en este entorno.
- Walkthrough detallado de implementación 1D.core:
  - `report/backtest_20251207_1d_core_walkthrough.md`.

**Estado de tests a cierre de 1D.core:**

- `python -m pytest -q` → 47 tests pasados, 0 fallos, 0 errores.

---

## 4. Aportación multi-IA específica de 1D

1. **Esquema canónico de configuración de riesgo (Gemini / Grok)**  
   - Definición de un `risk_rules.yaml` estructurado con bloques:
     - `drawdown_guardrail` (soft/hard thresholds, size_multiplier, hysteresis).
     - `atr_stop_loss` (multiplicadores, distancias mín/max, comportamiento ante datos faltantes).
     - `position_limits` (por activo, por sector, apalancamiento).
     - `kelly_sizing` (cap global, buckets de volatilidad y overrides).
   - Introducción del modo `mode: "active" | "monitor"` como futura palanca de despliegue seguro.
   - Propuesta de métricas de observabilidad para monitorizar estados de riesgo y actividad de guardrails.

2. **Contrato de mensajes Backtester ↔ RiskManager (Grok / marco FRAME)**  
   - Esquema explícito de:
     - `signal` (id, strategy_id, timestamp, assets, deltas, metadata).
     - `risk_ctx` (nav, equity_curve, dd_cfg, atr_ctx, last_prices, portfolio_id, etc.).
   - Tabla de comportamiento recomendado cuando faltan campos:
     - Desactivación controlada de DD o ATR + flags/warnings en la señal anotada.
   - Propuesta futura de un dataclass `RiskContext` versionable para blindar el contrato.

3. **Esquema técnico e invariantes (DeepSeek 1D.core)**  
   - Definición de `risk_ctx v0.5` con secciones `portfolio`, `config`, `atr_ctx`, `last_prices`, `env`.
   - Invariantes formales para cada bloque (DD, ATR, Kelly, límites de posición).
   - Pseudocódigo de `filter_signal` ordenando prioridades:
     - position_limits > dd_hard_stop > dd_soft > atr_stop > kelly_cap.
   - Lista ampliada de edge cases para tests (NaN en equity, ATR extremos, config inválida, conflictos entre guardrails, etc.).

La implementación 1D.core realizada en esta rama sigue estas líneas maestras, aunque algunos elementos (dataclass `RiskContext`, modo `monitor`, multi-portfolio completo, observabilidad avanzada) quedan como trabajo futuro.

---

## 5. Preguntas abiertas / Siguientes pasos para el Orchestrator

1. **Integración de contrato `risk_ctx` formalizado**
   - ¿Se debe introducir ya una estructura `RiskContext` (dataclass) en v0.5 o reservarlo para v0.6?
   - Decidir si el paso de contexto será:
     - `risk_manager.filter_signal(signal, current_weights, risk_ctx=dict)` (tal y como está ahora), o
     - `risk_manager.filter_signal(signal, current_weights, risk_ctx=RiskContext)` (nueva firma, manteniendo compatibilidad vía adapter).

2. **Modo `monitor` y despliegue gradual de guardrails**
   - Definir si el modo `monitor` se implementará en v0.5:
     - Solo logging de decisiones de riesgo.
     - Sin bloqueo real de señales de trading.
   - Decidir estrategia de rollout: backtest → paper → live.

3. **Observabilidad y métricas de riesgo**
   - Seleccionar un subconjunto mínimo de métricas para instrumentar primero:
     - Estado de riesgo (NORMAL/SOFT/HARD).
     - Distribución de `risk_reasons`.
     - Frecuencia de stops ATR activados y clipping de distancias.
   - Definir formato de logging/series temporales (JSON estructurado, tags, etc.).

4. **Extensión a multi-portfolio / multi-estrategia**
   - Introducir campos `portfolio_id`, `strategy_id` y posibles `weights_by_portfolio` en el contrato.
   - Diseñar cómo se calcularán y monitorizarán DD y guardrails por portfolio frente a DD global.

5. **Ampliación de test suite 1D → 1E**
   - Convertir parte de la lista de edge cases de DeepSeek en tests unitarios adicionales:
     - Configs inválidas de DD/ATR.
     - Casos extremos de NAV y precios.
     - Conflictos entre guardrails en régimen de alta volatilidad.

---

## 6. Resumen ejecutivo

- 1D.core deja a `RiskManager v0.5` en un estado:

  - Robusto ante datos incompletos o corruptos en DD y ATR.
  - Con un `risk_ctx` explícito desde el backtester, alineado con el marco 1D.
  - Sin romper compatibilidad con la API pública ni con los tests diseñados en 1C.

- La rama `feature/1D_riskmanager_v0_5_hardening` está lista para:

  - Ser sometida a un plan de stress testing y métricas más amplio (posible PLAN 1E).
  - Servir como base para formalizar el contrato `risk_ctx` y la configuración canónica de riesgo en versiones posteriores.

