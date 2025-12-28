# Calibration 2B Run Summary

**Timestamp**: 2025-12-28T16:38:04.630109
**Mode**: full
**Seed**: 42
**Git HEAD**: 3a82f71c8c80

## Results

- Total grid size: 216
- Combinations run: 40
- OK: 40
- Errors: 0
- Duration: 3.97s

## Activity Analysis

- Active scenarios: 13 (32.50%)
- Inactive scenarios: 27 (67.50%)
- Active pass rate: 100.00%
- **Gate passed**: YES

## Score Formula

```
1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop
```

## Top-K Candidates

| Rank | Combo ID | Score | Sharpe | CAGR | MaxDD | Active |
|------|----------|-------|--------|------|-------|--------|
| 1 | ffae19fec604 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 2 | fa94dabfc7d9 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 3 | abd891f17a53 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 4 | 9daf5a15114e | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 5 | 7a63e2010a20 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 6 | dc3c983f74bc | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 7 | c2d7b03329c4 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 8 | 59aac2ce9c2d | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 9 | a7ba7b95a053 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 10 | 34ae485cdeaf | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |

## Artifacts

- `results.csv` — Full results table
- `run_log.txt` — Execution log
- `topk.json` — Top-20 candidates with scores
- `run_meta.json` — Run metadata (hash, git, seed, timing, gates)
- `summary.md` — This file

## Reproducibility

```bash
python tools/run_calibration_2B.py --mode full --max-combinations 40 --seed 42
```