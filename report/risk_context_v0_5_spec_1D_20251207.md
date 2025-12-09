# RiskContext v0.5 — Contrato lógico (PLAN 1D)

Objetivo del documento:

- Definir el contrato de contexto de riesgo que consume RiskManagerV05.filter_signal(...) en v0.5.
- Mantener firma pública estable (kwargs planos en v0.5) pero documentando ya la estructura conceptual risk_ctx que se formalizará como dataclass en Plan 2A/v0.6.
- Documentar el comportamiento esperado cuando faltan campos (guardrail desactivado + flags) y las métricas mínimas de observabilidad.

En código v0.5, estos campos se pasan como kwargs:

- nav_eur
- equity_curve
- dd_cfg
- atr_ctx
- last_prices

Conceptualmente, todos ellos forman un único mensaje de contexto:

risk_ctx:
  portfolio: ...
  prices: ...
  atr_ctx: ...
  config: ...
  # campos futuros: env, portfolio_id, strategy_id, etc.

----------------------------------------------------------------------
1. Bloque portfolio
----------------------------------------------------------------------

Representa el estado agregado del portfolio en el momento de evaluar la señal.

1.1 Campos

- nav_eur: float
  - Tipo: número real (float), idealmente > 0.
  - Origen: NAV en EUR calculado por el backtester antes del rebalance.
  - Obligatorio: sí.
  - Uso actual:
    - Límite de tamaño por Kelly (cap_position_size).
    - Cálculo de pesos máximos permitidos (max_weight = max_eur / nav_eur).
  - Si falta o es None:
    - Comportamiento recomendado: lanzar error bloqueante o no evaluar señal (modo seguro).
    - En términos de contrato, no es válido invocar v0.5 sin nav_eur consistente.

- equity_curve: list[float]
  - Tipo: lista cronológica de NAVs (último = valor más reciente).
  - Obligatorio: requerido para DD, opcional para el resto.
  - Uso actual:
    - compute_drawdown(equity_curve) -> max_dd, peak_idx, trough_idx.
    - eval_dd_guardrail(max_dd, dd_cfg) -> estado "normal" / "risk_off_light" / "hard_stop".
  - Requisitos:
    - Lista no vacía.
    - Valores numéricos finitos (sin NaN ni inf).
  - Si falta:
    - Guardrail de DD desactivado.
    - Flag recomendado en la señal anotada: risk_warnings += ["dd_disabled"].
    - risk_decision.size_multiplier permanece en 1.0 salvo que otras reglas lo modifiquen.

- current_weights: dict[str, float]
  - Tipo: ticker -> peso_actual (fracción de NAV en [0,1]).
  - Obligatorio: opcional en v0.5 (se pasa como parámetro posicional adicional).
  - Uso actual:
    - Reglas de límites de posición (within_position_limits).
  - Nota de compatibilidad:
    - En v0.5, current_weights sigue siendo la fuente canónica.
    - portfolio.current_weights se considera espejo informativo de cara a futuras versiones.

----------------------------------------------------------------------
2. Bloque prices
----------------------------------------------------------------------

Estado de precios necesarios para evaluar stops ATR.

- last_prices: dict[str, float]
  - Tipo: ticker -> último precio > 0.
  - Obligatorio:
    - Requerido si atr_ctx está presente.
    - Opcional si no hay guardrail ATR activo.
  - Uso actual:
    - Evaluación de stops con is_stop_triggered(side, stop_price, last_price).
  - Si falta:
    - Con atr_ctx presente:
      - Guardrail ATR degradado a modo desactivado para ese ticker.
      - Flags sugeridos: risk_warnings += ["atr_data_missing:{ticker}"].
    - Sin atr_ctx:
      - No se evalúan stops ATR (guardrail ATR inactivo por diseño).

----------------------------------------------------------------------
3. Bloque atr_ctx
----------------------------------------------------------------------

Contexto por posición necesario para el stop-loss basado en ATR.

Estructura conceptual:

atr_ctx:
  TICKER:
    entry_price: float
    side: "long" o "short"
    atr: float o null
    atr_multiplier: float o null
    min_stop_pct: float o null
    last_price: float o null

Campos por ticker:

- entry_price: float
  - Obligatorio si se va a evaluar el stop para ese ticker.
  - Debe ser > 0.
  - Si falta -> no se evalúa stop para ese ticker.

- side: str
  - Valores normalizados: "long" o "short".
  - Obligatorio.
  - Si falta o es inválido -> no se evalúa stop para ese ticker.

- atr: float o None
  - Valor ATR (volatilidad) para el instrumento.
  - Opcional:
    - Si atr es None o no numérico:
      - Se usa min_stop_pct como fallback (stop en porcentaje fijo).
      - Flag recomendado: risk_reasons += ["atr_fallback:{ticker}"].

- atr_multiplier: float o None
  - Multiplicador local de ATR.
  - Si es None -> usar atr_stop.default_atr_multiplier desde config.

- min_stop_pct: float o None
  - Mínimo porcentaje de stop (por ejemplo 0.02 = 2%).
  - Si es None -> usar atr_stop.default_min_stop_pct desde config.

- last_price: float o None
  - Dato redundante (puede venir aquí o en last_prices).
  - Si está presente y válido, tiene prioridad sobre last_prices[ticker].

Comportamiento cuando faltan campos:

- Falta atr_ctx completo:
  - Guardrail ATR desactivado globalmente.
  - Flag sugerido: risk_warnings += ["atr_disabled"].

- Falta last_price para un ticker (ni en ctx ni en last_prices):
  - No se evalúa stop para ese ticker.
  - Flag sugerido: risk_warnings += ["partial_prices"].

----------------------------------------------------------------------
4. Bloque config (derivado de risk_rules.yaml)
----------------------------------------------------------------------

Este bloque agrupa la configuración de guardrails ya normalizada desde risk_rules.yaml.

Ejemplo conceptual:

config:
  dd_guardrail:
    max_dd_soft: float
    max_dd_hard: float
    size_multiplier_soft: float
  atr_stop:
    default_atr_multiplier: float
    default_min_stop_pct: float
  limits:
    max_single_asset_pct: float
    max_crypto_pct: float
    max_altcoin_pct: float
  kelly:
    cap_factor: float
    crypto_overrides: dict
    percentile_thresholds: dict

- dd_guardrail:
  - max_dd_soft: umbral soft de drawdown (ejemplo 0.05).
  - max_dd_hard: umbral hard (ejemplo 0.10).
  - size_multiplier_soft: multiplicador global de tamaño cuando el estado es "risk_off_light".
  - Si falta el bloque completo:
    - Usar defaults seguros desde risk_rules.yaml.
    - Flag sugerido: risk_warnings += ["dd_cfg_default"].

- atr_stop:
  - default_atr_multiplier: multiplicador por defecto de ATR (por ejemplo 2.5).
  - default_min_stop_pct: porcentaje mínimo de stop (por ejemplo 0.02).
  - Si falta:
    - Guardrail ATR se considera desactivado salvo overrides completos por ticker.
    - Reflejarlo en risk_warnings.

- limits:
  - Límites de concentración y cripto.
  - Uso actual: within_position_limits(current_weights).

- kelly:
  - Parámetros para el cálculo de tamaño máximo de posición, incluyendo cap_factor y overrides.
  - Uso actual: cálculo de max_eur y max_weight por activo.
  - Si falta:
    - Comportamiento seguro: no aumentar tamaño más allá de pesos actuales; en caso de duda, bloquear nuevas entradas con flags kelly_cap:{asset}.

----------------------------------------------------------------------
5. Reglas de degradación y flags recomendados
----------------------------------------------------------------------

Resumen de comportamiento cuando faltan campos en risk_ctx:

- Falta nav_eur:
  - Error bloqueante o no evaluar señal.
- Falta equity_curve:
  - DD desactivado.
  - Flag: risk_warnings += ["dd_disabled"].
- Falta dd_cfg:
  - Usar defaults seguros desde YAML.
  - Flag: risk_warnings += ["dd_cfg_default"].
- Falta atr_ctx completo:
  - ATR desactivado globalmente.
  - Flag: risk_warnings += ["atr_disabled"].
- last_prices parcial:
  - Ignorar stops en tickers sin precio.
  - Flag: risk_warnings += ["partial_prices"].
- atr = None:
  - Fallback a min_stop_pct.
  - Flag: risk_reasons += ["atr_fallback:{ticker}"].

----------------------------------------------------------------------
6. Observabilidad mínima v0.5
----------------------------------------------------------------------

Sin cambiar el contrato de salida de v0.4, v0.5 mantiene:

- allow: bool (valor de retorno principal).
- annotated: dict (señal anotada) con los campos:
  - risk_allow: bool
  - risk_reasons: list[str]
  - risk_decision: dict
    - allow_new_trades: bool
    - force_close_positions: bool
    - size_multiplier: float
    - stop_signals: list[str]
    - warnings: lista opcional de strings.

Para Plan 2A, este contrato se extenderá con:

- Contadores de stops ATR activados.
- Desglose por tipo de risk_reasons (DD, ATR, Kelly, límites).
- Campos portfolio_id y strategy_id para escenarios multi-portfolio y multi-estrategia.

----------------------------------------------------------------------
7. Compatibilidad y futuro (bridge 1D -> 2A)
----------------------------------------------------------------------

- En v0.5:
  - filter_signal(signal, current_weights, nav_eur=None, **kwargs) sigue siendo la firma pública.
  - risk_ctx existe como contrato lógico, no como tipo explícito.
- En v0.6 / Plan 2A:
  - Se introducirá RiskContext como dataclass:
    - risk_ctx podrá ser RiskContext o dict para mantener compatibilidad.
  - portfolio_id y strategy_id se volverán campos de primer nivel en el contexto.

Este documento cierra 1D en cuanto a especificación del contexto, sin tocar código, y sirve como referencia para futuras extensiones de RiskManager v0.5+.
