# AG-3M-1-1 Return Packet

## Ticket Summary

- **ID**: AG-3M-1-1
- **Parent**: baseline main@e758802 (3M.0 PASS)
- **Status**: ✅ PASS

## Changes Made

### `engine/loop_stepper.py`

- Added parameter `exchange_adapter` to `run_adapter_mode()`
- Added `_step_with_adapter()` private method for end-to-end wiring:
  - MarketDataAdapter → Strategy → Risk → Exec (ExchangeAdapter paper/stub) → PositionStore
- Maintains no-lookahead guard (`event.ts <= current_step_ts`)

### `tools/run_live_3E.py`

- Modified to pass `exchange_adapter` to `run_adapter_mode()` when `--data-mode adapter`
- No new CLI flags needed (existing `--exchange paper|stub` reused)

### New Tests

- `tests/test_adapter_mode_end_to_end_paper_3M1.py` (6 tests)
- `tests/test_adapter_mode_no_lookahead_3M1.py` (5 tests)

## Verification Results

### pytest -q

```
722 passed, 11 skipped, 7 warnings in 44.54s
```

### Tests específicos 3M1

```
11 passed in 0.72s
```

### Smoke test offline

```bash
python tools/run_live_3E.py \
  --data fixture \
  --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --data-mode adapter \
  --exchange paper \
  --clock simulated \
  --seed 42 \
  --max-steps 10 \
  --outdir report/out_3M1_smoke
```

Artifacts generated:

- `report/out_3M1_smoke/events.ndjson`
- `report/out_3M1_smoke/run_meta.json`
- `report/out_3M1_smoke/run_metrics.json`
- `report/out_3M1_smoke/smoke_cmd.txt`
- `report/out_3M1_smoke/smoke_log.txt`

## How to Test

```bash
# Run specific 3M1 tests
python -m pytest tests/test_adapter_mode_end_to_end_paper_3M1.py tests/test_adapter_mode_no_lookahead_3M1.py -v

# Run full suite
python -m pytest -q

# Smoke test
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv --data-mode adapter --exchange paper --clock simulated --seed 42 --max-steps 10 --outdir report/out_3M1_smoke
```

## Design Notes

1. **Backwards Compatible**: Without `exchange_adapter`, `run_adapter_mode()` uses original `step()` behavior
2. **Reused Existing Adapters**: PaperExchangeAdapter and StubNetworkExchangeAdapter work without modification
3. **No-Lookahead Preserved**: Guard assertion maintained in all code paths

## AUDIT_SUMMARY

- **Files Modified**:
  - `engine/loop_stepper.py` (added `_step_with_adapter()`, modified `run_adapter_mode()`)
  - `tools/run_live_3E.py` (pass exchange_adapter to run_adapter_mode)
- **Files Created**:
  - `tests/test_adapter_mode_end_to_end_paper_3M1.py`
  - `tests/test_adapter_mode_no_lookahead_3M1.py`
- **Risks**: None identified - backwards compatible, all tests pass
