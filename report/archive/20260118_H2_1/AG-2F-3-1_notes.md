# AG-2F-3-1 Design Notes

## Schema for Date Slicing

Used existing fields in config:

- `baseline.dataset.start_date`
- `baseline.dataset.end_date`

Applied as DataFrame filters after loading realdata:

```python
if start_date:
    realdata_prices = realdata_prices[realdata_prices["date"] >= start_date]
if end_date:
    realdata_prices = realdata_prices[realdata_prices["date"] <= end_date]
```

## Path Resolution Order

1. `realdata.path` in config (explicit)
2. `INVESTBOT_REALDATA_PATH` env var (fallback)
3. Error with clear message if neither available

## Relative Path Handling

Relative paths resolved against REPO_ROOT:

```python
if not realdata_path.is_absolute():
    realdata_path = REPO_ROOT / realdata_path
```

## run_meta.json Fields (realdata mode)

Added fields when data_source="realdata":

- `data_source: "realdata"`
- `realdata_path: "/absolute/path/to/file.csv"`
- `n_rows: 100`
- `start_date: "2024-01-01 00:00:00"`
- `end_date: "2024-04-10 00:00:00"`

## Backward Compatibility

- Missing `data_source` defaults to "synthetic"
- All existing configs continue to work unchanged
- run_meta.json shows `data_source: "synthetic"` for synthetic runs
