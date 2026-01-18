# AG-H0-1-1 Return Packet

## Resumen

Definido housekeeping robusto de `report/`:

- **Política**: `report/HOUSEKEEPING_report_policy.md` con clasificación Tier 1 (keep) y Tier 2 (ephemeral)
- **Gitignore**: Añadidos 27 patrones para ignorar snapshots de diagnóstico transitorio
- **Cleanup tool**: `tools/cleanup_report.py` con dry-run por defecto

## Patrones Ignorados

| Categoría | Patrón | Motivo |
|-----------|--------|--------|
| Git status | `git_status_*.txt`, `head_*.txt` | Snapshots temporales |
| Pytest | `pytest_*_snapshot.txt` | Snapshots de tests |
| Entorno | `python_*.txt`, `os_release_*.txt` | Info de entorno |
| Smoke | `smoke_*.txt`, `ls_out_*.txt` | Logs efímeros |
| Git ops | `origin_main_*.txt`, `working_tree_diff_*.txt` | Tracking |
| Determinism | `det_*/`, `det_close_*/` | Runs temporales |

Ver lista completa en `.gitignore` y `HOUSEKEEPING_report_policy.md`.

## Limpieza Local

```bash
# Dry-run (ver candidatos)
python tools/cleanup_report.py --dry-run

# Aplicar limpieza
python tools/cleanup_report.py --apply

# Solo archivos > 7 días
python tools/cleanup_report.py --apply --days 7
```

## Evidencia

### pytest -q (PASS)

```
750 passed, 11 skipped, 7 warnings in 237.03s
```

### git status -sb (post-commit)

```
## feature/AG-3N-4-1_closeout
# efímeros ignorados correctamente
```

### Cleanup dry-run

```
Total: 124 files, 4 dirs = 228.8 KB
(Use --apply to delete)
```

## Commit

```
f794a4c H0.1: report housekeeping policy + ignore + cleanup tool
```

## Archivos Modificados

- `.gitignore` (añadidos 27 patrones)
- `tools/cleanup_report.py` (nuevo, 200 LOC)
- `report/HOUSEKEEPING_report_policy.md` (nuevo, política)

---

**Status**: PASS
