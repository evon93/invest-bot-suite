# AG-2G-2-1 Design Notes

## Aggregation Logic

Confirmed implementation details via code inspection:

- `score_robust` uses `np.percentile(x, 5)`.
- "Worst" logic uses `min()` for all metrics. Since Drawdown is negative, `min()` correctly identifies the deepest drawdown (e.g. -0.5 is "worse" than -0.1).
- NaNs are dropped before aggregation.

## Determinism

Tests verify that using the same seed list produces identical `results_by_seed.csv` and `results_agg.csv`.
This relies on `np.random.seed(current_seed)` being called inside the loop for each seed.

## Seed Parsing Fix

The original `parse_seeds` had a logic flaw where `try...except ValueError` intended for `int()` conversion was masking the explicit `ValueError` raised for negative seeds.
Fixed by moving the negative check outside the try/except block.
Also added check `if not p: continue` to handle trailing commas (e.g. `42,`).
