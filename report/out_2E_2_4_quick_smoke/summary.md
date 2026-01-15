# Calibration 2B Run Summary

**Timestamp**: 2025-12-28T15:00:40.653477
**Mode**: quick
**Seed**: 42
**Git HEAD**: 7cfe98e0d045

## Results

- Total grid size: 216
- Combinations run: 12
- OK: 12
- Errors: 0
- Duration: 0.34s

## Activity Analysis

- Active scenarios: 4 (33.33%)
- Inactive scenarios: 8 (66.67%)
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
| 5 | c648aadd02dc | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |
| 6 | 2a7b39f06e64 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |
| 7 | 96764a80cf0c | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |
| 8 | c7a8cf081f41 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |
| 9 | a4e7cc151807 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |
| 10 | e1d02956d405 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | ✗ |

## Artifacts

- `results.csv` — Full results table
- `run_log.txt` — Execution log
- `topk.json` — Top-20 candidates with scores
- `run_meta.json` — Run metadata (hash, git, seed, timing, gates)
- `summary.md` — This file

## Reproducibility

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 12 --seed 42
```