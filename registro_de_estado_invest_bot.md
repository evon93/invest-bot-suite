# Registro de Estado  Proyecto invest-bot-suite

_Registro histórico, contexto para IAs colaboradoras y trazabilidad completa._

---
##  Estado Actual (2025-11-27)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (sin cambios de código desde 1A; solo specs y blueprints de riesgo).
- **Python venv**: 3.12.3 · mismo stack que en 1A (pytest, pyyaml, pandas, etc.).

- **Módulo de riesgo**: sigue siendo `RiskManager` v0.4 vía `risk_manager_v0_4_shim.py` (sin cambios de lógica).
- **Specs de riesgo avanzadas (1B)**:
  - `report/risk_advanced_guardrails_spec_1B_20251127.md`
  - `report/risk_advanced_tests_blueprint_1B_20251127.md`

- **Resumen 1B**:
  - Definido contrato objetivo de guardrails de riesgo avanzados:
    - max_drawdown (soft/hard), stop_loss basado en ATR, volatility_stop, liquidez, Kelly/overrides por activo.
  - Diseñado blueprint de tests:
    - matriz de cobertura por guardrail,
    - catálogo de tests unitarios,
    - escenarios de integración con backtester,
    - métricas a monitorizar.
  - Documentada integración event-driven propuesta:
    - uso de `context` en `filter_signal`,
    - eventos auxiliares (`PortfolioSnapshot`, `MarketFeatures`, etc.).
  - No se ha modificado código productivo; 1B es 100% diseño y documentación previa a la implementación (1C).

##  Estado Actual (2025-11-26)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (tag base `baseline_20251121_D0`).
- **Python venv**: 3.12.3 · numpy 2.3.1 · pandas 2.3.1 · pytest 8.4.1 · pyyaml 6.0.2.

- **Backtester**: `backtest_initial.py` · SimpleBacktester v0.1 (`fix_0C`) sin cambios adicionales respecto a 2025-11-24.
- **Tests backtester**: `tests/test_backtest_deepseek.py` → **6/6 PASS** (ver artefactos 0C ya registrados).

- **Módulo de riesgo**: `RiskManager` v0.4 vía `risk_manager_v0_4_shim.py` (sin cambios de lógica en 1A; solo documentación y trazabilidad).
- **Tests de riesgo** (antes/después de 1A):  
  - `python -m pytest tests/test_risk_suite.py -q` → **PASS** (`report/pytest_1A_risk_suite_before.txt`)  
  - `python -m pytest tests/test_risk_deepseek.py -q` → **PASS** (`report/pytest_1A_risk_deepseek_before.txt`)

- **Artefactos 1A (riesgo)**:
  - `report/risk_rules_summary_1A_20251126.md`
  - `report/risk_manager_contract_1A_20251126.md`
  - `report/risk_tests_matrix_1A_20251126.md`
  - `report/risk_manager_1A_auditoria_20251126.md`

- **Resumen 1A**:
  - Auditoría completa del sistema de riesgo:
    - YAML de reglas (`risk_rules.yaml`) → mapeado y resumido.
    - Implementación `RiskManager` v0.4 + shim → contrato explícito.
    - Tests de riesgo → matriz de escenarios y brechas de cobertura.
  - Sin modificación de código productivo; solo documentación y clarificación de contrato de riesgo.

##  Estado Actual (2025-11-24)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (base tag `baseline_20251121_D0`).
- **Python venv**: 3.12.3 · numpy 2.3.1 · pandas 2.3.1 · pytest 8.4.1 · pyyaml 6.0.2.

- **Backtester**: `backtest_initial.py` · SimpleBacktester v0.1 (parche 0C aplicado con Antigravity/Gemini 3 Pro).
- **Tests backtester**: `tests/test_backtest_deepseek.py` → **6/6 PASS**
  - Antes del fix: 4 FAIL (max_drawdown NaN, sin rebalanceos, portfolio 0 con precios 0/negativos).
  - Después del fix: ver `report/pytest_20251124_backtest_0C_after_fix.txt`.

- **Cambios clave 0C**:
  - Manejo robusto de precios 0/negativos: uso de `last_valid_prices` por activo.
  - Restricción “no weekend trading” respetada (entrada en primer día hábil disponible).
  - Entrada tardía + rebalanceo mensual con **log de rebalanceos** aunque `shares_delta = 0`
    (permite contar rebalanceos en portfolios single-asset).
  - Métricas robustas: evita `NaN` en `max_drawdown`, `cagr` y `sharpe` cuando hay valores iniciales 0
    o volatilidad ~0.

- **Artefactos 0C**:
  - Backup código: `backtest_initial.py.bak_0C`.
  - Diagnóstico previo: `report/backtest_0B_diagnostico_resumen_20251124.md`.
  - Logs pytest:
    - `report/pytest_0C_before_fix.txt`
    - `report/pytest_20251124_backtest_0B_summary.txt`
    - `report/pytest_20251124_0B_test_*.txt`
    - `report/pytest_20251124_backtest_0C_after_fix.txt`
  - Snapshot tests: `report/test_backtest_deepseek_snapshot_0B.py`.

##  Estado Actual (2025-11-24)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (tag base `baseline_20251121_D0`).
- **Backtester**: `backtest_initial.py` refactorizado (`fix_0C`) con precios robustos y rebalanceo mensual.
- **Build/tests**: `python -m pytest tests/test_backtest_deepseek.py -q` → **6/6 PASSED** (2025-11-24).
- **Artefactos clave**:
  - `report/pytest_20251124_backtest_0C_after_fix.txt`
  - `report/backtest_0B_diagnostico_resumen_20251124.md`
  - Logs detallados 0B (`report/pytest_20251124_0B_*.txt`) y snapshot de tests (`report/test_backtest_deepseek_snapshot_0B.py`).

### Notas de diseño del backtester (fix_0C)

- **Precios efectivos (`last_valid_prices`)**:  
  - Para cada activo se mantiene el último precio estrictamente positivo.  
  - Precios 0 o negativos se consideran no operables y se saltan en el rebalanceo.
- **Rebalanceo & calendario**:
  - No hay trades en fin de semana (respeta `test_no_rebalance_on_weekend`).
  - Si el primer día es fin de semana o no se ha entrado aún, se realiza **entrada tardía** el primer día hábil disponible.
  - Rebalanceo mensual el día 1 sólo si es laborable y no se ha rebalanceado ya ese mismo día.
  - Se registran eventos en `backtester.trades` incluso si `shares_delta == 0` para single-asset, lo que permite verificar frecuencia de rebalanceo.
- **Métricas robustas (`calculate_metrics`)**:
  - Protecciones para series vacías o con menos de 2 puntos → métricas 0 en lugar de NaN.
  - `total_return` protegido cuando el valor inicial ≤ 0.
  - Drawdown calculado con `cummax` + `fillna(0.0)` para evitar NaN.
  - Sharpe ratio forzado a 0 si la volatilidad es 0 o NaN.

##  Estado Actual (2025-11-21)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (base tag `baseline_20251121_D0`).
- **Python venv**: 3.12.3 · numpy 2.3.1 · pandas 2.3.1 · pytest 8.4.1 · pyyaml 6.0.2.
- **Build/tests**: `pytest` → 4 FAIL / 6 PASS (fallos en `tests/test_backtest_deepseek.py`).
- **Artefactos baseline**: `requirements.lock`, `baseline_venv_packages_0A.txt`, `report/pytest_20251121_baseline_full.txt`, `report/env_20251121.json`.

---

##  Estado Actual (2025-07-12)

- **Entorno**: Windows 11 23H2 host  **WSL 2** (Ubuntu 24.04, kernel 5.15, GPU habilitada).
- **Ruta de trabajo**: `~/invest-bot-suite` (ext4, fuera de OneDrive).
- **Python venv**: 3.12 · numpy 1.28 · pandas 2.2 · pytest 8.2 · pyyaml 6.0.2.
- **Build/tests**: `pytest`  **6 FAIL / 4 PASS** (error `.columns` en `SimpleBacktester._rebalance`).
- **CI**: workflow **edge_tests** operativo; métricas automáticas pendientes (`calc_metrics`).
- **Backlog abierto**: P1  P5 (ver tabla de problemas).
- **Próximo hito**: Rama `docs/v1.3`  CHANGELOG provisional  PR Stage A.

### Problemas abiertos (prioridad descendente)

| Nº | Ítem | Acción requerida |
|----|------|------------------|
| P1 | 6 tests fallan (`SimpleBacktester._rebalance`) | Refactor para soportar Series & DataFrame |
| P2 | `requirements.txt` sin versiones | Ejecutar `pip freeze > requirements.lock`, pin dependencias |
| P3 | Dev Container incompleto | Completar Dockerfile + `devcontainer.json` |
| P4 | OneDrive pop-ups al borrar archivos | Excluir `shared` de sincronización |
| P5 | Falta CI/CD completo | Crear workflow CI + GHCR |

---

##  Estado Actual (2025-07-08)

- **Freeze candidate v1.3:** código sincronizado en repo privado `evon93/invest-bot-suite`.
- RiskManager v0.5 (parches ISS-1923) en rama `main`.
- CI GitHub Actions activo: workflow **edge_tests** genera artefacto `edge_logs` .
- CHANGELOG y metrics report pendientes de subir (Calmar  2.0, FeeAdj ROIC  2.2 %, WF_ratio > 65 %).
- Orquestación IA establecida: Kai (o3), Claude Opus 4, Gemini 2.5 Pro, DeepSeek R1.

---

##  Historial de Fases Clave

### 2025-11-27  Paso 1B — Diseño avanzado de guardrails de riesgo
- Generada spec de guardrails avanzados:
  - `report/risk_advanced_guardrails_spec_1B_20251127.md`
  - Basada en auditoría 1A, risk_rules.yaml y código v0.4.
- Definida semántica objetivo para:
  - max_drawdown, stop_loss_ATR, volatility_stop, liquidez, Kelly con overrides per_asset.
- Diseñado blueprint de tests de riesgo:
  - catálogo de tests unitarios por guardrail,
  - escenarios de integración con estrategia/backtester,
  - métricas clave (DD, Sharpe/Calmar, % señales bloqueadas).
- Documentada integración event-driven propuesta para RiskManager v0.5 sin romper la API v0.4.
- Sin cambios de lógica aún; 1B sirve como base para la futura implementación en la Fase 1C.

### 2025-11-26  Paso 1A — Auditoría sistema de riesgo
- Congelado estado de tests de riesgo (`test_risk_suite.py`, `test_risk_deepseek.py`) con artefactos en `report/pytest_1A_*.txt`.
- Generados resúmenes estructurados:
  - Reglas declarativas (`risk_rules.yaml`).
  - Contrato de `RiskManager` v0.4 + shim.
  - Matriz de casos de prueba de riesgo.
- Redactado informe `report/risk_manager_1A_auditoria_20251126.md` sin tocar lógica:
  - Identificadas reglas de YAML no implementadas (stops, drawdown, liquidez real, overrides por activo).
  - Documentadas brechas de cobertura de tests para ser abordadas en fases 1B/1C.

### 2025-07-12  Migración a WSL 2 & detección de 6 tests FAIL
- Copiado repo a `~/invest-bot-suite` en volumen ext4.
- Creado venv `.venv` y actualización mínima de dependencias.
- Corregido indent en `backtest_initial.py`; aparecen 6 FAIL en rebalanceo.

### 2025-07-08  v1.3 (Design-Freeze loop)
-  Repo GitHub privado creado y código base push.
-  Añadido workflow **edge_tests** + artefactos logs.
-  Fixes críticos ISS-1923 integrados (cascade alert, liquidity multiplier Asia, stablecoin de-peg, gas multipliers, edge-tests CI).

### 2025-07-04
- Base limpia RiskManager v0.4 + SHIM universal + tests `3 passed`.
- Backup generado: `backup_20250704_1753.zip`.

---

##  Lecciones Aprendidas

1. Sin CI no hay auditoría IA  workflow mínimo indispensable.
2. Parar trading en rangos y cascadas evita DD > 15 %.
3. Métricas deben ser fee- y slippage-aware (FeeAdj ROIC).
4. Migrar a Linux/WSL reduce fricción con paths y venvs.

---

##  Próximos Hitos Inmediatos

| Semana | Hito | Responsable |
|--------|------|-------------|
| 0-1 | Crear rama `docs/v1.3`, subir CHANGELOG provisional | Kai |
| 0-1 | Generar `metrics_report.json` automático vía CI | DeepSeek |
| 1 | Completar Dev Container + Dockerfile | Gemini |
| 1 | Refactor re-balance + pasar tests | Kai |
| 2 | Declarar **Design Freeze** v1.3 final | Kai |

---

##  Trazabilidad IA  IA
- **TRACE_ID última build:** migrate_wsl2_v1.3_candidate
- IAs colaboradoras: Kai (o3), Claude Opus 4, Gemini 2.5 Pro, DeepSeek R1.

---

##  Notas
- Actualizar este registro tras cada push relevante.
- Adjuntar artefactos (edge_logs, metrics) en cada auditoría.
- Mantener backups tras milestones.
