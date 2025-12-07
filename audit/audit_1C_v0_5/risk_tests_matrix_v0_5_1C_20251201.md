# Matriz de Tests de Riesgo v0.5 — Fase 1C (2025-12-01)

Este documento mapea los tests v0.5 de riesgo con los guardrails implementados en la Fase 1C:

- **Guardrail DD Global**: límite de drawdown máximo a nivel de portfolio / estrategia.
- **Guardrail Stop-Loss ATR**: stop básico basado en ATR para cortar pérdidas por activo.
- **Wiring risk_decision v0.5**: integración de señales y filtros en `risk_manager_v0_5`.
- **Backtest E2E con guardrails activos**: validación integrada sobre el flujo completo de backtest.

---

## 1. Tabla Resumen por Test

| Test / Archivo                              | Guardrail DD Global | Stop ATR Básico | Wiring `risk_decision` | Backtest E2E | Estado 1C | Notas principales |
|--------------------------------------------|---------------------|-----------------|-------------------------|--------------|-----------|-------------------|
| `tests/test_risk_dd_v0_5.py`               | ✔ Cobertura directa | N/A             | Indirecto (inputs)      | Parcial      | PASA      | Verifica `compute_drawdown` y `eval_dd_guardrail` en casos borde. |
| `tests/test_risk_atr_stop_v0_5.py`         | N/A                 | ✔ Cobertura directa | Indirecto (inputs)   | Parcial      | PASA      | Valida `compute_atr_stop` y comportamiento ante falta de datos ATR. |
| `tests/test_risk_decision_v0_5.py`         | ✔ Vía decisiones    | ✔ Vía decisiones | ✔ Cobertura central   | Parcial      | PASA      | Testea que `risk_decision` aplica correctamente los filtros DD/ATR. |
| `tests/test_risk_v0_5_extended.py`         | ✔ Integrado         | ✔ Integrado      | ✔ Integrado           | ✔ Fuerte     | PASA      | Casos extendidos que combinan varias condiciones y rutas de decisión. |
| `pytest_1C_full_after.txt` (ejecución full)| ✔ Agregado suite    | ✔ Agregado suite | ✔ Agregado suite      | ✔ Suite full | PASA      | 47 tests pasando; no se rompen invariantes globales de riesgo. |

---

## 2. Detalle por Guardrail

### 2.1 Guardrail DD Global

**Objetivo:** asegurar que el drawdown máximo no supera el umbral definido en `risk_rules.yaml`.

**Tests clave:**

- `tests/test_risk_dd_v0_5.py`  
  - Cubre:
    - Cálculo de drawdown sobre series de PnL / equity.
    - Manejo de precios negativos o inputs anómalos.
    - Evaluación del umbral de DD y señalización de bloqueo.

- `tests/test_risk_decision_v0_5.py`  
  - Cubre:
    - Cómo la decisión de riesgo integra el resultado de `eval_dd_guardrail`.
    - Bloqueo de nuevas posiciones cuando el DD excede el límite.

- `tests/test_risk_v0_5_extended.py`  
  - Cubre:
    - Escenarios compuestos donde el DD interactúa con otros filtros de riesgo.
    - Confirmación de que los límites de DD prevalecen frente a señales agresivas.

---

### 2.2 Guardrail Stop-Loss ATR

**Objetivo:** introducir un stop-loss básico por activo basado en ATR, coherente con `risk_rules.yaml`.

**Tests clave:**

- `tests/test_risk_atr_stop_v0_5.py`  
  - Cubre:
    - Cálculo de niveles de stop a partir de ATR.
    - Comportamiento cuando no hay suficientes datos para ATR.
    - Robustez ante valores extremos (ATR muy alto / muy bajo).

- `tests/test_risk_decision_v0_5.py`  
  - Cubre:
    - Aplicación de stop ATR a señales de entrada/salida.
    - Priorización del stop frente a otros factores cuando se dispara.

- `tests/test_risk_v0_5_extended.py`  
  - Cubre:
    - Interacción del stop ATR con el guardrail de DD global en escenarios complejos.

---

### 2.3 Wiring de `risk_decision` en `risk_manager_v0_5`

**Objetivo:** garantizar que el manager v0.5 consume señales, aplica filtros DD/ATR y respeta los límites de riesgo.

**Tests clave:**

- `tests/test_risk_decision_v0_5.py`  
  - Cubre:
    - Flujo principal de `risk_decision`.
    - Orden de aplicación de guardrails (DD → ATR → otros filtros).
    - Comportamiento esperado ante combinación de señales contradictorias.

- `tests/test_risk_v0_5_extended.py`  
  - Cubre:
    - Casos más realistas de portfolio donde el wiring completo se ejerce.
    - Validación de que no se violan los límites definidos en `risk_rules.yaml`.

---

### 2.4 Backtest E2E con Guardrails Activos

**Objetivo:** validar que, en un flujo de backtest realista, los guardrails de DD y ATR se comportan como se espera.

**Artefactos clave:**

- `backtest_initial.py` (versión v0.5 compatible)  
  - Ejecuta un escenario de backtest con el `risk_manager_v0_5` activo.
  - Permite observar:
    - Impacto de los stops ATR en el PnL.
    - Impacto del guardrail de DD en la trayectoria de la curva de equity.

- `report/pytest_1C_full_after.txt`  
  - Confirma que la suite entera (47 tests) pasa con los guardrails activados.
  - Sirve como baseline de regresión para futuras fases (1D+).

---

## 3. Cobertura Actual vs Backlog 1D+

- La Fase **1C** cubre de forma sólida:
  - Guardrail de **drawdown global**.
  - Stop-loss **básico** basado en ATR.
  - Wiring principal de `risk_decision` en `risk_manager_v0_5`.
  - Un backtest de referencia con guardrails activos.

- Quedan para **1D+**:
  - Guardrails adicionales de volatilidad (σ rolling, ATR%) más avanzados.
  - Reglas de liquidez (ADV, % volumen) y límites finos de tamaño.
  - Overrides por activo/estrategia con granularidad específica.

