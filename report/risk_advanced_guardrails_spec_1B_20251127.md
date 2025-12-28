# Paso 1B — Spec de guardrails de riesgo avanzados

## 1. Marco objetivo (README + risk_rules)

El sistema de riesgo busca proteger el capital y garantizar la supervivencia de la estrategia a largo plazo mediante una arquitectura de defensa en profundidad. Los objetivos fundamentales derivados de `risk_rules.yaml` y la arquitectura implícita son:

1.  **Supervivencia (Anti-Ruina):** Evitar pérdidas catastróficas mediante límites duros de exposición (`max_single_asset_pct`, `max_crypto_pct`) y un "freno de emergencia" basado en Drawdown (`max_drawdown`).
2.  **Adaptabilidad al Régimen:** Ajustar el tamaño de las posiciones dinámicamente según la volatilidad del mercado (`volatility_stop`, Kelly overrides) para reducir riesgo en entornos turbulentos.
3.  **Protección por Operación:** Limitar las pérdidas de cada trade individual basándose en su volatilidad intrínseca (`stop_loss` ATR).
4.  **Operabilidad Realista:** Asegurar que solo se opera en activos líquidos (`liquidity_filter`) para minimizar deslizamiento (slippage) e impacto de mercado.

El contrato actual en `risk_rules.yaml` define estos parámetros, pero la implementación v0.4 es parcial. Esta spec define cómo cerrar esa brecha.

## 2. Estado actual (v0.4, resumen 1A)

**Implementado en v0.4:**
*   **Límites de posición estáticos:** `max_single_asset_pct`, `max_crypto_pct`, `max_altcoin_pct`.
*   **Kelly Cap básico:** Cálculo de tamaño máximo basado en `cap_factor` y overrides simples de volatilidad para "major cryptos".
*   **Infraestructura:** Clase `RiskManager` con carga de YAML y Shim de compatibilidad.

**Existente en YAML pero NO implementado (Stubs o ignorado):**
*   **Stop-loss dinámico (ATR):** Definido pero no calculado ni devuelto en la señal anotada.
*   **Volatility Stop:** Definido (`percentile: 0.8`) pero sin lógica de evaluación de régimen de mercado.
*   **Liquidez:** Stub `_check_liquidity` que siempre devuelve `True`.
*   **Max Drawdown:** Definido (`soft`/`hard` limits) pero sin estado ni lógica de bloqueo.
*   **Overrides finos:** `per_asset` y `min/max_trade_size_eur` ignorados.

## 3. Guardrails objetivo (descripción funcional)

### 3.1 max_drawdown
Mecanismo de defensa a nivel de portafolio. Debe monitorizar el NAV actual frente a su pico histórico (High Water Mark) en una ventana deslizante (ej. 90 días).
*   **Soft Limit (-5%):** Si se cruza, el sistema entra en modo "precaución". Se prohíbe aumentar exposición neta (nuevas compras solo si se reduce riesgo en otro lado) o se reduce el `cap_factor` de Kelly globalmente.
*   **Hard Limit (-8%):** Si se cruza, se bloquean todas las nuevas aperturas de posición. Solo se permiten cierres o reducciones. Se podría forzar una liquidación parcial (fuera del scope de v0.5, pero el bloqueo es mandatorio).

### 3.2 stop_loss_ATR
Protección a nivel de trade individual. Para cada señal de entrada, se debe calcular un precio de stop-loss dinámico.
*   El stop se sitúa a una distancia de `N * ATR(30)` del precio de entrada.
*   Existe una distancia mínima garantizada (`min_stop_pct`) para evitar stops demasiado ajustados en periodos de calma artificial.
*   Este precio de stop debe viajar con la señal anotada para que el ejecutor (bot) lo coloque en el mercado o lo gestione virtualmente.

### 3.3 volatility_stop
Filtro de régimen de mercado. Antes de procesar cualquier señal de compra, se evalúa la volatilidad del activo o del mercado general.
*   Si la volatilidad actual (ej. ATR relativo o desviación estándar) está en el percentil superior (ej. >80% histórico), se asume un régimen de "alta incertidumbre".
*   Acción: Bloquear nuevas entradas (`allow=False`) o reducir drásticamente el tamaño permitido (ej. forzar `low_vol` override).

### 3.4 liquidez
Filtro de elegibilidad. Evita operar en "fantasmas" o activos ilíquidos donde el slippage destruiría el alpha.
*   Verificar si el volumen promedio de 24h (o media de X días) supera `min_volume_24h_usd`.
*   Si no cumple, la señal se rechaza inmediatamente (`allow=False`) con razón `liquidity_low`.

### 3.5 Kelly / overrides per_asset
Refinamiento del sizing.
*   Aplicar los overrides específicos definidos en `per_asset` (ej. BTC vs SOL) si existen.
*   Respetar estrictamente `min_trade_size_eur` (para no enviar órdenes ridículas que el exchange rechace) y `max_trade_size_eur` (para no concentrar riesgo operativo en una sola orden).

## 4. Semántica propuesta de cada guardrail (inputs/outputs/decisiones)

### 4.1 max_drawdown
*   **Inputs:** `current_nav`, `historical_nav_series` (o `peak_nav_90d`).
*   **Lógica:** Calcular `current_dd_pct = (current_nav - peak_nav) / peak_nav`.
*   **Outputs:**
    *   Estado: `NORMAL` | `SOFT_LIMIT` | `HARD_LIMIT`.
    *   Acción en `filter_signal`: Si `HARD_LIMIT`, `allow=False` (salvo que sea venta/reducción). Si `SOFT_LIMIT`, aplicar factor de reducción a `max_position_size`.

### 4.2 stop_loss_ATR
*   **Inputs:** `entry_price`, `asset_history` (OHLC para calcular ATR).
*   **Lógica:** `atr_val = ATR(history, 30)`; `dist = max(atr_val * 2.5, entry_price * 0.02)`; `stop_price = entry_price - dist` (para largos).
*   **Outputs:**
    *   Campo en `annotated_signal`: `stop_loss_price` y `stop_loss_pct`.

### 4.3 volatility_stop
*   **Inputs:** `asset_history` (para calcular volatilidad actual y percentiles históricos).
*   **Lógica:** `current_vol = ...`; `threshold = percentile(history_vol, 0.8)`; `is_high_vol = current_vol > threshold`.
*   **Outputs:**
    *   Decisión: Si `is_high_vol` es True, `allow=False` (o reducción severa).
    *   Razón: `"volatility_regime_high"`.

### 4.4 liquidez
*   **Inputs:** `asset_metadata` (volumen 24h).
*   **Lógica:** `volume_usd >= 10_000_000`.
*   **Outputs:**
    *   Decisión: `allow=True/False`.
    *   Razón: `"liquidity_insufficient"`.

### 4.5 overrides per_asset
*   **Inputs:** `asset_id`, `nav_eur`, `vol_regime`.
*   **Lógica:** Buscar config específica en `kelly.per_asset[asset_id]`. Si existe, usar sus params en lugar de los genéricos. Aplicar `clamp(size, min_trade, max_trade)`.
*   **Outputs:**
    *   `target_eur` ajustado.
    *   Razón (si se clipea): `"kelly_cap_asset_specific"`, `"min_trade_size"`.

## 5. Prioridad de implementación (para 1C)

Se propone un enfoque incremental para RiskManager v0.5:

1.  **Prioridad ALTA (Fundamentos):**
    *   **Liquidez:** Fácil de implementar, evita errores costosos en live.
    *   **Kelly Completo (`min/max` + `per_asset`):** Cierra la lógica de sizing para evitar órdenes inválidas.

2.  **Prioridad MEDIA (Protección Activa):**
    *   **Stop-loss ATR:** Crítico para la gestión del trade, pero requiere acceso a datos históricos (OHLC) dentro del RiskManager, lo cual añade complejidad de I/O.
    *   **Volatility Stop:** Similar al anterior, depende de datos históricos.

3.  **Prioridad BAJA (Estado Complejo):**
    *   **Max Drawdown:** Requiere persistencia del estado del portafolio (trackear el High Water Mark entre ejecuciones). Se puede diferir o implementar una versión "stateless" si el NAV histórico se pasa como argumento.

**Plan sugerido para 1C:** Implementar **Liquidez** y **Kelly Completo**. Preparar la interfaz para recibir datos históricos (necesarios para ATR/Volatilidad) sin implementarlos todavía si la inyección de datos es compleja.

## 6. Riesgos y consideraciones

*   **Dependencia de Datos (Data Fetching):** Para calcular ATR y percentiles de volatilidad, el `RiskManager` deja de ser una función pura de `(signal, rules)` y necesita `history`. Esto puede introducir latencia o acoplamiento con el proveedor de datos.
    *   *Mitigación:* Pasar los datos pre-calculados o el dataframe de historia en el contexto de `filter_signal`, manteniendo el RiskManager "puro" y sin I/O directo.
*   **Persistencia de Estado (Drawdown):** El RiskManager actual no tiene memoria. Para `max_drawdown`, necesita saber el pico de NAV de los últimos 90 días.
    *   *Mitigación:* El orquestador debe proveer este estado al llamar a `filter_signal`, o el RiskManager debe tener una base de datos/archivo de estado propio.
*   **Latencia:** Calcular ATR y percentiles al vuelo para muchos activos puede ser lento.
    *   *Mitigación:* Caching o pre-cálculo en el loop del orquestador.
*   **Sobre-optimización:** Los overrides `per_asset` pueden llevar a overfitting si se ajustan demasiado fino a backtests pasados.

## 7. Integración event-driven

### 7.1 Flujo base de eventos

El flujo lógico (según README/arquitectura) es:

1. `strategy_engine` emite señales “crudas” de rebalanceo:
   - Evento lógico: **SignalEvent (raw)**
   - Contenido mínimo:
     - `timestamp`
     - `deltas` o `target_weights` por activo
     - `assets` afectados
     - metadatos de estrategia (id, nombre, etc.).

2. `risk_manager` recibe la señal junto con el estado de cartera y features de mercado y devuelve:
   - `allow: bool`
   - `annotated_signal: dict` con:
     - `risk_allow`, `risk_reasons`
     - anotaciones de guardrails (DD, liquidez, stops, etc.).

3. El backtester / live executor consume la señal ya filtrada:
   - Evento lógico: **SignalEvent (risk_filtered)**  
   - Solo se ejecutan órdenes cuando `risk_allow=True`.

### 7.2 Eventos y campos adicionales necesarios

Para soportar los guardrails avanzados, el orquestador debe mantener y/o enriquecer estos flujos con eventos auxiliares:

1. **PortfolioSnapshotEvent**
   - Fuente: backtester / live executor.
   - Campos mínimos:
     - `timestamp`
     - `nav` (equity / NAV actual)
     - `peak_nav` (NAV máximo histórico o en ventana)
     - `drawdown_pct` (opcional si viene pre-calculado).

2. **MarketFeaturesEvent**
   - Fuente: módulo de datos/indicadores.
   - Campos por activo:
     - `atr_30` (ATR en 30 barras o ventana configurada)
     - `volatility_pct` / `vol_regime_score`
     - `volume_24h_usd`
     - `adv_usd` (si está disponible)
     - cualquier tag útil (`is_major_crypto`, sector, etc.).

3. **PerAssetConfig / Tags**
   - Fuente: `risk_rules.yaml` (per_asset, crypto_overrides, etc.).
   - No es un evento en sí, pero su contenido debe estar accesible al RiskManager.

### 7.3 Contrato práctico de `filter_signal` en el pipeline

La firma actual de v0.4 ya permite extensión vía `**kwargs`:

```python
allow, annotated = risk_manager.filter_signal(
    signal,                      # dict con deltas/weights y metadatos
    current_weights,             # pesos actuales por activo
    nav_eur=nav,                 # NAV actual
    context={
        "dd_state": {
            "nav": nav,
            "peak_nav": peak_nav,
            "drawdown_pct": drawdown_pct,
        },
        "atr": {
            "BTC": atr_btc,
            "ETH": atr_eth,
            # ...
        },
        "vol_regime": {
            "label": "normal" | "high" | "extreme",
            "score": vol_regime_score,   # opcional
        },
        "liquidity": {
            "BTC": {"volume_24h_usd": v_btc, "adv_usd": adv_btc},
            "SOL": {"volume_24h_usd": v_sol, "adv_usd": adv_sol},
            # ...
        },
        "per_asset_tags": {
            "BTC": {"class": "major_crypto"},
            "SOL": {"class": "altcoin_high_beta"},
            # ...
        },
    },
)
Puntos clave del contrato propuesto:

No se rompe la API existente: filter_signal sigue aceptando signal, current_weights, nav_eur, **kwargs.

Toda la información para DD, ATR, volatilidad y liquidez entra por context:

max_drawdown consume context["dd_state"].

stop_loss_ATR consume context["atr"] + precios/side de la señal.

volatility_stop consume context["vol_regime"].

liquidez consume context["liquidity"].

Kelly/overrides puede usar per_asset_tags y config YAML.

El resultado (annotated) debe incluir, además de risk_allow/risk_reasons, campos opcionales como:

risk_annotations.max_drawdown

risk_annotations.stop_levels

risk_annotations.vol_regime

risk_annotations.liquidity

risk_annotations.kelly_size_eur

para facilitar logging y análisis posterior.

7.4 Backtester vs live

Backtester:

Puede pre-calcular ATR, volatilidad, volumen y DD para todo el histórico y pasarlo en cada llamada a filter_signal.

Permite experimentar con diferentes políticas de guardrails sin tocar la infraestructura live.

Live executor:

Debe mantener un estado incremental:

nav y peak_nav en memoria o storage ligero.

buffers de precios/volúmenes recientes por activo.

Debe garantizar que, antes de invocar filter_signal, los campos de context están lo suficientemente actualizados como para que los guardrails tomen decisiones coherentes (especialmente en mercados volátiles).