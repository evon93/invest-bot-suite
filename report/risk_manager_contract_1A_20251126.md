# Contrato de `RiskManager` v0.4 + shim (Paso 1A)

Basado en:
- `risk_manager_v_0_4.py`
- `risk_manager_v0_4_shim.py`

---

## 1. API pública principal

### 1.1. Clase `RiskManager`

Firma de construcción:

    RiskManager(rules: dict | str | Path)

Parámetro `rules`:

- `dict` → diccionario ya cargado con las reglas (normalmente `risk_rules.yaml` parseado).
- `str` o `Path` → ruta a un YAML de reglas; el propio constructor hace `yaml.safe_load`.

Atributos internos relevantes (después de `__init__`):

- `self.rules: dict`  
  YAML completo cargado.
- `self.pos_limits: dict`  
  Derivado de `rules["position_limits"]` o, por defecto:
  - `max_single_asset_pct`: 0.10
  - `max_crypto_pct`: 0.30
  - `max_altcoin_pct`: 0.05
- `self.kelly_rules: dict`  
  Derivado de `rules["kelly"]` o, por defecto:
  - `cap_factor`: 0.5
  - `crypto_overrides`: `{"high_vol": 0.3, "med_vol": 0.4, "low_vol": 0.5}`
  - `percentile_thresholds`: `{"low": 0.5, "high": 0.8}`
- `self.major_cryptos: set[str]`  
  Construido a partir de `rules["major_cryptos"]` (lista).
- `self.liquidity_filter: dict`  
  Derivado de `rules["liquidity_filter"]` o por defecto `{"min_volume_usd": 10_000_000}`  
  (actualmente no se usa en la lógica efectiva).
- `self.logger`: logger simple `logging.getLogger("RiskManager")`.

---

## 2. Métodos clave y contrato de uso

### 2.1. `cap_position_size`

    cap_position_size(asset: str, nav_eur: float, vol_pct: float) -> float

Propósito:  
Calcular el tamaño máximo en EUR permitido para un activo, usando fracción de Kelly capada + overrides cripto.

Inputs:

- `asset`: identificador del activo (ej. `"CRYPTO_BTC"`, `"STOCK_XYZ"`).
- `nav_eur`: NAV total de cartera en EUR (float > 0).
- `vol_pct`: percentil de volatilidad (0–1) o métrica equivalente.

Lógica:

1. Parte de `base_fraction = kelly_rules["cap_factor"]` (ej. 0.5).
2. Si `asset ∈ major_cryptos`:
   - Usa `kelly_rules["percentile_thresholds"]["low"/"high"]` (ej. 0.5 y 0.8) para clasificar `vol_pct`:
     - `vol_pct ≥ high` → usa `crypto_overrides["high_vol"]`.
     - `low ≤ vol_pct < high` → `crypto_overrides["med_vol"]`.
     - `vol_pct < low` → `crypto_overrides["low_vol"]`.
3. Devuelve `nav_eur * base_fraction`.

Notas:

- No aplica los overrides `per_asset` del YAML ni `min_trade_size_eur` / `max_trade_size_eur`: estos campos existen en `risk_rules.yaml` pero no están implementados aquí.
- Este método implementa una fracción de Kelly capada específica para cripto mayor, pero no controla tamaños mínimo/máximo por trade.

---

### 2.2. `max_position_size`

    max_position_size(nav_eur: float) -> float

Propósito:  
Tamaño máximo absoluto (EUR) permitido por reglas generales de posición individual.

Inputs:

- `nav_eur`: NAV total de cartera en EUR.

Lógica:

- Lee `pct = pos_limits["max_single_asset_pct"]` (o 0.10 por defecto).
- Devuelve `nav_eur * pct`.

Notas:

- Este método no se usa explícitamente dentro de `filter_signal` en la versión actual; se supone que el caller podría usarlo para controles adicionales.

---

### 2.3. `within_position_limits`

    within_position_limits(alloc: dict[str, float]) -> bool

Propósito:  
Validar que un diccionario de pesos por activo respeta los límites de exposición por activo / cripto / altcoins.

Inputs:

- `alloc`: diccionario `{asset: weight}` donde `weight` es fracción del portfolio (0–1).

Lógica:

1. Límite por activo:
   - Si cualquier `weight > max_single_asset_pct` → log warning `"Asset limit exceeded"` y devuelve `False`.
2. Identificación de cripto:
   - `crypto_assets = [a for a in alloc if a.startswith("CRYPTO")]`.
   - Si hay cripto:
     - `crypto_total = sum(alloc[a] for a in crypto_assets)`  
       Si `crypto_total > max_crypto_pct` → warning `"Crypto sector limit exceeded"`, devuelve `False`.
     - `altcoins = [a for a in crypto_assets if a not in major_cryptos]`
       - `altcoin_total = sum(alloc[a] for a in altcoins)`  
         Si `altcoin_total > max_altcoin_pct` → warning `"Altcoin limit exceeded"`, devuelve `False`.
3. Si pasa todos los checks → devuelve `True`.

Notas importantes:

- Usa un heurístico de tipo de activo por prefijo `"CRYPTO"`.
- No usa el límite `max_sector_pct` definido en el YAML.
- No diferencia sectores de acciones (no hay lógica sectorial en el código actual).
- Asume que `alloc` representa pesos actuales; no comprueba explícitamente la cartera post-trade.

---

### 2.4. `filter_signal`

    filter_signal(
        self,
        signal: dict,
        current_weights: dict,
        nav_eur: float | None = None,
        **kwargs,
    ) -> tuple[bool, dict]

Propósito:  
Filtrar una señal de trading y devolver:

- `allow`: si la señal pasa los filtros de riesgo.
- `annotated_signal`: copia de la señal con anotaciones de riesgo y posibles ajustes de tamaños.

Inputs esperados:

- `signal: dict` con al menos:
  - `signal["assets"]`: lista de activos implicados.
  - `signal["deltas"]`: dict `{asset: target_weight}` con pesos objetivo propuestos (o cambios de peso).
- `current_weights: dict[str, float]`:
  - Pesos actuales de cartera (0–1).
- `nav_eur: float | None`:
  - NAV total; si es truthy, se aplica lógica de Kelly.
- `**kwargs`:
  - Reservado para extensiones futuras (no usado actualmente).

Lógica de alto nivel:

1. Inicializa:
   - `allow = True`
   - `reasons = []`
   - `annotated = signal.copy()`
2. Límites de posición (portfolio-level):
   - Si `within_position_limits(current_weights)` → OK.
   - Si `False` → `allow = False`, añade `"position_limits"` a `reasons`.
3. Liquidez (stub):
   - Para cada `asset` en `signal["assets"]`:
     - Llama `_check_liquidity(asset)`:
       - Si devuelve `False` → `allow = False`, añade `"liquidity:{asset}"` a `reasons`.
     - En la implementación actual `_check_liquidity` siempre devuelve `True`, por lo que no hay filtro real.
4. Kelly sizing (solo si `nav_eur` está definido):
   - Para cada `(asset, target_weight)` en `signal["deltas"].items()`:
     - Obtiene `vol_pct = _get_volatility(asset)` (stub, actualmente siempre `0.65`).
     - Calcula `max_eur = cap_position_size(asset, nav_eur, vol_pct)`.
     - `max_weight = max_eur / nav_eur`.
     - Si `target_weight > max_weight`:
       - `allow = False`
       - añade `"kelly_cap:{asset}"` a `reasons`.
       - ajusta `annotated["deltas"][asset] = max_weight` (clip).
5. Anotaciones:
   - `annotated["risk_allow"] = allow`
   - `annotated["risk_reasons"] = reasons`
6. Devuelve `(allow, annotated)`.

Comportamiento efectivo:

- El módulo puede:
  - Marcar la señal como bloqueada (`allow = False`) si se viola algún límite.
  - Clampear pesos por Kelly cuando corresponde.
- No implementa:
  - Stop-loss ATR.
  - Volatility stop basado en percentiles.
  - Guardrails de drawdown.
  - Reglas de rebalanceo temporal.
  - Límites sectoriales por sectores no cripto.

Estas partes están definidas en `risk_rules.yaml` pero fuera del alcance de `RiskManager` v0.4.

---

### 2.5. Helpers internos

    _get_volatility(asset: str) -> float

- Stub para tests.
- Devuelve siempre `0.65` (valor fijo).
- En producción debería reemplazarse por un cálculo real de volatilidad o percentiles.

    _check_liquidity(asset: str) -> bool

- Stub para tests.
- Devuelve siempre `True`.
- Aunque existe `liquidity_filter` en las reglas, aquí no se utiliza.

---

## 3. Shim `risk_manager_v0_4_shim.py` — contrato de import

Rol del shim:  
Ofrecer una ruta de import estable y resolver variantes de nombre de archivo para el módulo real de riesgo.

### 3.1. Resolución de módulo

Funciones internas:

    _find_real_module() -> Path | None

- Busca en el directorio del shim (y su padre) alguno de estos archivos:
  - `risk_manager_v0_4.py`  (preferido)
  - `risk_manager_v_0_4.py` (alternativo)
- Devuelve la ruta del primero que exista o `None`.

    _load_module() -> module

- Usa `_find_real_module()` para encontrar el archivo real.
- Carga dinámicamente el módulo con `importlib.util.spec_from_file_location`.
- Cachea el módulo en `_cached_module`.
- Registra el módulo en `sys.modules` bajo `module_name = module_path.stem`.

### 3.2. API que expone

Al final del shim:

    RiskManager = _load_module().RiskManager

Contrato externo:

- Cualquier componente puede hacer:

      from risk_manager_v0_4_shim import RiskManager

  y obtendrá la clase `RiskManager` definida en:
  - `risk_manager_v0_4.py` o
  - `risk_manager_v_0_4.py`

  según cuál exista en disco.

Implicación para el sistema:

- El resto del framework NO debe importar el archivo concreto, sino el shim.
- El shim actúa como punto único de entrada para el módulo de riesgo v0.4, aislando:
  - Diferencias de nombre de archivo.
  - Duplicados por Windows / rutas.
  - Posibles refactorizaciones internas mientras se mantenga la firma de `RiskManager`.

---

## 4. Cobertura vs `risk_rules.yaml` (mapeo alto nivel)

### 4.1. Reglas del YAML implementadas en `RiskManager` v0.4

- `position_limits.max_single_asset_pct` → usado en `within_position_limits`.
- `position_limits.max_crypto_pct` → usado en `within_position_limits` (peso total cripto).
- `position_limits.max_altcoin_pct` → usado en `within_position_limits` (peso total altcoins).
- `kelly.cap_factor` → usado como fracción base en `cap_position_size`.
- `kelly.crypto_overrides` + `kelly.percentile_thresholds` → usados para ajustar fracción de Kelly según volatilidad y tipo de cripto.
- `major_cryptos` → usado para diferenciar majors vs altcoins en:
  - `within_position_limits` (altcoins vs majors).
  - `cap_position_size` (aplicar overrides cripto).

### 4.2. Reglas del YAML presentes pero NO implementadas aquí

- `position_limits.max_sector_pct` → no hay lógica sectorial en `RiskManager` v0.4.
- `kelly.min_trade_size_eur` / `kelly.max_trade_size_eur` → no se usan.
- `kelly.per_asset.*` → overrides específicos por activo definidos en el YAML pero ignorados.
- `stop_loss.*` (ATR, lookback, min_stop_pct) → sin implementación de stop-loss aquí.
- `volatility_stop.*` (enabled, lookback_days, percentile) → sin implementación.
- `max_drawdown.*` (soft/hard limit, lookback_days) → sin lógica de drawdown aquí.
- `liquidity_filter.min_volume_24h_usd` → no se usa; `_check_liquidity` es un stub.
- `rebalance.*`, `recalibration.*`, `latency_budget_seconds`, `max_fee_pct`, `seed.*` → fuera del alcance de este `RiskManager` v0.4.

---

## 5. Supuestos operativos

- Universo cripto identificado por prefijo `"CRYPTO"` en el `asset` ID.
- `alloc` y `current_weights` representan pesos en [0,1]; no se valida que sumen 1.
- `vol_pct` se interpreta como percentil (0–1) de volatilidad para aplicar thresholds.
- `nav_eur` debe ser positivo; si es `None` o 0, no se ejecuta la lógica de Kelly en `filter_signal`.
- Frecuencia temporal (diaria, intradía, etc.) y forma exacta de `signal["deltas"]` dependen del caller (backtester/strategy_engine); no se fuerzan aquí.

Este contrato es la referencia para:
- Diseñar tests adicionales.
- Detectar brechas entre `risk_rules.yaml` y la implementación actual.
- Planificar refactors en pasos 1B/1C.
