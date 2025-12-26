# Informe Auditoría — DeepSeek (Fase 1C · RiskManager v0.5)

## 1. Resumen ejecutivo

- Los guardrails de **Drawdown Global (DD)** y **stop-loss ATR** están bien implementados a nivel básico y pasan los 47 tests actuales.
- Hay **desalineaciones críticas de configuración** entre `risk_rules.yaml` y lo que espera el código, que pueden dejar guardrails inactivos en producción.
- El **wiring en backtest** no alimenta correctamente los contextos de riesgo (equity_curve, atr_ctx, etc.), por lo que los guardrails no se ejercen en backtests E2E.
- Los tests cubren los casos principales, pero faltan **edge cases numéricos y configuraciones inválidas**.
- La arquitectura (factory + risk_decision) es adecuada para extender en 1D+ (volatilidad, liquidez, etc.).

---

## 2. Hallazgos por categoría

### 2.1 Correctitud lógica

- **H1 (Sev. 2)** — Cálculo de DD con peak inicial fijo: `compute_drawdown` toma el primer valor de la equity curve como máximo inicial; si el máximo real ocurre después, el DD se subestima.
- **H2 (Sev. 3)** — NaN en equity curve: valores NaN no se tratan explícitamente; no rompen el cálculo pero pueden ocultar problemas de datos.
- **H3 (Sev. 2)** — Inconsistencia en `side` para stop ATR: `compute_atr_stop` normaliza `side` a minúsculas, pero `is_stop_triggered` no; un `side="LONG"` podría no disparar correctamente.
- **H4 (Sev. 3)** — Stubs no implementados (`_get_volatility`, `_check_liquidity`): devuelven constantes triviales y pueden generar falsa sensación de control si se usan sin completar.

### 2.2 Edge cases / escenarios extremos

- **H5 (Sev. 2)** — Stop ATR con distancias extremas: combinaciones de `atr` muy alto y `atr_multiplier` grande pueden producir stops irreales (p. ej. stop negativo en un long).
- **H6 (Sev. 3)** — Valores no finitos en equity curve: presencia de `inf`/`NaN` puede distorsionar el HWM y el DD sin detección explícita.
- **H7 (Sev. 3)** — Umbrales DD incoherentes: si `max_dd_soft > max_dd_hard`, el estado `hard_stop` puede no activarse nunca; no hay validación de esta configuración.

### 2.3 Coherencia con configuración (`risk_rules.yaml`)

- **H8 (Sev. 1)** — Desalineación de nombres para DD: el código espera claves tipo `max_dd_soft` / `max_dd_hard`, mientras el YAML usa `soft_limit_pct` / `hard_limit_pct` bajo `max_drawdown`. Esto puede dejar el guardrail de DD sin efecto si no se mapea correctamente.
- **H9 (Sev. 2)** — `size_multiplier_soft` ausente en YAML: se usa un valor por defecto en código pero no está configurado en `risk_rules.yaml`.
- **H10 (Sev. 2)** — Estructura para stop-loss distinta: la sección `stop_loss` del YAML no se traduce directamente al `cfg` que espera el código; la estructura anidada no se aprovecha y puede crear confusión.

### 2.4 Diseño / claridad / extensibilidad

- **H11 (Sev. 2)** — Wiring incompleto en backtest: `backtest_initial.py` instancia v0.5 pero no pasa `equity_curve`, `dd_cfg`, `atr_ctx`, `last_prices` a `filter_signal`, dejando los guardrails de riesgo inactivos en la práctica.
- **H12 (Sev. 3)** — Orden de aplicación de Kelly tras `hard_stop`: se sigue evaluando Kelly incluso cuando DD está en `hard_stop` (size_multiplier=0); es redundante y puede confundir la lectura del flujo.
- **H13 (Sev. 3)** — Semántica poco clara de `force_close_positions`: no está bien documentado si implica cerrar todo o solo posiciones afectadas; falta precisión en docstrings.
- **H14 (Sev. 4)** — Versión fija en factory: el YAML sigue marcando versión 0.4; usar v0.5 requiere modificar manualmente el YAML, lo que resta ergonomía.

---

## 3. Recomendaciones concretas (según DeepSeek)

- **R1 — Alinear `risk_rules.yaml` con el código**  
  Unificar nomenclatura (`soft_limit_pct`/`hard_limit_pct` ↔ `max_dd_soft`/`max_dd_hard`) y añadir explícitamente `size_multiplier_soft`, o introducir una capa de mapeo clara en el constructor de `RiskManagerV05`.

- **R2 — Completar wiring en `backtest_initial.py`**  
  Construir y pasar explícitamente:
  - `equity_curve` (histórico de `portfolio_value`),
  - `dd_cfg` (derivado del YAML),
  - `atr_ctx` (ATR y contexto por activo),
  - `last_prices` (precios actuales),
  a las llamadas de `filter_signal` para activar realmente los guardrails en los backtests.

- **R3 — Validación de datos en `compute_drawdown`**  
  Ignorar o loguear NAV no finitos (NaN/inf) de forma explícita y, opcionalmente, lanzar avisos si el input es sospechoso.

- **R4 — Normalizar `side` en `is_stop_triggered`**  
  Convertir `side` a minúsculas al entrar en la función para ser coherente con `compute_atr_stop` y evitar errores por mayúsculas.

- **R5 — Tests adicionales de edge cases**  
  Añadir tests que cubran:
  - `atr_multiplier <= 0`,
  - `min_stop_pct = 0`,
  - configuraciones DD con `max_dd_soft > max_dd_hard`,
  - equity curve con un solo punto,
  - valores `side` en mayúsculas / mixtos.

- **R6 — Documentar `force_close_positions`**  
  Precisar en docstrings y documentación qué implica exactamente este flag y cómo lo debe interpretar la capa de ejecución.

- **R7 — Implementar stubs mínimos útiles**  
  Dar una implementación sencilla pero realista a `_get_volatility` y `_check_liquidity` (por ejemplo, volatilidad histórica rolling y chequeo de volumen mínimo), o marcar claramente que no deben usarse aún en producción.

---

## 4. Prioridades para 1D (según DeepSeek)

### 4.1 Deben resolverse antes de Fase 1D (Severidad 1–2)

1. **H8 (Sev. 1)** — Desalineación de nombres DD en `risk_rules.yaml`.  
2. **H1 (Sev. 2)** — Cálculo de DD con peak inicial fijo.  
3. **H5 (Sev. 2)** — Stop ATR con distancias extremas.  
4. **H11 (Sev. 2)** — Wiring incompleto en backtest.  
5. **H3 (Sev. 2)** — Validación de `side` en stop ATR.  
6. **H9 (Sev. 2)** — Falta de `size_multiplier_soft` en YAML.

### 4.2 Mejoras para fases posteriores (Severidad 3–4)

1. **H2 / H6 / H7** — Tratamiento y validación de datos no finitos y configuraciones incoherentes de DD.  
2. **H12 / H13** — Claridad de flujo (Kelly tras hard_stop) y documentación de `force_close_positions`.  
3. **H4 / H14** — Completar stubs de volatilidad/liquidez y mejorar ergonomía de selección de versión en el factory.

