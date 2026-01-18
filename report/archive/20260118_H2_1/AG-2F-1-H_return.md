# AG-2F-1-H Return Packet — Hardened OHLCV Loader

## Result

✅ H1 + H2 + H3 implemented and tested.

## Implementation Summary

### H1: NaT/NaN Policy

- Drop rows with NaT dates (`stats.dropped_nat_date`)
- Drop rows with NaN in OHLC columns (`stats.dropped_ohlc_nan`)
- Fill volume NaN with 0.0 (`stats.volume_filled_zero`)

### H2: Epoch s/ms Parsing

- Detect numeric timestamps in date column
- Infer unit: `>1e12` → ms, else → s
- Validate date range [1990-2100]
- `stats.epoch_unit_used` reports detected unit

### H3: Encoding Parameter

- `load_ohlcv(path, encoding="utf-8")`
- CLI: `--encoding` flag

## Files Changed

| File | Lines | Change |
|------|-------|--------|
| `tools/load_ohlcv.py` | 305 | Rewritten with LoadStats, epoch detection, NaN policy |
| `tests/test_load_ohlcv.py` | 341 | 8 new tests for H1/H2/H3 |

## New Tests

| Test | Purpose |
|------|---------|
| `test_drop_nat_date_rows` | H1.1 |
| `test_drop_ohlc_nan_rows` | H1.2 |
| `test_volume_nan_filled_to_zero` | H1.3 |
| `test_epoch_seconds_parsing` | H2 |
| `test_epoch_milliseconds_parsing` | H2 |
| `test_epoch_out_of_range_raises` | H2 |
| `test_cli_accepts_encoding_flag` | H3 |
| `test_cli_shows_cleaning_stats` | CLI verification |

## Tests

- 158 passed, 2 skipped

## Commit

**`4ea818f`** — `2F.1H: harden OHLCV loader (NaT/NaN policy + epoch s/ms + encoding)`
