# Registro de Estado  Proyecto invest-bot-suite

_Registro histórico, contexto para IAs colaboradoras y trazabilidad completa._

---

## Estado Actual (2025-12-23) — Fase 2B: Risk Calibration Runner

- **Rama:** `feature/2B_risk_calibration`
- **Estado:** ✅ COMPLETADO
- **Commit HEAD:** `ab39260 2B.4: scoring formula uses risk counters`

**Entregables principales:**
- Runner de calibración: `tools/run_calibration_2B.py`
- Configuración: `configs/risk_calibration_2B.yaml`
- Tests: `tests/test_calibration_runner_2B.py`, `tests/test_backtester_closed_trades.py`

**Nuevas capacidades:**
- `closed_trades` con `realized_pnl` y `win_rate`
- `risk_events` con contadores ATR/hard_stop
- Score formula configurable con métricas de riesgo
- CLI `--output-dir` para override de directorio de salida

**Métricas añadidas:**
- `atr_stop_count`, `hard_stop_trigger_count`, `pct_time_hard_stop`, `missing_risk_events`
- `closed_trades_count`, `wins_count`, `losses_count`, `win_rate`, `gross_pnl`, `avg_win`, `avg_loss`

**Tests:** 57 passed

**Documentación:**
- `report/risk_calibration_2B_impl_20251223.md`
- `bridge_2B_to_2C_report.md`

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

---

## 2025-12-01 — Fase 1C: RiskManager v0.5 (guardrails DD global + stop-loss ATR básico)

- **Rama:** `feature/1C_riskmanager_v0_5`
- **Componentes afectados:**
  - `risk_manager_v0_5.py`
  - `risk_manager_factory.py`
  - `risk_rules.yaml`
  - Suite de tests v0.5:
    - `tests/test_risk_dd_v0_5.py`
    - `tests/test_risk_atr_stop_v0_5.py`
    - `tests/test_risk_decision_v0_5.py`
    - `tests/test_risk_v0_5_extended.py`
- **Guardrails de riesgo implementados en 1C:**
  - **Drawdown global (DD):**
    - Cálculo robusto de drawdown a partir de la curva de equity / PnL.
    - Evaluación de umbral de DD según `risk_rules.yaml`.
    - Bloqueo de nuevas posiciones cuando el DD excede el límite global.
  - **Stop-loss básico basado en ATR:**
    - Cálculo de niveles de stop por activo usando ATR.
    - Manejo explícito de casos sin datos suficientes de ATR.
    - Interacción coherente con el resto de filtros de riesgo.
  - **Wiring `risk_decision` v0.5:**
    - Integración de los guardrails DD y ATR en el flujo de decisión.
    - Priorización de límites de riesgo frente a señales agresivas de la estrategia.
- **Artefactos de apoyo generados en 1C:**
  - `report/risk_guardrails_impl_1C_20251201.md`
  - `report/risk_decision_v0_5_spec_1C_20251201.md`
  - `report/risk_v0_5_review_20251201.md`
  - `report/risk_tests_matrix_v0_5_1C_20251201.md`
  - `report/pytest_1C_full_after.txt`
- **Estado de tests (post-1C):**
  - `python -m pytest -q` → **47 tests PASANDO** (baseline de regresión con guardrails activos).
- **Notas para fases siguientes (1D+):**
  - Extender guardrails con:
    - Stops por volatilidad (σ rolling / %ATR).
    - Reglas de liquidez (ADV, % de volumen) para limitar tamaño de posiciones.
    - Overrides por activo/estrategia para ajustes finos.
  - Integrar estos guardrails adicionales con `stress_tester` y métricas de portfolio (Calmar, Max DD, etc.).


## PLAN 1D.validation — RiskManager v0.5 (DD/ATR/Kelly) · cierre y puente a 2A

Fecha: 2025-12-08  
Rama: feature/1D_riskmanager_v0_5_hardening  

Estado: COMPLETADO.

Resumen técnico:

- 1D.v1 — Snapshot final de tests
  - Se ejecuta pytest completo sobre la versión 1D.core.
  - Resultado: 47 tests PASSED (sin errores de colección).
  - Artefacto: report/pytest_1D_core_final.txt.

- 1D.v2 — Mini-backtest comparativo (none vs RiskManager v0.5)
  - Script: backtest_initial.py (escenario por defecto).
  - Escenario A (none, sin gestor de riesgo):
    - CAGR ≈ 15.79%
    - Total return ≈ 15.79%
    - Max drawdown ≈ -9.85%
    - Sharpe ratio ≈ 1.30
    - Volatilidad ≈ 0.1185
    - Artefacto: report/backtest_1D_none.txt
  - Escenario B (v0_5, RiskManagerV05 activado):
    - Logs muestran repetidamente: "Señal rechazada: ['kelly_cap:ETF']".
    - No se generan trades significativos; el NAV queda plano.
    - Métricas: todas en 0 (cagr, total_return, max_drawdown, sharpe_ratio, volatility).
    - Artefacto: report/backtest_1D_v05.txt
  - Informe de comparación:
    - report/backtest_1D_comparison_v05_vs_none.md
    - Conclusión: en este dataset concreto, la configuración de Kelly para el ETF es extremadamente conservadora y lleva el sistema a un modo casi full risk-off. No se modifican parámetros en 1D; la calibración se delega a 2A/2B.

- 1D.v3 — Contrato lógico RiskContext v0.5 (solo documentación)
  - No se cambia código de RiskManager en 1D.validation.
  - Se define el contrato lógico risk_ctx consumido por filter_signal(...) en v0.5:
    - Bloque portfolio: nav_eur, equity_curve, current_weights.
    - Bloque prices: last_prices.
    - Bloque atr_ctx: contexto por ticker para stop-loss ATR (entry_price, side, atr, atr_multiplier, min_stop_pct, last_price).
    - Bloque config: dd_guardrail, atr_stop, limits, kelly (derivados de risk_rules.yaml).
  - Se documentan reglas de degradación y flags recomendados cuando falta información (dd_disabled, atr_disabled, dd_cfg_default, partial_prices, atr_fallback:{ticker}, etc.).
  - Artefacto: report/risk_context_v0_5_spec_1D_20251207.md.

Decisión y puente a 2A:

- 1D.validation no ajusta parámetros de riesgo; se limita a:
  - Verificar que el wiring DD/ATR/Kelly funciona y no rompe tests.
  - Documentar el efecto extremo de la configuración actual de Kelly en el dataset de backtest.
  - Definir el contrato RiskContext v0.5 como base para futuras versiones.
- El ajuste fino de parámetros (por ejemplo relajación de Kelly para ETF, escenarios alternativos, multi-portfolio, etc.) se delega explícitamente a los planes de la serie 2A/2B, donde se trabajará ya con RiskContext formalizado como dataclass y objetivos cuantitativos de riesgo/retorno.


## 2025-12-11 — Workflow Antigravity v0.1 (infraestructura)

- Rama de trabajo: feature/workflow_antigravity_v0_1
- Objetivo: introducir infraestructura de soporte para agentes (Antigravity / EXECUTOR-BOT)
  sin modificar la lógica de trading ni de riesgo.

Cambios principales:
- Carpeta `.ai/`:
  - `.ai/active_context.md`: estado técnico resumido (rama actual, snapshots de pytest).
  - `.ai/decisions_log.md`: log de decisiones técnicas (incluye creación de protocolo y tooling).
  - `.ai/project_map.md`: mapa del repo generado automáticamente.
  - `.ai/antigravity_operational_protocol.md`: protocolo operativo v0.1 (roles, ciclo A→D, guardrails).
- Herramientas en `tools/`:
  - `tools/update_project_map.py`: genera `.ai/project_map.md`.
  - `tools/validate_risk_config.py`: valida `risk_rules.yaml` y escribe informe en `/report`.
- Esquema/config:
  - `config_schema.py`: validación best-effort de `risk_rules.yaml`.
- Tests:
  - `tests/test_risk_config_schema.py`: garantiza que `risk_rules.yaml` es estructuralmente válido.

Estado de validación:
- `python tools/validate_risk_config.py` → Errors: 0, Warnings: 4 (secciones recomendadas ausentes).
- `python -m pytest -q` → 48 tests OK.
- Snapshots:
  - `report/validate_risk_config_step5.txt`
  - `report/pytest_antigravity_step5.txt`
