
---

# Actualización — Fase 1C (2025-12-01)

Esta sección marca qué partes del blueprint ya han sido implementadas en la Fase 1C del RiskManager v0.5, así como los elementos que quedan abiertos para 1D+.

## Elementos ya cubiertos en 1C

### ✔ Guardrail de Drawdown Global (DD)
- Implementado en `risk_manager_v0_5.py`.
- Tests unitarios completados:
  - `tests/test_risk_dd_v0_5.py`
  - Cobertura parcial adicional en:
    - `tests/test_risk_decision_v0_5.py`
    - `tests/test_risk_v0_5_extended.py`
- Validado en backtest E2E.

### ✔ Stop-Loss Básico basado en ATR
- Implementado en `compute_atr_stop` y aplicado en el flujo de `risk_decision`.
- Tests unitarios:
  - `tests/test_risk_atr_stop_v0_5.py`
  - Integración adicional en:
    - `tests/test_risk_decision_v0_5.py`
    - `tests/test_risk_v0_5_extended.py`

### ✔ Wiring del Risk Manager v0.5
- Flujo de decisión completo (`risk_decision`) integrando DD + ATR.
- Pruebas cruzadas de wiring en:
  - `tests/test_risk_decision_v0_5.py`
  - `tests/test_risk_v0_5_extended.py`

### ✔ Validación E2E en Backtest
- Backtest ejecutado con guardrails activos.
- Estado de suite: **47 tests PASANDO**.
- Log consolidado: `report/pytest_1C_full_after.txt`.

---

## Elementos NO cubiertos aún (Backlog 1D+)

### 🔲 Guardrail de Volatilidad (σ rolling, % ATR)
Pendiente implementar:
- Cálculo de volatilidad rolling por activo.
- Definición de umbrales en `risk_rules.yaml`.
- Ajustes dinámicos del tamaño/entrada/salida.
- Tests requeridos:
  - Unitarios sobre cálculo σ.
  - Integración con risk_decision.
  - Casos extendidos (volatilidad extrema, gaps).

### 🔲 Reglas de Liquidez (ADV, %, buckets)
Pendiente implementar:
- Límite de tamaño por ADV y categorías de liquidez.
- Bloqueo o recorte en activos ilíquidos.
- Tests requeridos:
  - Unitarios de clasificación de liquidez.
  - Integración en risk_decision.
  - Escenarios multi-activo.

### 🔲 Overrides per-asset / per-strategy
Pendiente implementar:
- Modificadores por activo.
- Kelly fracción ajustada por regla.
- Stops específicos por activo.
- Tests requeridos:
  - Unitarios de carga/validación de overrides.
  - Conflictos entre reglas globales y específicas.

### 🔲 Integración con Stress Tester
Pendiente:
- Simulación de guardrails bajo escenarios extremos.
- Métricas de portfolio (Calmar, max DD, varianza, % tiempo con guardrails activos).
- Tests requeridos:
  - Stress scenarios unitarios.
  - Monte Carlo con guardrails activados.

