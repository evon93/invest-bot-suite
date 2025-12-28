# Active Context — Antigravity Workflow v0.1

- Proyecto: invest-bot-suite
- Rama actual: feature/workflow_antigravity_v0_1
- Última actualización manual: (rellenar fecha YYYY-MM-DD si se desea)

## Estado técnico reciente

- Baseline pytest antes de Antigravity: 47 tests OK (rama feature/2A_riskcontext_v0_6_and_monitor)
- Snapshot guardado en: report/pytest_2A_before.txt
- Rama de trabajo actual para Antigravity: feature/workflow_antigravity_v0_1

## Notas rápidas

- No incluir en commits de Antigravity:
  - report/pytest_2A_before.txt
  - risk_context_v0_6.py

## Paso 5 — Validación de configuración de riesgo (v0.1)

- Herramientas añadidas:
  - config_schema.py
  - tools/validate_risk_config.py
  - tests/test_risk_config_schema.py
- Snapshot validador: report/validate_risk_config_step5.txt
- Pytest global tras Paso 5: 48 tests OK (report/pytest_antigravity_step5.txt)

## Estado 2E — Full Calibration Gate (2025-12-28)

- **Rama**: `feature/2E_full_gate_useful`
- **Commit**: `0611785`

### Semántica ACTIVE/INACTIVE
- `is_active = num_trades > 0`
- Columnas de diagnóstico: `rejection_no_signal`, `rejection_blocked_risk`, `rejection_size_zero`, `rejection_price_missing`, `rejection_other`

### Ejecución

```bash
# Quick (smoke, sin gates)
python tools/run_calibration_2B.py --mode quick

# Full (con activity/quality gate)
python tools/run_calibration_2B.py --mode full

# Full estricto (exit 1 si gate falla)
python tools/run_calibration_2B.py --mode full --strict-gate
```

### Campos en run_meta.json (full mode)
- `gate_passed`: bool — true si pasa activity + quality gate
- `insufficient_activity`: bool — true si active_n y active_rate bajo thresholds
- `gate_fail_reasons`: lista — ej. `["insufficient_activity"]`
- `suggested_exit_code`: 0|1 — 1 si gate falla

### Thresholds (configs/risk_calibration_2B.yaml)
```yaml
profiles.full.activity_gate:
  min_active_n: 20
  min_active_rate: 0.60
  min_active_pass_rate: 0.70
```

