# AG-2I-1-1 Design Notes

## Active Rate Heuristic

The dashboard attempts to calculate "Active Rate" (percentage of combos not rejected) using the following priority:

1. `is_active` (boolean column)
2. `active` (boolean column)
3. Inference from any present "reason" column (`inactive_reason`, `rejection_reason`, etc.):
   - If row has empty string, None, or "nan" in reason column -> Considered Active.
   - Otherwise -> Rejected.

## Robust Metrics

Specifically looks for `worst_` columns (e.g. `worst_max_drawdown`) if present (from results_agg), or computes `min(max_drawdown)` from raw results.
Calculates P05 (5th percentile) for Sharpe and Calmar ratios if columns exist.

## Output Structure

- **Index.html**: Single file, designed for offline viewing.
- **Summary.json**: Contains parsed structured data. Can be used by other tools for meta-analysis.
- **Determinism**: Runs are sorted by folder path. HTML generation order is fixed.
