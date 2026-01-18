# AG-2G-1-1 Design Notes

## Score Aggregation

For multi-seed runs, `score_robust` = p05 of all scores across seeds.
This penalizes high variance results.

## Stability Metrics

Uses pandas `corr(method='spearman')` - no scipy dependency.

Computes pairwise Spearman for all seed pairs:

```python
r1.corr(r2, method='spearman')
```

TopK overlap uses Jaccard:

```python
overlap = |A ∩ B| / |A ∪ B|
```

## Backward Compatibility

- `--seed 42` (legacy) → seeds=[42]
- `--seeds "42"` (default) → seeds=[42]
- Existing configs unchanged (single seed behavior)

## run_meta.json Fields (2G)

```json
{
  "seeds": [42, 123, 456],
  "n_seeds": 3,
  "spearman_mean": 0.95,
  "spearman_min": 0.89,
  "topk_overlap": 0.70
}
```
