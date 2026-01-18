# AG-H2-3-1 Return Packet

## Metadata

| Campo | Valor |
|-------|-------|
| Ticket | AG-H2-3-1 |
| Objetivo | Supervisor exit codes coherentes (0=graceful, 2=error) |
| Status | **PASS** |
| Fecha | 2026-01-18 |

## Baseline

- Branch: `main`
- HEAD: `6ad421286a2e0e14d6be4c7d9c0f082db1405d7a`

## Cambios realizados

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `tools/supervisor_live_3E_3H.py` | Línea 257: actualizar docstring. Línea 272: `return 2` |
| `tests/test_supervisor_3H.py` | Línea 146: `assert result == 2` |
| `tests/test_supervisor_graceful_shutdown_3I2.py` | Línea 210: `assert result == 2` |

### Archivo creado

| Archivo | Descripción |
|---------|-------------|
| `tests/test_supervisor_exit_codes_H23.py` | 4 nuevos tests para exit code semantics |

## Contrato final

| Escenario | Exit code |
|-----------|-----------|
| Child exit 0 | 0 |
| Graceful shutdown (SIGINT/SIGTERM/StopController) | 0 |
| Max_restarts exceeded | **2** |
| Child error sin reinicio | **2** |

## Verificación

| Test | Resultado |
|------|-----------|
| pytest test_supervisor_exit_codes_H23.py | 4 passed ✓ |
| pytest supervisor tests (27 total) | 27 passed ✓ |
| pytest full | 751 passed, 11 skipped, 2 warnings ✓ |

## AUDIT_SUMMARY

- **Archivos modificados**: 3 (supervisor + 2 test files)
- **Archivos creados**: 1 (nuevo test file)
- **Descripción**: Exit code 2 para error en supervisor (antes era variable)
- **Riesgos**: Ninguno. Cambio semántico menor, tests actualizados.
