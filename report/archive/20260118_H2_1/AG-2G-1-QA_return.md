# AG-2G-1-QA Return Packet — Ranking Stability QA

## Result

✅ QA Completed. Ranking stability logic hardened and verified.

## QA Summary

| Item | Status | Notes |
|------|--------|-------|
| **Ranking Logic** | Verified | Uses Spearman (via Pearson on ranks) + TopK Jaccard |
| **Dependencies** | **NO SciPy** | Replaced `method='spearman'` with `method='pearson'` on ranks |
| **Edge Cases** | Covered | Identical, Inverted, N<2, Disjoint sets |
| **Tests** | Passed | 5/5 new tests in `tests/test_ranking_stability_2G.py` |

## Environment Traceability

The execution environment used for verification:

- **Python**: 3.13.3
- **Pip**: 25.1.1
- **Path**: `C:\Program Files\Python313\python.exe` (System Python, no venv detected active)

## Files Changed

| File | Change |
|------|--------|
| `tools/run_calibration_2B.py` | Replaced Spearman method to remove implicit SciPy dep |
| `tests/test_ranking_stability_2G.py` | Added QA tests for stability logic |

## Artifacts

- `report/AG-2G-1-QA_notes.md` — Logic detailed analysis
- `report/AG-2G-1-QA_pytest.txt` — Test results

## Commit

**`HEAD`** — `2G.1: QA ranking stability edge cases`
