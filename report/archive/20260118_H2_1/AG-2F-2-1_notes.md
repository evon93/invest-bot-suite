# AG-2F-2-1 Design Notes

## Decisions

### Max Rows

- Default: 2000 rows (tail)
- Rationale: Fast execution (~2s), enough for meaningful metrics
- Configurable via `--max-rows`

### Metrics Computed

- `total_return`: (final / initial) - 1
- `cagr`: Annualized return based on date range
- `max_drawdown`: Peak-to-trough drop
- `sharpe`: Daily returns annualized (sqrt(252))

### Marker Config

- Added `realdata` marker to `pytest.ini`
- Prevents "unknown marker" warnings in strict mode

### Skip Behavior

- Uses `pytest.skip()` in fixture, not `skipif` decorator
- Allows dynamic check of file existence
- Clean skip message in test output

### Runner vs Test

- Chose Option A (separate runner tool)
- Benefits: reusable CLI, testable via subprocess, clear separation
- Test validates runner outputs, not just import
