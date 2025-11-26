# Resumen estructurado de `risk_rules.yaml` (v0.3 — 2025-07-03)

## 1. Rebalanceo

- `rebalance.frequency`: **monthly**
- `rebalance.drift_threshold`: **0.03**  
  - Rebalanceo si la deriva de pesos supera el **3%**.
- `rebalance.day_of_month`: **1**  
  - Rebalanceo programado el **día 1** de cada mes.
- `rebalance.execution_window_minutes`: **30**  
  - Ventana de ejecución de **30 minutos** para aplicar el rebalanceo.

---

## 2. Límites de exposición

### 2.1. Límites por activo/sector/cripto

- `position_limits.max_single_asset_pct`: **0.06**  
  - Máx. **6%** del portfolio por activo individual.
- `position_limits.max_sector_pct`: **0.25**  
  - Máx. **25%** del portfolio por sector.
- `position_limits.max_crypto_pct`: **0.12**  
  - Máx. **12%** del portfolio en **cripto** total.
- `position_limits.max_altcoin_pct`: **0.05**  
  - Máx. **5%** del portfolio en **altcoins**.

### 2.2. Clasificación de criptos

- `major_cryptos`:
  - `CRYPTO_BTC`
  - `CRYPTO_ETH`
  - `CRYPTO_USDT`
- Implicación: el universo cripto se separa en **“major_cryptos”** vs **“altcoins”** (el resto), para aplicar límites diferenciados (especialmente `max_altcoin_pct`).

---

## 3. Reglas de stops

### 3.1. Stop-loss dinámico (ATR)

Sección `stop_loss`:

- `method`: `"ATR"`
- `atr_multiplier`: **2.5**
- `lookback_days`: **30**
- `min_stop_pct`: **0.02**
  - Stop mínimo del **2%** aunque el ATR sugiera menos.
- Interpretación:
  - El stop-loss se calcula como **ATR × 2.5** con ventana de **30 días**.
  - Nunca se coloca un stop menor al **2%** desde el punto de entrada.

### 3.2. Volatility stop

Sección `volatility_stop`:

- `enabled`: **true**
- `lookback_days`: **30**
- `percentile`: **0.8**
  - Usar el **percentil 80** de volatilidad a 30 días como umbral.
- Interpretación:
  - Regla de “apagado” o endurecimiento de riesgo cuando la volatilidad reciente está en el tramo superior de su distribución histórica (top 20%).

---

## 4. Kelly capped (gestión de tamaño)

Sección `kelly`:

- Parámetros globales:
  - `cap_factor`: **0.50**
    - Se usa como tope: **máx. 50% de la fracción Kelly** teórica.
  - `min_trade_size_eur`: **20**
  - `max_trade_size_eur`: **400**

- Overrides por nivel de volatilidad en cripto:
  - `crypto_overrides.low_vol`: **0.5**
  - `crypto_overrides.med_vol`: **0.4**
  - `crypto_overrides.high_vol`: **0.3**
  - `crypto_overrides.percentile_thresholds.low`: **0.50**
  - `crypto_overrides.percentile_thresholds.high`: **0.80**
  - Interpretación:
    - Se clasifica la volatilidad en buckets usando percentiles:
      - **< 50%** → low_vol
      - **50–80%** → med_vol
      - **> 80%** → high_vol
    - En cada bucket se aplica un multiplicador de Kelly más conservador cuanto mayor es la volatilidad.

- Overrides por activo:
  - `per_asset.CRYPTO_BTC`:
    - `low_vol`: **0.55**
    - `high_vol`: **0.40**
  - `per_asset.CRYPTO_ETH`:
    - `low_vol`: **0.45**
    - `high_vol`: **0.35**
  - `per_asset.CRYPTO_SOL`:
    - `low_vol`: **0.30**
    - `high_vol`: **0.25**
  - Interpretación:
    - Ajustes finos de fracción efectiva de Kelly por activo, para reflejar perfiles de riesgo diferentes dentro del universo cripto.

---

## 5. Filtros de liquidez

Sección `liquidity_filter`:

- `min_volume_24h_usd`: **10,000,000** (10 M USD)
- Interpretación:
  - Solo se consideran operables los activos con **volumen mínimo de 10M USD en 24h**.
  - Actúa como filtro de elegibilidad previa a cualquier sizing.

---

## 6. Recalibración automática

Sección `recalibration`:

- `window_days`: **90**
- Interpretación:
  - Ventana temporal de **90 días** para procesos de recalibración (p.ej. para reevaluar parámetros a partir de nuevos backtests).
  - En esta versión del YAML **no se referencian explícitamente métricas** como Sharpe/Sortino, solo la ventana.

---

## 7. Drawdown guardrail

Sección `max_drawdown`:

- `soft_limit_pct`: **0.05**
- `hard_limit_pct`: **0.08**
- `lookback_days`: **90**

Interpretación:

- En una ventana de **90 días**:
  - Si el DD cae por debajo de **−5%** → se activa un **soft limit** (probable reducción, freno de riesgo, etc.).
  - Si supera **−8%** → **hard limit** (reglas más estrictas, potencial cierre/reducción fuerte del riesgo).
- La lógica exacta se implementa en `risk_manager_v_0_4.py`, pero el YAML define los umbrales.

---

## 8. Latencia, comisiones y reproducibilidad

- `latency_budget_seconds`: **1.0**
  - Presupuesto de latencia total (1 segundo) para el pipeline de decisión/ejecución.
- `max_fee_pct`: **0.25**
  - Límite de comisión máximo (se asume que la interpretación exacta “en %” la hace el código, pero el YAML fija el umbral numérico).

- Sección `seed`:
  - `seed.python`: **42**
  - `seed.cpp`: **42**
  - `seed.rust`: **42**
  - Interpretación:
    - Semillas compartidas para garantizar reproducibilidad entre implementaciones en distintos lenguajes/módulos.

---

## 9. Metadatos

Sección `meta`:

- `meta.version`: `"0.3"`
- `meta.author`: `"Kai"`
- `meta.checksum`: `"TBD"`

Uso esperado:

- Control de versión del esquema de riesgo.
- Verificación de integridad futura vía `checksum`.
