# Decisions Log — Antigravity Workflow v0.1

Formato recomendado:
- [YYYY-MM-DD HH:MM] [actor] [rama] — Descripción de la decisión.

---

- [PENDIENTE_FECHA] [EXECUTOR-BOT] [feature/workflow_antigravity_v0_1] — Creación de infraestructura mínima .ai (active_context, decisions_log, project_map).
- [2025-12-11 20:31] [EXECUTOR-BOT] [feature/workflow_antigravity_v0_1] — Creación de .ai/antigravity_operational_protocol.md v0.1
- [2025-12-11 20:46] [EXECUTOR-BOT] [feature/workflow_antigravity_v0_1] — Introducción de config_schema.py, tools/validate_risk_config.py y tests/test_risk_config_schema.py; risk_rules.yaml validado (Errors: 0, Warnings: 4).

## 2025-12-12 — Inicio Fase 2A: RiskContext v0.6 + modo monitor (workflow Antigravity)

- Branch: `feature/2A_riskcontext_v0_6_and_monitor`
- Contexto:
  - PLAN: PLAN_2A_RISKCONTEXT_V0_6_MONITOR_v0_2
  - Infraestructura Antigravity v0.1 activa (.ai/* revisado)

Snapshots iniciales 2A:
- `report/pytest_2A_before.txt` (baseline previo al workflow Antigravity, 47 tests OK).
- `report/pytest_2A_before_antigravity_integration.txt` (48 tests OK).
- `report/validate_risk_config_2A_before.txt`:
  - Errors: 0
  - Warnings: 4 (secciones recomendadas todavía ausentes):
    - `risk_limits`
    - `dd_limits`
    - `atr_stop`
    - `position_sizing`

Notas:
- No se ha tocado aún `risk_rules.yaml` ni `config_schema.py` en 2A.
- Próximos pasos: implementación de `RiskContextV06` completo, integración en RiskManager v0.5, modo `active|monitor` y observabilidad mínima.

- [2025-12-14 18:59] [ANTIGRAVITY/EXECUTOR] [feature/2A_riskcontext_v0_6_and_monitor] — 2.2 RiskContextV06 wiring fix aplicado (indentación OK, reasignaciones eliminadas, loop ATR sin shadowing). Snapshots: report/pytest_2A_2.2_partial_after_fix.txt (20 passed), report/pytest_2A_2.2_global_after_fix.txt (48 passed).

- [2025-12-16 17:45] [ANTIGRAVITY/EXECUTOR] [feature/2A_riskcontext_v0_6_and_monitor] — 2A/3.4 Monitor mode deltas fix: guardado snapshot `orig_deltas` antes de mutaciones Kelly y restauración en modo monitor para evitar shallow copy. Snapshots:
  - report/pytest_2A_3.4_monitor_tests_after_fix.txt (2 passed)
  - report/pytest_2A_3.4_risk_partial_after_fix.txt (20 passed)
  - report/pytest_2A_3.4_global_after_fix.txt (50 passed)
  - report/diff_2A_3.4_monitor_restore_deltas.patch

- [2025-12-16 18:20] [ANTIGRAVITY/EXECUTOR] [feature/2A_riskcontext_v0_6_and_monitor] — 2A/4.3 risk_logging tests (caplog) añadidos + integración emit_risk_decision_log en RiskManager. Snapshots:
  - report/pytest_2A_4.3_risk_logging_tests.txt (2 passed)
  - report/pytest_2A_4.3_risk_partial_after_logging.txt (24 passed)
  - report/pytest_2A_4.3_global_after_logging.txt (52 passed)
  - report/diff_2A_4.3_risk_logging_tests.patch

- [2025-12-17 18:18] [ANTIGRAVITY/EXECUTOR] [feature/2A_riskcontext_v0_6_and_monitor] — 2A/5.4: placeholders añadidos en risk_rules.yaml para eliminar warnings del validador. Evidencia: report/validate_risk_config_2A_after_warnings0.txt (Warnings:0) + report/diff_2A_5.4_remove_config_warnings.patch.

## 2025-12-28 — Decisiones 2E: Full Calibration Gate Useful

- [2025-12-28 13:45] [ANTIGRAVITY/EXECUTOR] [feature/2E_full_gate_useful] — **Decisión**: comportamiento default de exit code es **silencioso** (exit 0 siempre), con `gate_passed=false` y `suggested_exit_code=1` expuestos en `run_meta.json`. Esto permite que CI/Orchestrator decida si bloquear sin romper flujos actuales ni perder evidencia (artefactos siempre se generan).

- [2025-12-28 13:45] [ANTIGRAVITY/EXECUTOR] [feature/2E_full_gate_useful] — **Decisión**: añadido flag `--strict-gate` para modo estricto. Si `--strict-gate` y `--mode full` y `gate_passed=false` → exit 1. Esto permite backwards compatibility por defecto + opción de bloqueo explícito en CI.

- [2025-12-28 13:52] [ANTIGRAVITY/EXECUTOR] [feature/2E_full_gate_useful] — Commit `0611785`: implementación completa de activity/quality gates con columnas `is_active`, `rejection_*`, campos en meta, línea GATE en stdout. 61 tests pasando.

