# RiskManager v0.5 — Auditoría Multi-IA (Fase 1C)
Documento para recopilar hallazgos provenientes de DeepSeek, Gemini, Claude, Grok u otras IAs.

---

## 1. DeepSeek — Informe de Auditoría

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


---

## 2. Gemini — Informe de Auditoría

### 2.1 Resumen ejecutivo
- Lógica core robusta: las funciones de cálculo DD y ATR son correctas y pasan todos los tests.
- Fallo crítico de wiring: el backtester no inyecta `equity_curve` ni `atr_ctx`, dejando los guardrails inactivos.
- Desalineación YAML ↔ código: claves como `soft_limit_pct` no coinciden con las esperadas (`max_dd_soft`).
- Cobertura de tests buena a nivel unitario, pero los tests de integración no detectan el wiring desconectado.

### 2.2 Hallazgos

#### Correctitud lógica
- **[H1] (Severidad 1)** — Wiring desconectado en `backtest_initial.py`. Guardrails DD y ATR nunca se activan.
- **[H2] (Severidad 2)** — Falta de validación/alertas: si faltan `equity_curve` o `atr_ctx`, el sistema falla silenciosamente.

#### Edge cases
- **[H3] (Severidad 3)** — Curva de equity siempre negativa devuelve DD=0%, ocultando comportamientos anómalos.

#### Configuración (`risk_rules.yaml`)
- **[H4] (Severidad 2)** — YAML usa `soft_limit_pct` / `hard_limit_pct`, pero código espera `max_dd_soft` / `max_dd_hard`.
- **[H5] (Severidad 3)** — Demasiada carga cognitiva en el caller: demasiadas dependencias deben inyectarse manualmente.

#### Diseño / claridad
- **[H6] (Severidad 3)** — Ausencia de logging crítico dificulta detectar que los guardrails están funcionando o no.
- **[H7] (Severidad 4)** — Arquitectura viable pero sin mecanismo claro de versiones o auto-configuración.

### 2.3 Recomendaciones
- **[R1] (prioritaria)** — Reparar wiring y pasar `equity_curve`, `atr_ctx`, `dd_cfg`, `last_prices` en todas las llamadas.
- **[R2] (prioritaria)** — Añadir carga automática desde YAML a `RiskManagerV05.__init__`.
- **[R3]** — Añadir avisos/logging cuando un guardrail no puede aplicarse por falta de contexto.
- **[R4]** — Normalizar claves del YAML o implementar un mapeo claro.
- **[R5]** — Añadir tests de integración que verifiquen el wiring real.

### 2.4 Severidades
**Severidad 1–2 (críticos, deben resolverse antes de Fase 1D):**
- H1 — Wiring desconectado.
- H4 — YAML ↔ código desalineado.
- H2 — Falla silenciosa de guardrails.

**Severidad 3–4 (no bloqueantes, corregir después):**
- H3 — DD incorrecto con equity negativa.
- H5 — Carga cognitiva excesiva.
- H6 — Logging insuficiente.
- H7 — Ergonomía de configuración.

---

## 3. Claude — Informe de Auditoría

### 3.1 Resumen ejecutivo
- ...

### 3.2 Hallazgos
#### Correctitud lógica
- ...

#### Edge cases
- ...

#### Configuración (`risk_rules.yaml`)
- ...

#### Diseño / claridad
- ...

### 3.3 Recomendaciones
- ...

### 3.4 Severidades
- ...

---

## 4. Grok — Informe de Auditoría

# Grok — Fase IA.3 (Informe de Auditoría)

## 1. Resumen ejecutivo
- El módulo entregado como RiskManager v0.5 NO implementa el flujo completo descrito en la especificación de Fase 1C.
- Las funciones estáticas (DD, ATR) están bien implementadas y bien testeadas, pero el flujo `filter_signal` / `risk_decision` no existe o no está integrado.
- Los guardrails DD y ATR nunca se aplican realmente en backtests.
- Los tests unitarios pasan porque prueban funciones aisladas, pero los tests de integración no reflejan el wiring real.
- Este estado es bloqueante para avanzar a la Fase 1D.

## 2. Hallazgos por categoría

### 2.1 Correctitud lógica
- **[H1] (Sev. 1)** — Ausencia total de `filter_signal` y `risk_decision` en v0.5.  
  → Ningún guardrail se ejecuta nunca; el sistema opera sin protección.
- **[H2] (Sev. 1)** — `max_drawdown` y `stop_loss` del YAML nunca se leen ni aplican.  
  → Configuración muerta.
- **[H3] (Sev. 2)** — Los tests de integración (`test_risk_decision_v0_5.py`) no pueden pasar contra el código real.  
  → Falta de API esperada por la suite.
- **[H4] (Sev. 2)** — `risk_rules.yaml` declara versión `"0.4"` mientras el proyecto se declara como `"0.5"`.

### 2.2 Edge cases / escenarios extremos
- **[H5] (Sev. 2)** — `compute_drawdown` no maneja explícitamente NaN / inf → resultados silenciosos y poco fiables.  
- **[H6] (Sev. 3)** — Equity curve negativa o cero no tiene semántica documentada (DD=0 en estos casos).
- **[H7] (Sev. 3)** — ATR = 0 o negativo no está testeado en contexto integrado.

### 2.3 Coherencia YAML ↔ Código ↔ Tests
- **[H8] (Sev. 1)** — Desalineación total entre documentación 1C y el código actual.  
  → La especificación describe un flujo que no existe.
- **[H9] (Sev. 2)** — Cobertura de tests unitarios excelente, pero cobertura de integración inexistente.

### 2.4 Diseño / Arquitectura / Extensibilidad
- **[H10] (Sev. 2)** — Acoplamiento excesivo: el caller debe inyectar manualmente todos los contextos, y si falta uno, todo el guardrail se omite sin aviso.
- **[H11] (Sev. 3)** — Falta de logging cuando se activa cualquier guardrail; dificulta auditoría en producción.
- **[H12] (Sev. 4)** — Nomenclatura mejorable (`entry_price` debería ser `reference_price` para futuros trailing stops).

## 3. Recomendaciones concretas
- **[R1]** — Implementar `filter_signal` y `risk_decision` siguiendo exactamente la especificación oficial.  
- **[R2]** — Leer las secciones `max_drawdown` y `stop_loss` del YAML e integrarlas en el manager.  
- **[R3]** — Añadir tests de integración completos:  
  - DD soft (size_multiplier=0.5)  
  - DD hard (bloqueo y cierre forzoso)  
  - stop ATR aplicado  
  - combinación de guardrails  
- **[R4]** — Ajustar `risk_rules.yaml` a `version: "0.5"` una vez implementado.  
- **[R5]** — Añadir logging INFO/WARNING al activar cualquier guardrail.  
- **[R6]** — Integrar `test_risk_v0_5_extended.py` en la suite oficial.

## 4. Prioridades (para EXECUTOR / ORCHESTRATOR)

### Críticos (Severidad 1–2) — deben resolverse ANTES de Fase 1D
- H1 — Falta `filter_signal` y `risk_decision`.  
- H2 — YAML no leído.  
- H3 — Tests integrados no coinciden con API real.  
- H4 — YAML marca versión incorrecta.  
- H8 — Especificación ↔ código desalineado.  
- R1, R2, R3 — Implementación mínima necesaria.

### Fase posterior (Severidad 3–4)
- H5–H7 — Validaciones adicionales (NaN/inf, equity negativa, ATR=0).  
- H10–H12 — Mejoras de arquitectura, logging y nomenclatura.  
- R5, R6 — Extender suite y trazabilidad.


---

## 5. Conclusión agregada (se completa después en AUDIT.5)

### 5.1 Síntesis general
- ...

### 5.2 Issues de severidad 1–2 (para parche inmediato)
- ...

### 5.3 Issues de severidad 3–4 (para fases posteriores)
- ...

