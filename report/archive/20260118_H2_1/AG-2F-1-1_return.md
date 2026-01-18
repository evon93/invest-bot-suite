# AG-2F-1-1 Return Packet — Local OHLCV Loader

## Result

✅ `load_ohlcv.py` implemented with CSV/Parquet support + CLI + 10 tests.

## Features

- **Column normalization**: date/timestamp/time → date; o/open → open; etc.
- **Timezone**: naive (no tz)
- **Dtypes**: date=datetime64[ns], OHLCV=float64
- **Sorting**: ascending by date
- **Deduplication**: drop duplicates, keep last

## Files Created

| File | Lines | Description |
|------|-------|-------------|
| `tools/load_ohlcv.py` | 215 | OHLCV loader with CLI |
| `tests/test_load_ohlcv.py` | 223 | Test suite (10 tests) |

## CLI Usage

```bash
python tools/load_ohlcv.py --path data/btc_ohlcv.csv
```

## Tests

- 150 passed, 2 skipped (parquet engine not available)
- 10 new tests for OHLCV loader

## Commit

**`e8c7793`** — `2F.1: add local OHLCV loader + tests`

## Notes

- Parquet support: requires pyarrow/fastparquet (not in deps)
- Windows encoding: tests use PYTHONIOENCODING=utf-8 for subprocess
