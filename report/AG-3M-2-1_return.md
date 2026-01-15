# AG-3M-2-1 Return Packet

## Ticket Summary

- **ID**: AG-3M-2-1
- **Parent**: AG-3M-1-1 merged (HEAD c957bc3)
- **Status**: ✅ PASS

## Changes Made

### `engine/loop_stepper.py`

- Added parameters `checkpoint`, `checkpoint_path`, `start_idx` to `run_adapter_mode()`
- Added resume logic: skip warmup + already-processed events when `start_idx > 0`
- Added checkpoint save after each step: `checkpoint.update(idx).save_atomic(path)`

### `tools/run_live_3E.py`

- Modified to pass `checkpoint`, `checkpoint_path`, `start_idx` to `run_adapter_mode()` when `--data-mode adapter`

### New Tests

- `tests/test_adapter_mode_resume_idempotent_3M2.py` (3 tests)
- `tests/test_adapter_mode_checkpoint_state_3M2.py` (4 tests)

## Verification Results

### pytest -q

```
729 passed, 11 skipped, 7 warnings in 43.68s
```

### Tests específicos 3M2

```
7 passed in 0.86s
```

### Smoke test first_run + resume

**First run (5 steps):**

```bash
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --data-mode adapter --exchange paper --clock simulated --seed 42 --max-steps 5 \
  --run-dir report/out_3M2_smoke/first_run
```

- Created checkpoint.json: `last_processed_idx=4, processed_count=5`

**Resume run (5 more steps):**

```bash
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --data-mode adapter --exchange paper --clock simulated --seed 42 --max-steps 5 \
  --resume report/out_3M2_smoke/first_run --outdir report/out_3M2_smoke/resume_run
```

- Resumed from index 5
- Generated artifacts in resume_run/

## How to Test

```bash
# Run specific 3M2 tests
python -m pytest tests/test_adapter_mode_resume_idempotent_3M2.py tests/test_adapter_mode_checkpoint_state_3M2.py -v

# Run full suite
python -m pytest -q

# Smoke test: first run
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --data-mode adapter --exchange paper --clock simulated --seed 42 --max-steps 5 \
  --run-dir report/out_3M2_smoke/first_run

# Smoke test: resume
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --data-mode adapter --exchange paper --clock simulated --seed 42 --max-steps 5 \
  --resume report/out_3M2_smoke/first_run --outdir report/out_3M2_smoke/resume_run
```

## Design Notes

1. **Resume Skip Logic**: On resume, warmup + start_idx events are consumed to rebuild_ohlcv_rows slice
2. **Checkpoint Index**: Uses `start_idx + step_count - 1` to correctly track absolute index across runs
3. **Idempotency**: No duplicate events/fills - resume continues from where previous run stopped
4. **No-Lookahead Preserved**: Guard assertion maintained in all code paths

## AUDIT_SUMMARY

- **Files Modified**:
  - `engine/loop_stepper.py` (added checkpoint params, resume logic, checkpoint save)
  - `tools/run_live_3E.py` (pass checkpoint params to run_adapter_mode)
- **Files Created**:
  - `tests/test_adapter_mode_resume_idempotent_3M2.py`
  - `tests/test_adapter_mode_checkpoint_state_3M2.py`
- **Risks**: None identified - backwards compatible, all tests pass
