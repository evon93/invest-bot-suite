# AG-2I-1-1 Return Packet — Dashboard Builder

## Result

✅ `tools/build_dashboard.py` implemented.

## Summary

The tool generates a single-file static HTML dashboard (`report/dashboard/index.html`) from multiple calibration run directories.

- **Robustness**: Handles missing files/columns gracefully (N/A).
- **Heuristics**: Automatically detects active rates (active column or reasons) and robust metric columns.
- **Self-contained**: HTML uses inline CSS with no external dependencies.
- **JSON Summary**: Also outputs `summary.json` for programmatic consumption.

## Environment Traceability

- **Python**: 3.13.3
- **Pip**: 25.1.1
- **Path**: `C:\Program Files\Python313\python.exe`

## Verification

- **Pytest**: `tests/test_build_dashboard_2I.py` passed (2 tests covering generation, metric extraction, and graceful failure).
- **Manual**: Verified glob expansion logic and consistent output structure.

## Files Changed

- `tools/build_dashboard.py` (New CLI tool)
- `tests/test_build_dashboard_2I.py` (New tests)

## Artifacts

- `report/AG-2I-1-1_notes.md` — Heuristics documentation
- `report/AG-2I-1-1_pytest.txt` — Test logs
- `report/AG-2I-1-1_diff.patch` — patch

## Commit

**`d8460bf`** — `2I.1: add static run dashboard builder`
