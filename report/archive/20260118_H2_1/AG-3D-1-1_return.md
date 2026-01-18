# AG-3D-1-1 Return Packet

## Resumen

Implementada carga de risk rules con validación fail-fast cuando `--strict-risk-config=1`.

**Commit**: `fed004c` — "3D.1: risk rules strict fail-fast + tests"

## Archivos Creados/Modificados

| Tipo | Archivo | Descripción |
|------|---------|-------------|
| [NEW] | `risk_rules_loader.py` | `load_risk_rules()` + `validate_risk_rules_critical()` |
| [NEW] | `tools/run_bus_integration_3D.py` | Runner 3D con `--strict-risk-config=1` default |
| [MODIFY] | `tools/run_live_integration_3C.py` | Añadido `--strict-risk-config=0` para compat |
| [NEW] | `tests/test_risk_rules_failfast_3D.py` | 12 tests de validación fail-fast |
| [NEW] | `tests/fixtures/invalid_risk_3D.yaml` | Fixture para generar error ejemplo |

## Critical Set

Keys validadas como críticas (derivadas de RiskManager v0.4):

- `position_limits` → dict
- `kelly` → dict
- `risk_manager` → dict

## Evidencias

| Archivo | Estado |
|---------|--------|
| `report/pytest_3D1_risk_rules.txt` | ✅ 12 passed |
| `report/3D1_failfast_example.txt` | ✅ Error "missing critical keys: ['kelly', 'risk_manager']" |
| `report/out_3D1_failfast/run_meta.json` | ✅ Generado (no commiteado por .gitignore) |
| `report/AG-3D-1-1_diff.patch` | ✅ Generado |
| `report/AG-3D-1-1_last_commit.txt` | ✅ Generado |

## Pytest Suite Completa

```
324 passed, 7 skipped, 7 warnings in 24.25s
Exit code: 0
```

## DoD Checklist

- [x] `--strict-risk-config=1` + config sin critical keys → ValueError explícito
- [x] Config válida → `report/out_3D1_failfast/run_meta.json` generado
- [x] `pytest tests/test_risk_rules_failfast_3D.py` PASS (12/12)
- [x] `report/pytest_3D1_risk_rules.txt` existe
- [x] `report/3D1_failfast_example.txt` existe
- [x] Commit realizado

## Decisiones Técnicas

1. **Módulo separado**: `risk_rules_loader.py` en raíz para reutilización por cualquier runner.
2. **No modificar RiskManager v0.4**: Solo validación/cableado, semántica intacta.
3. **Runner 3D con dry-run**: Genera `run_meta.json` sin simulación completa (extensible).
4. **Runner 3C compat**: `--strict-risk-config=0` por defecto para no romper flujos existentes.
