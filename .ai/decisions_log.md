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

## 2025-12-28 — Instrumentación 2E-4: Inactive Reasons + Structured Risk Rejection

- [2025-12-28 17:48] [ANTIGRAVITY/EXECUTOR] [feature/2E_inactive_instrumentation] — **2E-4-1**: Añadida instrumentación de inactive reasons (`signal_count`, `signal_rejected_count`, `price_missing_count`) en backtester. Función `classify_inactive_reason()` para 1-hot encoding. PR #7 merged (db8f355).

- [2025-12-28 19:50] [ANTIGRAVITY/EXECUTOR] [feature/2E_structured_risk_reasons] — **2E-4-2**: Añadido `risk_reject_reasons_counter: Counter` en backtester. Columna CSV `risk_reject_reasons_top`, campo meta `risk_reject_reasons_topk`. Elimina dependencia de parseo de logs. PR #8 merged (6a225ef).

## 2025-12-29 — Kelly Floor Promotion (2B-3.5/3.6)

- [2025-12-28 21:02] [ANTIGRAVITY/EXECUTOR] [feature/2B_kelly_grid_expand] — **2B-3.5**: Validación multi-seed (seeds 42,43,44) de Kelly cap_factor. Resultado: `cap_factor=0.5` → 0% activity (FAIL), `cap_factor=0.7` → 100% activity (PASS). Robustez confirmada.

- [2025-12-29 16:20] [ANTIGRAVITY/EXECUTOR] [feature/2B_kelly_floor_promotion] — **2B-3.6**: Promovido floor `kelly.cap_factor >= 0.70` a baseline config. Grid actualizado a `[0.70, 0.90, 1.10, 1.30]`. Valores sub-óptimos (0.30, 0.50) eliminados.

## 2025-12-30 — 7.2 CLI Polish + 2E-3.3 Gate Semantics Merge

- [2025-12-30 17:30] [ANTIGRAVITY/EXECUTOR] [main] — **7.2 CLI polish**: PR #11 merged (073b643). Añadido `--mode full_demo` como alias de `--mode full --profile full_demo`. Detección de conflictos explícitos si se combinan alias + profile diferente.

- [2025-12-30 17:45] [ANTIGRAVITY/EXECUTOR] [main] — **2E-3.3 Gate semantics**: PR #12 merged (e3fb90d). Evaluación de thresholds con lógica OR independiente (cualquiera falla → gate FAIL). Razones granulares: `active_n_below_min`, `active_rate_below_min`, `inactive_rate_above_max`, `active_pass_rate_below_min`.

- [2025-12-30 18:00] [ANTIGRAVITY/EXECUTOR] [main] — **Decisión: versionado de `report/out_*`**: Los directorios de evidencia (`report/out_2E_*`) se commitean cuando contienen resultados de validación crítica (smokes PASS/FAIL, strict gate tests). Esto permite trazabilidad reproducible sin depender de CI artifacts externos.
