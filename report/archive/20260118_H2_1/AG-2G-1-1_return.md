# AG-2G-1-1 Return Packet — Multi-Seed Calibration Robustness

## Result

✅ Multi-seed calibration implemented.

## Features

| Feature | Description |
|---------|-------------|
| `--seeds` CLI | Comma-separated seeds: `--seeds 42,123,456` |
| `--seed` legacy | Single seed backward compat |
| `results_by_seed.csv` | All combos×seeds with seed column |
| `results_agg.csv` | Aggregated: mean, median, p05, p95, worst, score_robust |
| Ranking stability | spearman_mean, spearman_min, topk_overlap in run_meta.json |

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `tools/run_calibration_2B.py` | +293 | Multi-seed loop, aggregation, stability |
| `tests/test_calibration_runner_2B.py` | +1 | Updated seed→seeds assertion |
| `tests/test_calibration_multiseed_2G.py` | +56 | 6 unit tests for parse_seeds |

## Aggregation Formula

```python
score_robust = p05(score)  # 5th percentile across seeds
```

Metrics aggregated: mean, median, p05, p95, worst

## Stability Metrics

- **spearman_mean**: Mean pairwise Spearman correlation of rankings
- **spearman_min**: Minimum pairwise Spearman correlation
- **topk_overlap**: Mean Jaccard overlap of top-10 sets

## Tests

- 167 passed, 6 skipped

## Commit

**`6d696f1`** — `2G.1: add multi-seed calibration robustness outputs`
