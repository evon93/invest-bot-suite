# Active Context — invest-bot-suite

- **Proyecto**: invest-bot-suite
- **Rama actual**: `main`
- **Última actualización**: 2025-12-28

## Estado actual: 2E Phase 4 completado

- **HEAD**: `6a225ef` (Merge PR #8: structured risk rejection reasons)
- **Fase**: 2E-4-1/2E-4-2 completados (Inactive Reasons Instrumentation)
- **Tests**: 127 passed
- **Validador**: 0 errors, 0 warnings

## PRs Mergeados Recientemente

| PR | Commit | Descripción |
|----|--------|-------------|
| #7 | db8f355 | 2E-4-1: inactive reason breakdown |
| #8 | 6a225ef | 2E-4-2: structured risk rejection reasons |

## Instrumentación 2E-4 Añadida

### Contrato de Datos

**results.csv**:
- `is_active`: boolean (combo produjo trades)
- `rejection_no_signal`, `rejection_blocked_risk`, `rejection_size_zero`, `rejection_price_missing`, `rejection_other`: 1-hot flags
- `risk_reject_reasons_top`: string compacta (ej. `kelly_cap:ETF:181|dd_soft:5`)

**run_meta.json**:
- `rejection_reasons_agg`: conteo por categoría
- `top_inactive_reasons`: lista ordenada
- `risk_reject_reasons_topk`: Counter global de motivos de riesgo (ej. `{"kelly_cap:ETF": 4887}`)

### Por qué (rationale)

- Evitar parseo de logs/stderr (PowerShell genera ruido UTF-16).
- Diagnósticos estructurados permiten CI/orchestrator consumir datos directamente.

## Cómo ejecutar tests

```powershell
python -m pytest -q
python tools/validate_risk_config.py --config risk_rules.yaml
```

## Próximo paso

Ver `report/AG-2E-4-3_handoff.md` para roadmap.
