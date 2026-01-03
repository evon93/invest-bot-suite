# QA Notes: Ranking Stability (AG-2G-1-QA)

## Function: `compute_ranking_stability`

Located in `tools/run_calibration_2B.py`.

### Logic

1. **Inputs**: list of result dicts, list of seeds.
2. **Pivoting**: Creates a matrix (rows=combo_id, cols=seed) of `score`.
3. **Spearman**:
   - Iterates pairwise over seeds (seed1 vs seed2).
   - Computes rank (`pivot[s].rank(ascending=False)`).
   - Computes Spearman correlation using **Pearson on ranks** (`method='pearson'`) to avoid SciPy dependency.
   - Aggregates: Mean and Min of pairwise correlations.
4. **TopK Overlap**:
   - `K=10`.
   - Extracts top-10 combo_ids per seed.
   - Computes pairwise Jaccard index: $|A \cap B| / |A \cup B|$.
   - Aggregates: Mean.

### Guardrails

- **Seeds < 2**: Returns 1.0 stability (trivial stability).
- **Empty results**: Returns 0.0.
- **N < 2 rows**: Spearman skipped (needs >= 2 points), returns 0.0 if no pairs computable.
- **TopK > N**: `nlargest(K)` returns N items. Overlap is computed on full sets (likely 1.0 if stable).

### Edge Cases

- **Identical rankings**: Spearman should be 1.0.
- **Inverted rankings**: Spearman should be -1.0.
- **Single row**: Spearman undefined (returned as 0.0 currently).
- **Seeds with missing data**: `valid.sum() < 2` check handles NaNs.

### snippet

```python
def compute_ranking_stability(results_by_seed, seeds, score_col="score"):
    if len(seeds) < 2:
        return {"spearman_mean": 1.0, ...}
    # ... pivot ...
    for i, s1 in enumerate(seed_cols):
        for s2 in seed_cols[i+1:]:
            # ...
            # Pearson on ranks == Spearman (avoids scipy)
            corr = r1[valid].corr(r2[valid], method='pearson')
```
