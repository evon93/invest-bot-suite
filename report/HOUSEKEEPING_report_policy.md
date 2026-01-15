# Report Housekeeping Policy

> **Ticket**: AG-H0-1-1  
> **Date**: 2026-01-15

---

## Tier 1: KEEP (Evidence — Commit-Tracked)

Estos archivos documentan decisiones y resultados de tickets. **No borrar**.

| Pattern | Example | Purpose |
|---------|---------|---------|
| `AG-*_return.md` | `AG-3N-4-1_return.md` | Return packet oficial |
| `AG-*_diff.patch` | `AG-3N-4-1_diff.patch` | Diff de cambios |
| `AG-*_last_commit.txt` | `AG-3N-4-1_last_commit.txt` | Evidencia de commit |
| `AG-*_notes.md` | `AG-2B-4-2_notes.md` | Notas fuera de scope |
| `bridge_*_report.md` | `bridge_3N_to_next_report.md` | Bridge docs |
| `HOUSEKEEPING_*.md` | Este archivo | Políticas |
| `risk_*.md` | specs de riesgo | Documentación técnica |
| `calibration_*.md` | calibration baselines | Specs de calibración |

---

## Tier 2: EPHEMERAL (Ignorar — Cleanup-Safe)

Archivos de diagnóstico transitorio. Ignorados en `.gitignore` y elegibles para limpieza local.

| Pattern | Example | Purpose |
|---------|---------|---------|
| `git_status_*.txt` | `git_status_3N0.txt` | Snapshot temporal de git |
| `head_*.txt` | `head_3N0_oneline.txt` | Dump de HEAD |
| `origin_main_*.txt` | `origin_main_head_3N0.txt` | Tracking origin |
| `pytest_*_snapshot.txt` | `pytest_3N0_snapshot.txt` | Snapshot de tests |
| `python_*.txt` | `python_3N0.txt` | Info de entorno |
| `smoke_*.txt` | `smoke_3N1_preset.txt` | Smoke logs |
| `ls_out_*.txt` | `ls_out_3N1.txt` | Listados de dirs |
| `det_*/` | `det_a/`, `det_b/` | Runs temporales determinism |
| `det_close_*/` | `det_close_a/` | Runs temporales |
| `working_tree_diff_*.txt` | Diff efímero |
| `ahead_*.txt` | Tracking ahead/behind |
| `ffonly_*.txt` | Merge info |
| `log_graph_*.txt` | Git log visual |
| `session_*.txt`, `session_*.md` | Session dumps |
| `os_release_*.txt` | Info de OS |
| `remote_*.txt` | Git remotes |
| `untracked_count_*.txt` | Conteo untracked |
| `help_*.txt` | CLI help dumps |
| `contains_*.txt` | Git contains checks |
| `in_main_*.txt` | Branch checks |
| `delta_*.md` | Deltas efímeros |
| `git_show_*.txt` | Git show dumps |

---

## Limpieza Local

### Dry-run (ver qué se borraría)

```bash
python tools/cleanup_report.py --dry-run
```

### Aplicar limpieza

```bash
python tools/cleanup_report.py --apply
```

### Filtrar por antigüedad (días)

```bash
python tools/cleanup_report.py --apply --days 14
```

---

## Notas

- Los archivos `ORCH_HANDOFF_*.md` ya están ignorados en `.gitignore` (ticket anterior).
- Los directorios `out_*` (runs de calibración) también están ignorados.
- Este documento es la referencia autoritativa para clasificación de archivos en `report/`.
