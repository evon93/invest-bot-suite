# Return Packet — AG-2B-3-3A

**Ticket**: AG-2B-3-3A  
**Fecha**: 2025-12-22T22:08

## Output Directory

```
output.dir = report/calibration_2B
```

Source of truth: `configs/risk_calibration_2B.yaml` → `output.dir`

## Artefactos en `report/calibration_2B/`

| Archivo          | Tamaño  | Descripción                              |
|------------------|---------|------------------------------------------|
| `results.csv`    | 658 B   | Resultados completos de todas las combos |
| `run_log.txt`    | 1437 B  | Log de ejecución con timestamps          |
| `summary.md`     | 979 B   | Resumen Markdown con top-k y stats       |
| `topk.json`      | 1633 B  | Top-20 candidatos ordenados por score    |
| `run_meta.json`  | 285 B   | Metadata: hash, git, seed, timing        |

## Meta de Ejecución

```json
{
  "config_hash": "0aa0669081dc969a",
  "git_head": "1fb093e1c944",
  "seed": 42,
  "mode": "quick",
  "total_grid": 216,
  "running": 3,
  "ok": 3,
  "errors": 0,
  "duration_s": 0.32,
  "output_dir": "report/calibration_2B"
}
```

## Comando Reproducible

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```

## Artefactos DoD en `report/`

- [x] `AG-2B-3-3A_return.md` (este archivo)
- [x] `AG-2B-3-3A_diff.patch` (294 líneas, no vacío)
- [x] `AG-2B-3-3A_run.txt` (copia de run_log.txt)
