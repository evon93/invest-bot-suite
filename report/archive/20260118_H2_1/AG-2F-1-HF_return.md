# AG-2F-1-HF Return Packet — Restore load_ohlcv API

## Result

✅ API restored with backward compatibility.

## Design Decision

**Option A** implemented:

- `load_ohlcv(path, *, return_stats=False)` → `DataFrame` by default
- `load_ohlcv(path, return_stats=True)` → `(DataFrame, LoadStats)` tuple
- CLI uses `return_stats=True` internally

## API Example

```python
# Default (backward compatible)
df = load_ohlcv("data.csv")

# With stats
df, stats = load_ohlcv("data.csv", return_stats=True)
```

## Tests

- 158 passed, 2 skipped
- Test `test_load_csv_basic` verifies both modes

## Commit

**`729b2a5`** — `2F.1H: restore load_ohlcv API (stats optional)`
