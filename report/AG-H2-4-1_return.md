# AG-H2-4-1 Return Packet

## Metadata

| Campo | Valor |
|-------|-------|
| Ticket | AG-H2-4-1 |
| Objetivo | Consolidar workflows CI reduciendo duplicación |
| Status | **PASS** |
| Fecha | 2026-01-18 |

## Baseline

- Branch: `main`
- HEAD: `8d0562364d9d2879174eda672316b20716bc52d1`

## Resultado

**15 → 8 workflows** (47% reducción)

### Acciones ejecutadas

| Acción | Workflows |
|--------|-----------|
| ✅ Mantener | `robustness_*.yml`, `e2e_smoke_2J.yml`, `smoke_3B/3H/3I/3J.yml` |
| ⬆️ Expandir | `ci.yml` (5 jobs: check, tests, h1-gate, graceful-shutdown, edge-tests) |
| 🔀 Merge → ci.yml | `h1_gate.yml`, `graceful_shutdown_3O.yml`, `edge_tests.yml` |
| ❌ Delete | `smoke_3C.yml`, `smoke_3E.yml`, `smoke_3F.yml`, `smoke_3G.yml` |

### Triggers preservados

- **edge-tests**: `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
  - Solo push a main, NO en PRs (preserva comportamiento original)

## Verificación

| Test | Resultado |
|------|-----------|
| pytest full | 751 passed, 11 skipped, 2 warnings ✓ |

## Artefactos generados

- `report/AG-H2-4-1_return.md`
- `report/AG-H2-4-1_last_commit.txt`
- `report/AG-H2-4-1_git_status_after.txt`
- `report/AG-H2-4-1_diff.txt`
- `report/AG-H2-4-1_pytest_full.txt`
- `report/AG-H2-4-1_workflows_ls_before.txt`
- `report/AG-H2-4-1_workflows_ls_after.txt`
- `report/AG-H2-4-1_ci_triggers_excerpt.txt`
- `report/ci_workflows_map_H24.md`

## AUDIT_SUMMARY

- **Archivos modificados**: `.github/workflows/ci.yml` (expandido con 4 jobs)
- **Archivos eliminados**: 7 workflows redundantes
- **Archivos fuera de scope**: Ninguno tocado
- **Riesgos**: Ninguno. Consolidación sin cambio de lógica.
