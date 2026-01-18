# AG-2F-1-H Design Notes

## Decisions

### Date Range Validation

- Valid range: 1990-2100
- Rationale: Most financial data starts after 1990, 2100 is far enough for future data

### Timezone Policy

- All dates converted to naive (no timezone)
- Epoch timestamps parsed as UTC, then tz stripped
- Wall time preserved (not converted)

### Epoch Detection Threshold

- `>1e12` → milliseconds
- `<=1e12` → seconds
- Based on: 1e12 seconds ≈ year 33,000 (clearly invalid)
- 1e12 milliseconds ≈ year 2001 (reasonable)

### Encoding Default

- Default: "utf-8"
- Rationale: Most modern data sources use UTF-8
- User can override via parameter or CLI flag

### NaN Handling Priority

1. Drop NaT dates first (before OHLC check)
2. Drop OHLC NaN rows (can't calculate indicators)
3. Fill volume NaN with 0 (acceptable for missing volume)

### Return Value Change

- Changed from `df` to `(df, stats)`
- Breaking change for callers
- Rationale: Stats are important for data quality visibility
