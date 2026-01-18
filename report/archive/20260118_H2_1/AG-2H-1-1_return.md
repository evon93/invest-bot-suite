# AG-2H-1-1 Return Packet — TopK Freeze Tool

## Result

✅ `tools/freeze_topk_2H.py` implemented.

## Summary

The tool deterministically selects the best configuration from multi-seed calibration results (`results_agg.csv`).

- **Input**: CSV with `score_robust` (or `score`).
- **Determinism**: Sorts by score (desc) + stable tie-breaker (`combo_id` or `param_id`).
- **Audit**: Output parameters include `source_results_agg_sha256` and `git_commit`.
- **Outputs**:
  - `configs/best_params_2H.json`: Single best config.
  - `report/topk_freeze_2H.json`: List of top K configs.

## Environment Traceability

- **Python**: 3.13.3
- **Pip**: 25.1.1
- **Path**: `C:\Program Files\Python313\python.exe`

## Verification

- **Pytest**: `tests/test_freeze_topk_2H.py` passed (4 tests).
- **Checks**: Verified binary determinism (byte-exact output on repeated runs) and schema validity.

## Files Changed

- `tools/freeze_topk_2H.py` (New CLI tool)
- `tests/test_freeze_topk_2H.py` (New tests)

## Artifacts

- `report/AG-2H-1-1_notes.md` — Design decisions
- `report/AG-2H-1-1_pytest.txt` — Test logs
- `report/AG-2H-1-1_diff.patch` — patch

## Commit

**`e3bf2e0`** — `2H.1: freeze robust topK config`
