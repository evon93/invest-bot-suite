# AG-3A-2-1 Paper Trading Loop

## Veredicto

- **Estado**: IMPLEMENTED
- **Runner**: `tools/run_paper_loop_3A.py`
- **Output Verified**: `report/runs/3A_paper_smoke/events.ndjson` contiene traza completa.
- **Metrics Verified**: `report/runs/3A_paper_smoke/metrics.json`
- **Tests**: `tests/test_paper_loop_3A.py` (Integration passing).

## Entregables

1. **Runner CLI**: acepta signals NDJSON, valida con `risk_rules.yaml` y genera eventos simulados.
2. **Contracts Usage**: Usa `contracts.event_messages` para serialización estricta.
3. **Smoke Data**: `examples/signals_3A.ndjson` creado.

## Artefactos

- `report/AG-3A-2-1_diff.patch`
- `report/AG-3A-2-1_run_log.txt` (Log combinado Pytest + Run + Head)
- `report/AG-3A-2-1_last_commit.txt`

## Próximos Pasos (3A)

- Integrar feed de precios real (o simulado via CSV histórico).
- Implementar métricas de latencia y health check.
