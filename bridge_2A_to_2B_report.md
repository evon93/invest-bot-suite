# Bridge 2A → 2B Report

**Branch:** `feature/2A_riskcontext_v0_6_and_monitor`  
**Fecha:** 2025-12-16

---

## Estado Actual — Checklist 2A

| Componente | Estado | Evidencia |
|------------|--------|-----------|
| RiskContextV06 dataclass | ✅ Completo | `risk_context_v0_6.py` |
| Adapter dict → RiskContextV06 | ✅ Completo | `from_dict()` + wiring en filter_signal |
| Modo active/monitor | ✅ Completo | risk_manager.mode en yaml |
| would_* en monitor | ✅ Completo | risk_monitor payload |
| Deltas restore (shallow copy fix) | ✅ Completo | orig_deltas snapshot |
| Logging estructurado | ✅ Completo | `risk_logging.py` + emit_risk_decision_log |
| config_schema.py actualizado | ✅ Completo | Valida mode + logging.enabled |
| Tests globales | ✅ 52 passed | `pytest_2A_4.3_global_after_logging.txt` |

---

## Snapshots Relevantes

### Tests
- `report/pytest_2A_3.4_monitor_tests_after_fix.txt` — 2 passed (monitor mode)
- `report/pytest_2A_4.3_risk_logging_tests.txt` — 2 passed (caplog)
- `report/pytest_2A_4.3_risk_partial_after_logging.txt` — 24 passed
- `report/pytest_2A_4.3_global_after_logging.txt` — 52 passed
- `report/pytest_2A_5.1_config_schema_tests.txt` — 1 passed

### Validación Config
- `report/validate_risk_config_2A_before.txt` — Errors: 0, Warnings: 4
- `report/validate_risk_config_2A_after.txt` — Errors: 0, Warnings: 4

### Patches
- `report/diff_2A_3.4_monitor_restore_deltas.patch`
- `report/diff_2A_4.3_risk_logging_tests.patch`

---

## Deuda Técnica / Warnings

El validador reporta 4 secciones recomendadas ausentes en `risk_rules.yaml`:

1. `risk_limits` — Límites globales de riesgo
2. `dd_limits` — Configuración DD separada (actualmente usa `max_drawdown`)
3. `atr_stop` — Configuración ATR stop (actualmente embebida en atr_ctx)
4. `position_sizing` — Reglas de sizing separadas

> [!NOTE]
> Estos warnings son informativos. El sistema funciona con la estructura actual.

---

## Alcance 2B — Calibración y Backtests

### Objetivos
1. **Calibración DD/Kelly/ATR** — Definir valores óptimos para cada guardrail
2. **Batería de backtests paramétricos** — Grid sobre DD soft/hard, Kelly cap, ATR mult
3. **Métricas objetivo** — CAGR, max DD, Sharpe, Calmar, win rate

### Entregables esperados
- `risk_calibration_2B.yaml` — Parámetros calibrados
- `report/backtest_parametric_2B_*.csv` — Resultados de grid
- `report/calibration_analysis_2B.md` — Análisis y recomendaciones

### Dependencias
- 2A completo (✅)
- Backtester funcional (`backtest_initial.py`)
- Históricos de precios disponibles

---

## Archivos Clave 2A

| Archivo | Propósito |
|---------|-----------|
| `risk_context_v0_6.py` | Dataclass RiskContextV06 |
| `risk_manager_v0_5.py` | RiskManager con mode + guardrails |
| `risk_logging.py` | emit_risk_decision_log |
| `config_schema.py` | Validación best-effort |
| `tests/test_risk_mode_monitor_v0_5.py` | Tests monitor mode |
| `tests/test_risk_logging_v0_5.py` | Tests caplog |
