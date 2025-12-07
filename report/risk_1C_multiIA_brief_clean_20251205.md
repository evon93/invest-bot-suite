# Brief Auditoría Multi-IA — RiskManager v0.5 (Fase 1C)

## 1. Contexto

Proyecto: **invest-bot-suite**  
Módulo: **RiskManager v0.5** (Fase 1C)  
Rama de trabajo actual: `feature/1C_riskmanager_v0_5_audit`

Objetivo de esta auditoría:  
Revisar la implementación de riesgo v0.5 (guardrails de DD global y stop-loss ATR básico, más wiring de `risk_decision`) desde varios ángulos: robustez, claridad, edge cases, coherencia con `risk_rules.yaml` y con el flujo de backtest.

Estado actual:
- `python -m pytest -q` → **47 tests pasando**.
- Sub-suite de riesgo v0.5 (`test_risk_*v0_5.py`) → **31 tests pasando**.
- Fase 1C considerada baseline estable antes de diseñar guardrails avanzados (1D+).

---

## 2. Archivos relevantes para revisar

### Código core

- `risk_manager_v0_5.py`
- `risk_manager_factory.py`
- `backtest_initial.py`
- `risk_rules.yaml`

### Tests de riesgo v0.5

- `tests/test_risk_dd_v0_5.py`
- `tests/test_risk_atr_stop_v0_5.py`
- `tests/test_risk_decision_v0_5.py`
- `tests/test_risk_v0_5_extended.py`

### Documentación / reporting

- `report/risk_decision_v0_5_spec_1C_20251201.md`
- `report/risk_guardrails_impl_1C_20251201.md`
- `report/risk_tests_matrix_v0_5_1C_20251201.md`
- `report/risk_v0_5_review_20251201.md`
- `report/risk_advanced_tests_blueprint_1B_20251126.md` (con actualización 1C)
- `report/pytest_1C_full_after.txt`
- `report/pytest_1C_audit_baseline.txt`

### Paquete empaquetado

- `report/audit_1C_v0_5_bundle_20251204.tar.gz`  
  (contiene código + tests + reports clave + baseline pytest para esta fase).

---

## 3. Qué revisar y qué tipo de feedback esperamos

### 3.1 Correctitud lógica de guardrails

- ¿El cálculo de **drawdown global (DD)** es numéricamente robusto?
  - Series cortas, con gaps de precios, retornos extremos, precios negativos.
- ¿El **stop-loss ATR** es coherente con prácticas estándar?
  - ¿Hay parámetros o casos donde los niveles de stop puedan resultar inestables o poco realistas?
- ¿El flujo de `risk_decision` respeta el orden correcto de aplicación de guardrails?
  - DD global → ATR → otros filtros (si existen).
- ¿Se respetan en todo momento los límites definidos en `risk_rules.yaml`?

### 3.2 Edge cases y escenarios extremos

- Proponer escenarios (series de precios, gaps, shocks de volatilidad) donde:
  - El DD global pueda comportarse de forma contraintuitiva o peligrosa.
  - El stop ATR pueda producir stops excesivamente laxos o estrictos.
- Evaluar si los tests actuales cubren:
  - Valores extremos de ATR.
  - Curvas de equity con saltos bruscos.
  - Períodos con datos incompletos o ausentes.

### 3.3 Coherencia con `risk_rules.yaml`

- Comprobar que:
  - Los parámetros de DD global y ATR están bien interpretados (semántica, rangos, tipos).
  - No hay campos muertos, ambiguos o no utilizados.
- Detectar posibles inconsistencias entre:
  - Lo que declara el YAML.
  - Lo que realmente aplica el código.

### 3.4 Diseño, claridad y extensibilidad

- Evaluar si la API de `risk_manager_v0_5` y `risk_manager_factory` es clara y extensible para:
  - Añadir guardrails de volatilidad.
  - Añadir reglas de liquidez.
  - Añadir overrides por activo/estrategia.
- Valorar si la documentación (`risk_decision_v0_5_spec`, `risk_guardrails_impl`, `risk_tests_matrix`, `risk_advanced_tests_blueprint`) refleja fielmente el comportamiento del código.
- Señalar oportunidades de refactor para:
  - Reducir complejidad ciclomática.
  - Mejorar legibilidad y trazabilidad.

---

## 4. Formato esperado de la respuesta de cada IA

Se recomienda devolver el informe en el siguiente esquema Markdown:

```markdown
# Informe Auditoría — [NOMBRE IA]

## 1. Resumen ejecutivo
- [2–5 bullets con las conclusiones principales]

## 2. Hallazgos por categoría

### 2.1 Correctitud lógica
- [H1] (Severidad: 1–4) — Descripción, referencia a archivo/línea si es posible.
- [H2] ...
- ...

### 2.2 Edge cases / escenarios extremos
- [Hn] (Severidad: 1–4) — Descripción + ejemplo de escenario.

### 2.3 Coherencia con configuración (risk_rules.yaml)
- [Hn] (Severidad: 1–4) — Descripción + sugerencia de alineación.

### 2.4 Diseño / claridad / extensibilidad
- [Hn] (Severidad: 3–4 habitualmente) — Comentarios de arquitectura y estilo.

## 3. Recomendaciones concretas
- [R1] — Sugerencia de cambio o test adicional (si aplica).
- [R2] — Refactor o mejora de documentación.
- ...

## 4. Prioridades (para EXECUTOR / ORCHESTRATOR)
- Severidad 1–2: deben resolverse antes de Fase 1D.
- Severidad 3–4: se pueden agendar como mejoras futuras.
```

---

## 5. Criterio de severidad sugerido

- **Severidad 1:** Bug lógico que puede romper el control de riesgo o la consistencia del portfolio.
- **Severidad 2:** Comportamiento inesperado en edge cases relevantes (riesgo real).
- **Severidad 3:** Problemas de diseño, claridad o mantenibilidad (pero sin romper riesgo).
- **Severidad 4:** Mejora cosmética / refactor deseable pero no urgente.

---

## 6. Uso previsto de los resultados de la auditoría

Los hallazgos y recomendaciones de las distintas IAs se consolidarán en:

1. Una **matriz de issues** (archivo separado) con:
   - ID de issue.
   - Severidad (1–4).
   - Categoría (lógica, edge case, config, diseño).
   - Estado (pendiente / resuelto / descartado).
2. Un conjunto de **parches mínimos** para issues Severidad 1–2, aplicados antes de la Fase 1D.
3. Un input para el diseño de la Fase 1D (guardrails de volatilidad, liquidez, overrides por activo y su integración con el `stress_tester`).

Este brief puede copiarse directamente en los chats de DeepSeek, Gemini, Claude u otras IAs para que realicen la auditoría sobre el paquete `audit_1C_v0_5_bundle_20251204.tar.gz` o directamente sobre el repo `invest-bot-suite` en la rama `feature/1C_riskmanager_v0_5_audit`.
