# Paso 1A — Auditoría de sistema de riesgo

## 1. Contexto

- Rama de trabajo: `orchestrator-v2`
- Fecha: 2025-11-26
- Estado de tests de riesgo **antes** de 1A:
  - `python -m pytest tests/test_risk_suite.py -q` → PASS (guardado en `report/pytest_1A_risk_suite_before.txt`)
  - `python -m pytest tests/test_risk_deepseek.py -q` → PASS (guardado en `report/pytest_1A_risk_deepseek_before.txt`)
- Objetivo de este paso:
  - Entender y documentar el sistema de riesgo actual sin modificar lógica:
    - Reglas declarativas en `risk_rules.yaml`.
    - Implementación en `risk_manager_v_0_4.py` + `risk_manager_v0_4_shim.py`.
    - Tests de riesgo (`test_risk_suite.py`, `test_risk_deepseek.py`) y script de edge cases (`risk_edge_cases.py`).

---

## 2. Resumen de `risk_rules.yaml`

Referencia: `report/risk_rules_summary_1A_20251126.md`.

### 2.1. Rebalanceo

- `rebalance.frequency`: `monthly`
- `rebalance.drift_threshold`: `0.03`
  - Rebalanceo cuando la deriva de pesos supera el 3%.
- `rebalance.day_of_month`: `1`
- `rebalance.execution_window_minutes`: `30`
  - Ventana de ejecución de 30 minutos.

**Implicación:** el sistema está pensado para un rebalanceo discreto mensual + rebalanceo por deriva, pero estas reglas no están aún conectadas al `RiskManager` v0.4.

---

### 2.2. Límites de exposición

- `position_limits.max_single_asset_pct`: `0.06`
  - Máx. 6% del portfolio por activo individual.
- `position_limits.max_sector_pct`: `0.25`
  - Máx. 25% por sector (no implementado en `RiskManager` v0.4).
- `position_limits.max_crypto_pct`: `0.12`
  - Máx. 12% del portfolio en cripto total.
- `position_limits.max_altcoin_pct`: `0.05`
  - Máx. 5% en altcoins (cripto no consideradas “major”).

**Clasificación de criptos**

- `major_cryptos`:
  - `CRYPTO_BTC`
  - `CRYPTO_ETH`
  - `CRYPTO_USDT`

**Implicación:** el YAML distingue claramente entre:
- Exposición total a cripto.
- Exposición a altcoins (no majors).
- Límite por activo y por sector (este último aún sin lógica en código).

---

### 2.3. Reglas de stops

**Stop-loss ATR (`stop_loss`):**

- `method`: `ATR`
- `atr_multiplier`: `2.5`
- `lookback_days`: `30`
- `min_stop_pct`: `0.02`

**Interpretación:**

- Stop-loss dinámico basado en ATR de 30 días, multiplicador 2.5.
- Nunca se coloca un stop inferior al 2% desde el punto de entrada.

**Volatility stop (`volatility_stop`):**

- `enabled`: `true`
- `lookback_days`: `30`
- `percentile`: `0.8`

**Interpretación:**

- Regla para activar “modo defensivo” cuando la volatilidad reciente está en el percentil 80 o superior.

**Estado en la implementación actual:**

- Estas reglas existen en el YAML pero no tienen implementación explícita en `RiskManager` v0.4 (no se calculan stops ni se aplican condiciones de volatility stop en `filter_signal`).

---

### 2.4. Kelly capped y sizing

Sección `kelly`:

- `cap_factor`: `0.50`
  - Tope global de fracción de Kelly (50%).
- `min_trade_size_eur`: `20`
- `max_trade_size_eur`: `400`

**Overrides por volatilidad cripto (`crypto_overrides`):**

- `low_vol`: `0.5`
- `med_vol`: `0.4`
- `high_vol`: `0.3`

**Umbrales de percentil (`percentile_thresholds`):**

- `low`: `0.50`
- `high`: `0.80`

**Overrides por activo (`per_asset`):**

- `CRYPTO_BTC`:
  - `low_vol`: `0.55`
  - `high_vol`: `0.40`
- `CRYPTO_ETH`:
  - `low_vol`: `0.45`
  - `high_vol`: `0.35`
- `CRYPTO_SOL`:
  - `low_vol`: `0.30`
  - `high_vol`: `0.25`

**Implicación:**

- El YAML está diseñado para:
  - Aplicar una fracción de Kelly capada globalmente.
  - Ajustar fracción efectiva según volatilidad (percentiles).
  - Afinar todavía más por activo.
  - Respetar tamaños mínimo/máximo por trade.

**Estado en código:**

- `cap_factor` y `crypto_overrides` + `percentile_thresholds` sí se usan.
- `min_trade_size_eur`, `max_trade_size_eur` y `per_asset` no se usan en `RiskManager` v0.4.

---

### 2.5. Filtros de liquidez

- `liquidity_filter.min_volume_24h_usd`: `10,000,000`

**Implicación:**

- Solo deberían operarse activos con volumen mínimo de 10M USD en 24h.

**Estado en código:**

- Existe `_check_liquidity(asset)` pero es un stub que siempre devuelve `True`.
- El valor `min_volume_24h_usd` no se consulta; la lógica de liquidez está pendiente de implementación real.

---

### 2.6. Recalibración, drawdown y metadatos

**Recalibración (`recalibration`):**

- `window_days`: `90`

**Drawdown (`max_drawdown`):**

- `soft_limit_pct`: `0.05`
- `hard_limit_pct`: `0.08`
- `lookback_days`: `90`

**Otros parámetros:**

- `latency_budget_seconds`: `1.0`
- `max_fee_pct`: `0.25`
- `seed.python`, `seed.cpp`, `seed.rust`: `42`.
- `meta.version`: `"0.3"`, `meta.author`: `"Kai"`, `meta.checksum`: `"TBD"`.

**Estado:**

- Reglas de drawdown, latencia, fees y seeds están definidas como contrato declarativo, pero `RiskManager` v0.4 no las aplica todavía.

---

## 3. API y lógica de `risk_manager_v_0_4.py` + shim

Referencia: `report/risk_manager_contract_1A_20251126.md`.

### 3.1. Construcción de `RiskManager`

- `RiskManager(rules: dict | str | Path)`
  - Acepta un diccionario ya cargado o una ruta a YAML.
  - Internamente:
    - Normaliza `position_limits`, `kelly`, `major_cryptos`, `liquidity_filter`.
    - Inicializa un logger específico del módulo.

---

### 3.2. Métodos principales

**`cap_position_size(asset, nav_eur, vol_pct) -> float`**

- Calcula tamaño máximo en EUR basado en:
  - `kelly.cap_factor` como fracción base.
  - Overrides de `crypto_overrides` + `percentile_thresholds` cuando el activo es cripto “major”.
- Actualmente no usa:
  - Overrides `per_asset`.
  - `min_trade_size_eur` / `max_trade_size_eur`.

**`max_position_size(nav_eur) -> float`**

- Devuelve `nav_eur * max_single_asset_pct`.
- Método auxiliar que no está integrado directamente en `filter_signal`.

**`within_position_limits(alloc: dict[str, float]) -> bool`**

- Valida limites de posición a nivel de cartera:
  - `max_single_asset_pct` por activo.
  - `max_crypto_pct` para suma de todos los activos `CRYPTO_*`.
  - `max_altcoin_pct` para suma de cripto no incluidas en `major_cryptos`.
- No usa `max_sector_pct`.
- No diferencia sectores para acciones, solo cripto vs altcoins.

**`filter_signal(signal: dict, current_weights: dict, nav_eur: float | None = None, **kwargs) -> (bool, dict)`**

- Punto de entrada “oficial” de riesgo.
- Lógica:
  1. Comprueba `within_position_limits(current_weights)`.
     - Si falla → `allow = False`, motivo `"position_limits"`.
  2. Aplica `_check_liquidity(asset)` a cada activo de la señal.
     - Actualmente siempre `True` → sin efecto real.
  3. Si `nav_eur` está definido:
     - Para cada `asset, target_weight` en `signal["deltas"]`:
       - Obtiene `vol_pct` con `_get_volatility(asset)` (stub fijo 0.65).
       - Limita el peso por `cap_position_size`.
       - Si clipea → añade motivo `"kelly_cap:{asset}"`.
  4. Anota:
     - `annotated["risk_allow"] = allow`
     - `annotated["risk_reasons"] = reasons`
- Devuelve:
  - `allow: bool`
  - `annotated_signal: dict` (señal original + anotaciones y posibles ajustes de pesos).

---

### 3.3. Shim `risk_manager_v0_4_shim.py`

- Función principal del shim:
  - Resolver automáticamente si el módulo real se llama:
    - `risk_manager_v0_4.py` o
    - `risk_manager_v_0_4.py`.
  - Cargarlo con `importlib` y exponer:

    ```python
    from risk_manager_v0_4_shim import RiskManager
    ```

- El shim cachea el módulo y simplifica el contrato externo:
  - El resto del sistema debe depender solo del shim, no del archivo físico.

---

### 3.4. Brecha YAML ↔ implementación

- Implementado en `RiskManager` v0.4:
  - Límites por activo (`max_single_asset_pct`).
  - Límites por cripto total (`max_crypto_pct`) y altcoins (`max_altcoin_pct`).
  - Kelly cap básico (`cap_factor` + `crypto_overrides` + `percentile_thresholds`).
  - Diferenciación majors vs altcoins a partir de `major_cryptos`.

- Definido en `risk_rules.yaml` pero no implementado aquí:
  - `max_sector_pct`.
  - Overrides `kelly.per_asset` por activo.
  - `min_trade_size_eur` / `max_trade_size_eur`.
  - Stop-loss ATR y volatility stop.
  - Guardrails de drawdown (soft/hard).
  - Liquidity filter real (mínimo volumen 24h).
  - Reglas de rebalance, recalibración, latencia y fees.

---

## 4. Cobertura de tests de riesgo

Referencia: `report/risk_tests_matrix_1A_20251126.md`.

### 4.1. Qué comprueban los tests actuales

**`tests/test_risk_suite.py`**

- Verifica que:
  - `RiskManager` se importa correctamente vía shim.
  - La clase expone métodos clave (`within_position_limits`, `filter_signal`, `max_position_size`).
  - `within_position_limits` respeta `max_single_asset_pct` en casos simples.
  - `filter_signal` devuelve `(bool, dict)` y no rompe tipos.
  - `max_position_size(nav_eur)` produce tamaños coherentes (`<= nav_eur`).

**`tests/test_risk_deepseek.py`**

- Refuerza compatibilidad tras cambios:
  - Comprueba que `within_position_limits` sigue respetando un `max_single_asset_pct` más estricto (ej. 5%).
  - Comprueba que `cap_position_size` no da tamaños absurdos para casos de Kelly con parámetros distintos.

**`risk_edge_cases.py`**

- Es un smoke test mínimo (assert trivial):
  - Confirma que el entorno de ejecución funciona.
  - No contiene lógica de riesgo real.

---

### 4.2. Cobertura efectiva sobre el contrato de riesgo

- Cubierto:
  - Import estable de `RiskManager` vía shim.
  - Existencia de API pública mínima.
  - Límite por activo (`max_single_asset_pct`) en escenarios sencillos.
  - Kelly cap básico no produce tamaños fuera de rango.

- No cubierto:
  - Casos con múltiples activos donde:
    - Se violen límites `max_crypto_pct` y `max_altcoin_pct`.
    - Haya mezcla de majors y altcoins.
  - Overrides `kelly.per_asset`.
  - Reglas de stop-loss, volatility stop, drawdown, liquidez real.
  - Escenarios de integración estrategia–riesgo–backtest donde cambios en el YAML alteren el comportamiento.

---

## 5. Coherencia con objetivos de riesgo del proyecto

> Nota: esta sección debe revisarse contra `README.md` y `architecture.md` del repo en local; aquí se evalúa sólo con `risk_rules.yaml` + `RiskManager` v0.4.

### 5.1. Coherencias

- El uso de:
  - Límite por activo (6%).
  - Límite por cripto total (12%).
  - Límite por altcoins (5%).
  sugiere un diseño orientado a:
  - Mantener exposición controlada a activos volátiles.
  - Evitar concentración excesiva en nichos (altcoins).
- La existencia de:
  - Kelly cap (`cap_factor=0.5`).
  - Overrides por volatilidad y por activo.
  indica una intención clara de:
  - Priorizar estabilidad de drawdown frente a maximización “pura” de Kelly.

### 5.2. Incoherencias / huecos visibles

- El YAML define:
  - Stop-loss ATR.
  - Volatility stop.
  - Guardrails de drawdown (soft/hard).
  - Límites sectoriales (`max_sector_pct`).
  pero el `RiskManager` v0.4 no consume estos parámetros:
  - No hay lógica de stops ligada a ATR.
  - No se usa volatilidad histórica real ni percentiles de mercado.
  - No se aplica ninguna lógica de drawdown máximo.
  - No se diferencia por sector en renta variable.

**Riesgo:** el sistema puede aparentar tener un marco de control de riesgo más completo de lo que realmente se ejecuta en código.

### 5.3. Acciones recomendadas (a validar en 1B/1C)

- Revisar `README.md` y `architecture.md` para:
  - Confirmar el objetivo de drawdown máximo (ej. 10–15%).
  - Confirmar límites de apalancamiento y exposición objetivo por tipo de activo.
- Una vez confirmados:
  - Alinear explícitamente:
    - `max_drawdown` del YAML con la lógica que se implemente.
    - Límites de exposición (valores numéricos) con lo que se documente como objetivo del sistema.

---

## 6. Recomendaciones para próximos pasos (1B/1C)

### 6.1. API más limpia para integración con backtester

- Mantener el shim como punto único de entrada:

  ```python
  from risk_manager_v0_4_shim import RiskManager
Normalizar la interfaz del RiskManager a algo del estilo:

rm = RiskManager(rules_dict)

allow, annotated = rm.filter_signal(
    signal=signal_dict,
    current_weights=current_weights,
    nav_eur=current_nav,
    context=context_dict,  # régimen de mercado, métricas de DD, etc.
)


A largo plazo, separar explícitamente:

Filtros de exposición (posición/cripto/altcoins/sector).

Filtros de liquidez.

Sizing (Kelly, caps).

Stops + drawdown.

6.2. Nuevos tests deseables

Tests unitarios adicionales (extender tests/test_risk_suite.py y/o crear tests/test_risk_limits_extended.py):

Límites combinados cripto/altcoins:

Cartera con mezcla de majors y altcoins que:

Respete max_crypto_pct y max_altcoin_pct.

Los exceda de forma controlada.

Verificar bloqueos correctos y mensajes en risk_reasons.

Kelly en multi-activo:

Señales con varios activos con distintos target_weight y nav_eur realista.

Comprobar que todos los pesos se clipean correctamente y que allow refleja la violación cuando corresponde.

Tests de regresión de API:

Asegurar que futuros cambios no rompen:

La firma de RiskManager.

El contrato del shim.

Tests de integración (cuando backtester esté más maduro):

Casos donde se modifiquen parámetros de risk_rules.yaml (p. ej. max_crypto_pct) y se observe el impacto en:

% de señales bloqueadas.

Exposición efectiva resultante en backtests.

6.3. Cambios de configuración sugeridos (aún sin implementar)

Revisar si:

max_single_asset_pct = 0.06

max_crypto_pct = 0.12

max_altcoin_pct = 0.05
son coherentes con el objetivo de DD máximo real y con la volatilidad histórica de los activos.

Decidir una política realista para:

min_trade_size_eur / max_trade_size_eur:

Integrarlos en cap_position_size o en un paso posterior de sizing.

Overrides per_asset:

Activarlos de forma explícita para activos con comportamiento muy particular (BTC vs SOL, etc.).

7. Resumen ejecutivo (takeaways clave)

risk_rules.yaml define un marco de riesgo rico (límites, Kelly avanzado, stops, drawdown, liquidez), pero:

RiskManager v0.4 solo implementa hoy:

Límites por activo y cripto/altcoins.

Una parte del Kelly cap (sin min/max trade ni overrides por activo).

Stubs para liquidez y volatilidad sin lógica real.

Los tests actuales son buenos para API y límites básicos, pero:

No cubren escenarios multi-activo ni reglas avanzadas (stops, drawdown).

Para 1B/1C se recomienda:

Extender tests para cubrir los límites existentes.

Diseñar la implementación progresiva de stops, drawdown y liquidez real.

Alinear los parámetros del YAML con los objetivos de riesgo documentados en README/architecture.