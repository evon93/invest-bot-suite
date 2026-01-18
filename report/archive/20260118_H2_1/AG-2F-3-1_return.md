# AG-2F-3-1 Return Packet — Wire Realdata into Robustness Runner

## Result

✅ Realdata source wired into robustness runner with backward compat.

## Implementation

### Config Schema (new optional keys)

```yaml
data_source: realdata  # or synthetic (default)
realdata:
  path: "data/btc_daily.csv"  # or use INVESTBOT_REALDATA_PATH env
```

### Changes to run_robustness_2D.py

1. **data_source resolution**: Defaults to "synthetic" if missing
2. **realdata loading**: Uses `load_ohlcv()` from tools module
3. **Date filtering**: Applies baseline.dataset.start_date/end_date if present
4. **run_meta.json update**: Includes data_source, realdata_path, n_rows, start/end

### Backward Compatibility

- Existing configs (no data_source) continue to work with synthetic data
- No breaking changes to CLI or API

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `tools/run_robustness_2D.py` | +68 | data_source parsing, realdata loading, meta update |
| `tests/test_runner_realdata_wiring_2F3.py` | +213 | 3 new tests |

## Tests

- 161 passed, 6 skipped

## Commit

**`a97b3da`** — `2F.3: wire realdata source into robustness runner`
