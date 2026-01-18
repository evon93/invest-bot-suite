# AG-2H-1-1 Design Notes

## Determinism

Achieved by:

1. Sorting by `score_robust` (or `score`) descending.
2. Using a stable tie-breaker:
   - Primary: `combo_id` (ascending)
   - Secondary: `param_id` (ascending)
   - Fallback: SHA256 of JSON-serialized parameter values (stable sorting of keys).
3. Using `json.dump(sort_keys=True)` for output.
4. Avoiding timestamp fields in the output JSON (only commit hash and input file hash).

## Parameter Heuristic

To determine which columns are "parameters":

1. Prefer columns starting with `param_`.
2. Fallback: Exclude known non-parameter columns (metrics like `sharpe`, metadata like `timestamp`) and take the rest.

## Audit Trail

Output JSONs include:

- `source_results_agg_path`
- `source_results_agg_sha256` (content-based ID)
- `git_commit` (code version)
This links the chosen config back to the exact code and results file used.
