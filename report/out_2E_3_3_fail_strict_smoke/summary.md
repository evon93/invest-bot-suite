# Calibration 2B Run Summary

**Timestamp**: 2025-12-30T17:57:59.219098
**Mode**: full
**Seed**: 42
**Git HEAD**: e3fb90d3087b

## Results

- Total grid size: 288
- Combinations run: 1
- OK: 1
- Errors: 0
- Duration: 0.03s

## Activity Analysis

- Active scenarios: 1 (100.00%)
- Inactive scenarios: 0 (0.00%)
- Active pass rate: 100.00%
- **Gate passed**: NO
- Gate fail reasons: active_n_below_min

## Score Formula

```
1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop
```

## Top-K Candidates

| Rank | Combo ID | Score | Sharpe | CAGR | MaxDD | Active |
|------|----------|-------|--------|------|-------|--------|
| 1 | ffae19fec604 | 0.9926 | 1.0702 | 0.1426 | -0.0993 | ✓ |

## Artifacts

- `results.csv` — Full results table
- `run_log.txt` — Execution log
- `topk.json` — Top-20 candidates with scores
- `run_meta.json` — Run metadata (hash, git, seed, timing, gates)
- `summary.md` — This file

## Reproducibility

```bash
python tools/run_calibration_2B.py --mode full --max-combinations 1 --seed 42
```