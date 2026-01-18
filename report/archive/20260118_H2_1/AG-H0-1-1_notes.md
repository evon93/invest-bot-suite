# AG-H0-1-1 Notes

## Inventario Inicial

- **Total archivos en report/**: ~1100+
- **Untracked detectados**: ~130 archivos
- **Patrones efímeros identificados**: 27 (files) + 2 (dirs)

## Decisiones

1. **Patrón `pytest_*_snapshot.txt`**: Solo snapshots, no todos los pytest_*.txt
   - Motivo: algunos pytest logs son evidencia de tickets (e.g., `pytest_3N1_postmerge.txt`)
   - Los que no son snapshots deberían renombrarse a `AG-*_pytest.txt` en futuros tickets

2. **Directorios `det_*/`**: Incluidos como efímeros
   - Usados para tests de determinismo, regenerables

3. **`ORCH_HANDOFF_*.md`**: Ya ignorados en ticket anterior
   - No duplicados en H0.1

## Anomalías Observadas

- Hay archivos `pytest_3*_postmerge.txt` untracked que no coinciden con `*_snapshot.txt`
- Considerar para futuro ticket: unificar nomenclatura de pytest logs

## Ideas Fuera de Scope

1. Rotación automática de archivos antiguos
2. Integración con CI para limpiar runs de calibración
3. Dashboard de espacio usado en report/

## AUDIT_SUMMARY

- **Ficheros modificados**: `.gitignore`, `tools/cleanup_report.py`, `report/HOUSEKEEPING_report_policy.md`
- **Cambios**: Política de housekeeping, patrones de ignore, script de limpieza
- **Riesgos**: Ninguno identificado, cambios no afectan lógica de trading/risk
- **Dudas abiertas**: Nomenclatura de pytest logs no unificada
