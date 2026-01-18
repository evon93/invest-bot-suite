# AG-3A-3-1 Observability Metrics

## Veredicto

- **Estado**: IMPLEMENTED
- **Metrics**: Implementadas en `tools/run_paper_loop_3A.py`.
- **Verified**: `tests/test_paper_loop_3A.py` valida presencia y rangos de KPIs.

## Métricas Implementadas

- **Financial**: `max_drawdown_pct`, `max_gross_exposure_pct`.
- **Activity**: `active_rate`, `n_allowed`, `n_rejected`.
- **System**: `latency_ms_mean`, `latency_ms_p95`.
- **Traceability**: `trace_id` propagado en todos los eventos.

## Entregables

1. **Code Update**: Runner calcula NAV, Exposure y Latencia por evento.
2. **Test Update**: Verificación estructural de `metrics.json` y rangos lógicos.
3. **Output**: `metrics.json` enriquecido.

## Artefactos

- `report/AG-3A-3-1_diff.patch`
- `report/AG-3A-3-1_run_log.txt`
- `report/AG-3A-3-1_pytest.txt`

## Próximos Pasos (3A)

- Conectar feed de precios externo (CSV/Historic).
