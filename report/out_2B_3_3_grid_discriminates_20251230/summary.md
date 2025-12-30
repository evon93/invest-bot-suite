# Calibration 2B Run Summary

**Timestamp**: 2025-12-30T22:47:10.905526
**Mode**: full
**Seed**: 42
**Git HEAD**: 51fb8f8e3d91

## Results

- Total grid size: 288
- Combinations run: 24
- OK: 24
- Errors: 0
- Duration: 0.43s

## Activity Analysis

- Active scenarios: 24 (100.00%)
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
| 1 | 9daf5a15114e | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 2 | 671ea044ad47 | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 3 | 55f9ee043f57 | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 4 | e5c570b4dcef | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 5 | 7a63e2010a20 | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 6 | fe30318401ff | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 7 | 5c455bd3ac35 | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 8 | 00701c56debb | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 9 | dc3c983f74bc | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |
| 10 | c7fe42239dff | 0.3458 | 0.8164 | 0.1065 | -0.1587 | ✓ |

## Artifacts

- `results.csv` — Full results table
- `run_log.txt` — Execution log
- `topk.json` — Top-20 candidates with scores
- `run_meta.json` — Run metadata (hash, git, seed, timing, gates)
- `summary.md` — This file

## Reproducibility

```bash
python tools/run_calibration_2B.py --mode full --max-combinations 24 --seed 42
```