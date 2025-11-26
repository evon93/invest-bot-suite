# Matriz de casos de prueba de riesgo (Paso 1A)

Basado en:
- tests/test_risk_suite.py
- tests/test_risk_deepseek.py
- risk_edge_cases.py

---

## 1. Tabla de escenarios de test

| # | Archivo                     | Nombre del test / escenario         | Condiciones de entrada principales                                                                 | Regla / aspecto de riesgo implicado                               | Expectativa / decisión comprobada                                                                                          |
|---|-----------------------------|--------------------------------------|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| 1 | test_risk_suite.py          | test_risk_manager_imported           | Import `RiskManager` desde `risk_manager_v0_4_shim`                                                | Carga correcta del módulo de riesgo a través del SHIM             | `RiskManager` existe y se importa sin error; garantiza que el SHIM resuelve correctamente la implementación v0.4.         |
| 2 | test_risk_suite.py          | test_risk_manager_basic_attrs        | `RiskManager(mock_rules)` con `position_limits` y `kelly` mínimos; no se usan señales complejas     | Existencia de API mínima: `within_position_limits`, `filter_signal`, `max_position_size` | La clase expone los métodos clave esperados por el resto del sistema.                                                     |
| 3 | test_risk_suite.py          | test_risk_manager_methods            | `mock_rules` con: `max_single_asset_pct=0.1`, `max_crypto_pct=1.0`, `major_cryptos=["BTC"]`; pruebas con `{"BTC": 0.05}` y `{"BTC": 0.15}`; señal simple con `{"deltas": {"BTC": 0.01}}`, `nav_eur=1000` | Límites de posición por activo (`max_single_asset_pct`), integración básica de Kelly y tipos de retorno | `within_position_limits({"BTC":0.05})` → `True`; `within_position_limits({"BTC":0.15})` → `False`; `filter_signal` devuelve `(bool, dict)` y `max_position_size(1000) <= 1000`. No se validan aún límites cripto/altcoins complejos. |
| 4 | test_risk_deepseek.py       | test_risk_manager_after_upgrade      | `RiskManager(mock_rules)` con `max_single_asset_pct=0.05`, `kelly.cap_factor=0.4`, `major_cryptos=["BTC","ETH"]`; pesos `{"BTC":0.03}` y `{"BTC":0.06}`; `cap_position_size("BTC", 10_000, 0.75)` | Compatibilidad de `within_position_limits` tras upgrade + Kelly cap | `within_position_limits({"BTC":0.03})` → `True`; `within_position_limits({"BTC":0.06})` → `False`. `cap_position_size(...)` devuelve un tamaño EUR tal que `0 < size < 10_000`, validando que se respeta el cap global de Kelly y no se rompe la API. |
| 5 | risk_edge_cases.py          | risk_edge_smoke                      | No usa reglas de riesgo; sólo `assert 1 + 1 == 2` y `print("Edge smoke OK")`                        | Smoke-test mínimo del entorno                                     | Verifica que el entorno de ejecución básico funciona (Python, assert); no cubre lógica de riesgo, pero sirve como check rápido. |

---

## 2. Cobertura efectiva sobre `risk_rules.yaml`

- **Cubierto directamente por tests:**
  - Límites por activo vía `max_single_asset_pct`:
    - Escenarios explícitos: `0.05`/`0.06`/`0.10`/`0.15`.
  - API pública de `RiskManager`:
    - Existencia de métodos `within_position_limits`, `filter_signal`, `max_position_size`.
  - Comportamiento básico de Kelly:
    - `cap_position_size` respeta `cap_factor` y no excede `nav_eur`.
  - Import estable a través del SHIM:
    - Garantiza que los tests y otros módulos pueden hacer `from risk_manager_v0_4_shim import RiskManager`.

- **No cubierto (o sólo tangencialmente) por tests de riesgo actuales:**
  - Límites de cripto total (`max_crypto_pct`) y altcoins (`max_altcoin_pct`) en escenarios multi-activo.
  - Uso de overrides `kelly.per_asset` definidos en el YAML.
  - Reglas de `stop_loss` (ATR, `min_stop_pct`) y `volatility_stop`.
  - Guardrails de `max_drawdown` (soft/hard) y lógica asociada.
  - Filtros de liquidez reales con `liquidity_filter.min_volume_24h_usd` (los stubs aceptan todo).
  - Integración explícita con régimen de mercado, rebalanceo o recalibración.

---

## 3. Observaciones para diseño de nuevos tests (1B/1C)

- Los tests actuales garantizan sólo que:
  - La API pública mínima existe y no se rompe al cambiar la implementación.
  - Los límites por activo son respetados en casos simples.
  - Kelly cap no produce tamaños absurdos (> NAV) y se mantiene dentro de los caps globales.

- No hay aún:
  - Casos donde una señal se bloquee por exceso de exposición cripto/altcoins.
  - Casos donde una señal sea recortada por Kelly en múltiples activos a la vez.
  - Casos donde el resultado de `filter_signal` dependa de reglas de stops/drawdown.
  - Pruebas de integración donde cambios en `risk_rules.yaml` (por ejemplo, bajar `max_crypto_pct`) se reflejen en el comportamiento de riesgo bajo escenarios de backtest.

Esta matriz se usará en el informe `risk_manager_1A_auditoria_YYYYMMDD.md` para documentar qué parte del contrato de riesgo está protegida por tests y qué parte queda abierta para futuros pasos (1B/1C).
