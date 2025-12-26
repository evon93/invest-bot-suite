# Paso 1B — Blueprint de tests avanzados de riesgo

## 1. Objetivo del blueprint

Definir un catálogo de tests para validar los guardrails de riesgo avanzados descritos en:

- `report/risk_advanced_guardrails_spec_1B_20251127.md`
- `risk_rules.yaml`

El objetivo es que la futura implementación `RiskManager v0.5` pueda ser verificada mediante:

- Tests **unitarios** a nivel de guardrail (max_drawdown, stop_loss_ATR, volatility_stop, liquidez, Kelly/overrides).
- Tests de **integración** con estrategia + backtester.
- Tests de **regresión** para mantener compatibilidad con la API v0.4 y evitar cambios silenciosos de comportamiento.

---

## 2. Matriz de cobertura por guardrail

| Guardrail              | Tipo      | Tests unitarios principales                         | Tests de integración principales                                    |
|------------------------|-----------|-----------------------------------------------------|---------------------------------------------------------------------|
| max_drawdown           | Global    | Cálculo de DD, flags soft/hard, ventanas            | Bloqueo de nuevas señales, reducción de exposición en backtests     |
| stop_loss_ATR          | Por trade | Cálculo de stop, respeto de min_stop_pct            | Coherencia señal-stop, cierre cuando el precio cruza el stop        |
| volatility_stop        | Global    | Clasificación de régimen (normal/alta/extrema)      | Cambio de sizing / bloqueo de señales según régimen                |
| liquidez               | Por activo| Límite por volumen/ADV, comportamiento sin datos    | Rechazo de señales ilíquidas en backtests                           |
| Kelly / overrides      | Por trade | Aplicación de cap_factor, min/max size, per_asset   | Distribución de tamaños en cartera multi-activo                     |

---

## 3. Tests unitarios por guardrail

### 3.1 max_drawdown

**Objetivo:** asegurarse de que el cálculo de drawdown y la lógica de flags funciona como se define en la spec.

Casos mínimos:

1. **DD cero:**  
   - Serie NAV monótona creciente.  
   - Esperado: `max_drawdown=0`, sin flags `dd_risk_off_light` ni `dd_hard_stop`.

2. **DD moderado (por debajo de soft_limit):**  
   - Serie con pequeñas caídas (< soft_limit_pct).  
   - Esperado: ningún flag activo.

3. **DD entre soft_limit y hard_limit:**  
   - NAV cae, DD supera soft_limit pero no hard_limit.  
   - Esperado: flag `dd_risk_off_light=True`, `dd_hard_stop=False`.

4. **DD por encima de hard_limit:**  
   - NAV cae por encima de hard_limit_pct.  
   - Esperado: `dd_hard_stop=True` (y posiblemente `dd_risk_off_light=True`), bloqueo total de nuevas señales.

5. **Ventana de lookback:**  
   - Serie larga con DD antiguo > hard_limit, pero ventana actual por debajo.  
   - Esperado: comportamiento coherente con `lookback_days` (solo cuenta DD reciente).

---

### 3.2 stop_loss_ATR

**Objetivo:** validar el cálculo del stop dinámico por activo y los flags asociados.

Casos mínimos:

1. **Stop básico long:**
   - Precio entrada = 100, ATR(30) = 2, `atr_multiplier=2.5`, `min_stop_pct=0.02`.  
   - Esperado: stop ≈ 100 - max(2.5*2, 0.02*100).

2. **Respeto de min_stop_pct:**
   - ATR muy pequeño (ej. 0.1), `min_stop_pct=0.02`.  
   - Esperado: el stop usa la distancia del 2% y no `atr_multiplier * ATR`.

3. **Caso short:**
   - Precio entrada = 100, posición short, misma ATR.  
   - Esperado: stop por encima del precio de entrada (100 + distancia calculada).

4. **Trigger del stop:**
   - Serie de precios que cruza el nivel de stop.  
   - Esperado: flag `stop_triggered=True` y recomendación de cerrar/ajustar posición.

5. **Falta de datos ATR:**
   - ATR no disponible o ventana insuficiente.  
   - Esperado: política clara (rechazar señal, usar fallback, etc.) según spec.

---

### 3.3 volatility_stop

**Objetivo:** comprobar que el régimen de volatilidad se clasifica correctamente y que se aplican los caps o bloqueos definidos.

Casos mínimos:

1. **Régimen normal:**
   - Volatilidad en percentil medio (ej. 40–60).  
   - Esperado: `vol_regime="normal"`, sin cambios en tamaño.

2. **Régimen alta volatilidad:**
   - Volatilidad > percentil alto (ej. 80).  
   - Esperado: `vol_regime="high"`, multiplicador de tamaño reducido (p.ej. 0.5).

3. **Régimen extrema volatilidad:**
   - Volatilidad en la cola (ej. 95–99).  
   - Esperado: `vol_regime="extreme"`, bloqueo de nuevas señales o tamaño mínimo.

4. **Datos insuficientes:**
   - Ventana insuficiente para percentiles.  
   - Esperado: comportamiento definido (conservador o neutro).

5. **Interacción con Kelly:**
   - Verificar que el multiplicador de volatilidad se aplica sobre el tamaño resultante de Kelly cap.

---

### 3.4 liquidez

**Objetivo:** asegurar que no se operan activos ilíquidos y que el tamaño no viola los límites de volumen.

Casos mínimos:

1. **Activo líquido:**
   - Volumen 24h >> `min_volume_24h_usd`.  
   - Señal de tamaño moderado.  
   - Esperado: `liquidity_ok=True`, sin recortes.

2. **Activo justo en el umbral:**
   - Volumen ≈ `min_volume_24h_usd`.  
   - Señal de tamaño razonable.  
   - Esperado: `liquidity_ok=True` (o política definida en spec).

3. **Activo ilíquido:**
   - Volumen << `min_volume_24h_usd`.  
   - Esperado: `liquidity_ok=False`, flag `liquidity_insufficient`, señal bloqueada.

4. **Orden demasiado grande para el volumen:**
   - Volumen alto, pero el tamaño propuesto supone > X% del volumen/ADV.  
   - Esperado: recorte de tamaño o bloqueo según política.

5. **Falta de datos de liquidez:**
   - Sin datos de volumen/ADV.  
   - Esperado: comportamiento definido (p.ej. bloquear por defecto o marcar como riesgo alto).

---

### 3.5 Kelly / overrides per_asset

**Objetivo:** comprobar que el sizing respeta Kelly cap, min/max trade y overrides por activo.

Casos mínimos:

1. **Kelly global sin overrides:**
   - NAV = 10 000 EUR, señal con edge razonable.  
   - Esperado: tamaño base `nav * kelly_cap_factor` dentro de min/max trade.

2. **Override por volatilidad (low/med/high):**
   - Tres escenarios de volatilidad (percentiles distintos).  
   - Esperado: fracciones diferentes según `low_vol`, `med_vol`, `high_vol`.

3. **Overrides per_asset:**
   - Activos con configuración específica en `risk_rules.yaml` (ej. BTC, SOL).  
   - Esperado: se apliquen los overrides específicos, no solo los globales.

4. **Respeto de min/max_trade_size:**
   - Tamaños calculados por debajo del mínimo o por encima del máximo.  
   - Esperado: se clipean a `min_trade_size_eur` / `max_trade_size_eur`.

5. **Activos sin override:**
   - Activo no listado en `per_asset`.  
   - Esperado: uso de reglas generales y comportamiento consistente.

---

## 4. Tests de integración

### 4.1 Estrategia + RiskManager + Backtester

Diseñar escenarios de backtest que combinen:

1. **Mercado cripto alcista con baja volatilidad:**
   - Esperado: alta utilización de límites de exposición, DD controlado, pocas señales bloqueadas.

2. **Crash brusco (alta volatilidad + drawdown rápido):**
   - Esperado:
     - Activación de `volatility_stop`.
     - Aumento del DD hasta soft/hard_limit dentro de los márgenes previstos.
     - Bloqueo de nuevas entradas y posible cierre parcial/total.

3. **Mercado lateral e ilíquido en algunos activos:**
   - Esperado:
     - Muchas señales rechazadas por liquidez.
     - Poca utilización de límites de Kelly.

4. **Cambio de parámetros en risk_rules.yaml:**
   - Modificar `max_crypto_pct`, `max_altcoin_pct`, `soft_limit_pct`, etc.  
   - Esperado: cambios visibles en:
     - % de señales aceptadas/bloqueadas,
     - DD,
     - exposición media.

### 4.2 Ensayos de regresión

- Confirmar que:
  - La API de `RiskManager` (firma de métodos, tipos de retorno) se mantiene estable.
  - Para config “legacy” (sin nuevos guardrails activados) el comportamiento es equivalente a v0.4 dentro de tolerancias definidas.

---

## 5. Priorización de implementación (hacia 1C)

Orden sugerido para implementar y cubrir con tests:

1. **Liquidez + Kelly/overrides completos**
   - Beneficio inmediato en control de sizing y elegibilidad de activos.
   - Casos de test relativamente acotados.

2. **max_drawdown global**
   - Añade capa de protección a nivel portfolio.
   - Requiere acceso consistente a `equity_curve`/NAV.

3. **volatility_stop**
   - Asegura adaptación a régimen de mercado.
   - Puede aprovechar métricas ya usadas por la estrategia.

4. **stop_loss_ATR**
   - Completa protección por operación.
   - Integra precios de entrada y ATR de cada activo.

Cada bloque de implementación en 1C debería ir acompañado de:

- Nuevos tests unitarios (según secciones 3.1–3.5).
- Al menos un escenario de integración relevante (sección 4).
- Métricas de impacto (DD, Sharpe/Calmar, % señales bloqueadas vs baseline).

---

## 6. Métricas y observabilidad

Para evaluar el efecto de los guardrails de riesgo debería monitorizarse:

- Max drawdown y drawdown medio.
- Volatilidad de la curva de equity.
- Ratio Sharpe/Calmar vs baseline (sin guardrails avanzados).
- % de señales bloqueadas por:
  - max_drawdown,
  - stop_loss_ATR,
  - volatility_stop,
  - liquidez,
  - Kelly/overrides.
- Distribución de tamaños de posición (histograma) antes/después.
- Número de eventos de “hard stop” por periodo.

Estas métricas pueden implementarse como:
- hooks de logging estructurado en `RiskManager`/backtester.
- scripts de análisis sobre los resultados de backtest.

