# AG-2G-2-1 Return Packet — Multi-Seed Calibration Spec & Tests

## Result

✅ Spec created and tests implemented. Parsing logic fixed.

## Summary

Completed 2G.2 tasks:

- **Spec**: `report/2G_multi_seed_spec.md` created. Defines `score_robust` (p05), "Worst" metrics (min), and ranking stability using Pearson on ranks.
- **Tests**: `tests/test_multiseed_spec_2G2.py` covers parsing (incl. empty/trailing parts), determinism, and aggregation logic consistency.
- **Fix**: Updated `parse_seeds` in `run_calibration_2B.py` to robustly handle negative seed check (removed generic try/except masking) and skip empty parts from split.

## Environment Traceability

- **Python**: 3.13.3
- **Pip**: 25.1.1
- **Path**: `C:\Program Files\Python313\python.exe` (System Python)

## Verification

- **Pytest**: All tests passed (6 passed, 2 warnings from numpy divide on small dataset).
- **Determinism**: Verified bit-exact output reproduction for same seeds.

## Files Changed

- `report/2G_multi_seed_spec.md` (New)
- `tests/test_multiseed_spec_2G2.py` (New)
- `tools/run_calibration_2B.py` (Fixed seed parsing exception & empty tokens)

## Artifacts

- `report/AG-2G-2-1_notes.md` — Notes on decisions
- `report/AG-2G-2-1_pytest.txt` — Test output
- `report/AG-2G-2-1_diff.patch` — patch

## Commit

**`f9f7f53`** — `2G.2: add multi-seed tests and spec`
