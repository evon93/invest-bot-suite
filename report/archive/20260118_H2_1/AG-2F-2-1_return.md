# AG-2F-2-1 Return Packet — RealData Smoke Test

## Result

✅ Optional realdata smoke test implemented.

## Files Created

| File | Lines | Description |
|------|-------|-------------|
| `tools/run_realdata_smoke_2F.py` | 175 | Minimal runner with buy-and-hold metrics |
| `tests/test_realdata_smoke_2F.py` | 130 | 4 tests with @pytest.mark.realdata |
| `pytest.ini` | +2 | Registered realdata marker |

## Behavior

- **Without env var**: Tests skip gracefully
- **With env var**: Tests run and validate outputs

```bash
# Without env var (CI default)
pytest -q  # 158 passed, 6 skipped

# With env var (local)
set INVESTBOT_REALDATA_PATH=data/btc_daily.csv
pytest -q -m realdata  # 4 passed
```

## Outputs

When run, the smoke test produces:

- `<outdir>/results.json` — metrics (total_return, cagr, max_drawdown, sharpe)
- `<outdir>/run_meta.json` — metadata with `data_source: "realdata"`

## Tests

- 158 passed, 6 skipped (4 realdata + 2 parquet)

## Commit

**`a5e3bb8`** — `2F.2: add optional realdata smoke test`
