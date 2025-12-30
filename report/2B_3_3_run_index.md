# 2B-3.3 Run Index — Full Grid (288 combos)

## Runs

| Campo | Full | Strict |
|-------|------|--------|
| **Folder** | `out_2B_3_3_grid_full_20251230_191032` | `out_2B_3_3_grid_strict_20251230_193344` |
| **Timestamp** | 2025-12-30T19:10:36 | 2025-12-30T19:33:47 |
| **Git HEAD** | `c299848251c4` | `3d63d26b4871` |
| **Config Hash** | `6e8214a42d39b659` | `6e8214a42d39b659` |
| **Seed** | 42 | 42 |
| **Mode** | full | full |
| **Profile** | full_demo | full_demo |
| **Total Grid** | 288 | 288 |
| **Running** | 288 | 288 |
| **OK** | 288 | 288 |
| **Errors** | 0 | 0 |
| **Duration** | 3.20s | 3.08s |
| **Active Rate** | 100% | 100% |
| **Gate Passed** | ✅ | ✅ |
| **Exit Code** | 0 | 0 |

## Risk Rejection Reasons (Top)

| Reason | Count |
|--------|-------|
| `position_limits` | 1728 |
| `dd_soft` | 1584 |

---

## Cómo Reproducir

### Full Grid (no strict gate)

```powershell
python tools/run_calibration_2B.py `
  --mode full `
  --seed 42 `
  --output-dir report/out_2B_3_3_grid_full_$(Get-Date -Format 'yyyyMMdd_HHmmss')
```

### Strict Gate

```powershell
python tools/run_calibration_2B.py `
  --mode full `
  --strict-gate `
  --seed 42 `
  --output-dir report/out_2B_3_3_grid_strict_$(Get-Date -Format 'yyyyMMdd_HHmmss')
```

---

## Artefactos por Run

Cada carpeta contiene:

- `results.csv` — Métricas por combo
- `run_log.txt` — Log de ejecución
- `topk.json` — Top-20 candidatos
- `run_meta.json` — Metadata de reproducibilidad
- `summary.md` — Resumen ejecutivo
