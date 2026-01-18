# AG-3A-3-2 Hardening Observability

## Veredicto

- **Estado**: HARDENED
- **Metrics**: `rejected_by_reason` (alias) implementado. Normalización de razones implementada.
- **Robustness**: P95 sin dependencia externa y safe guard.
- **Verified**: `tests/test_paper_loop_3A.py` valida alias y robustez.

## Cambios

1. **Normalization**: Listas/Dicts en `reasons` se convierten a strings estables recortados (max 100 chars).
2. **Alias**: `metrics.json` expone `rejected_by_reason` (para alineación futura) igual a `rejection_reasons`.
3. **Latency**: Cálculo P95 manual optimizado y seguro.

## Artefactos

- `report/AG-3A-3-2_diff.patch`
- `report/AG-3A-3-2_run_log.txt`
- `report/AG-3A-3-2_pytest.txt`

## Próximos Pasos (3A)

- Completar integración de datos reales.
