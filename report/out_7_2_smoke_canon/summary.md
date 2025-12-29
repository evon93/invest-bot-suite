# Calibration 2B Run Summary

**Timestamp**: 2025-12-29T20:35:55.163794
**Mode**: full
**Seed**: 42
**Git HEAD**: 1ad7c3898683

## Results

- Total grid size: 288
- Combinations run: 40
- OK: 40
- Errors: 0
- Duration: 0.47s

## Activity Analysis

- Active scenarios: 40 (100.00%)
- Inactive scenarios: 0 (0.00%)
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
| 2 | 0576d1c2bfe6 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 3 | 2411a44ce582 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 4 | f93ac29cc62d | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 5 | fa94dabfc7d9 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 6 | c9b8c7cf9b5f | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 7 | 2368daacf8d9 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 8 | 6ecd3e5356e1 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 9 | abd891f17a53 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |
| 10 | 70d95e17dd21 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |

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