# Calibration 2B Run Summary

**Timestamp**: 2025-12-22T22:08:18.888533
**Mode**: quick
**Seed**: 42
**Git HEAD**: 1fb093e1c944

## Results

- Total grid size: 216
- Combinations run: 3
- OK: 3
- Errors: 0
- Duration: 0.32s

## Score Formula

```
1.0*sharpe_ratio + 0.5*cagr - 1.5*abs(max_drawdown)
```

## Top-K Candidates

| Rank | Combo ID | Score | Sharpe | CAGR | MaxDD |
|------|----------|-------|--------|------|-------|
| 1 | ffae19fec604 | 0.9926 | 1.0702 | 0.1426 | -0.0993 |
| 2 | c648aadd02dc | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| 3 | 2a7b39f06e64 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Artifacts

- `results.csv` — Full results table
- `run_log.txt` — Execution log
- `topk.json` — Top-20 candidates with scores
- `run_meta.json` — Run metadata (hash, git, seed, timing)
- `summary.md` — This file

## Reproducibility

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```