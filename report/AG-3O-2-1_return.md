# AG-3O-2-1 Return Packet: Graceful Shutdown Signals

## Summary

Implemented graceful shutdown handling for `SIGINT` (Ctrl+C) and `SIGTERM` in `run_live_3E.py`. The system now detects these signals, requests a stop via `StopController`, and cleanly drains the execution loop in `LoopStepper`, saving a checkpoint before exiting with code 0.

## Changes

1. **`tools/run_live_3E.py`**:
    * Added `StopController` and `install_signal_handlers`.
    * Updated `main()` to wire `stop_controller` to signal handlers and execution logic.
    * Fixed accidental deletion of `argparse` definitions (restored `--preset` and `--config`).

2. **`engine/loop_stepper.py`**:
    * Updated `run_bus_mode` and `run_adapter_mode` to accept `stop_controller`.
    * Added periodic check `if stop_controller.is_stop_requested:` inside processing loops.
    * Logs shutdown reason and breaks loop cleanly.

3. **Tests**:
    * Created `tests/test_graceful_shutdown_signal_3O2.py`: Integration test using subprocess to verify clean exit code 0 and checkpoint creation upon SIGINT/SIGTERM.
    * Passes offline.

4. **CI**:
    * Created `.github/workflows/graceful_shutdown_3O.yml` to run the integration test in offline mode and upload artifacts.

## Verification

* **Command**: `python -m pytest tests/test_graceful_shutdown_signal_3O2.py -v`
* **Result**: 2 passed in ~16s.
* **Manual**: Verified `run_live_3E.py` argument parsing works after restore.

## Audit Summary

* **Files Modified**: `tools/run_live_3E.py`, `engine/loop_stepper.py`.
* **Risks**: Low. The shutdown logic is additive/optional (defaults to None in `LoopStepper`).
* **Notes**:
  * Fixed a syntax error (duplicate argument) in `loop_stepper.py` during implementation.
  * Restored missing CLI args in `run_live_3E.py`.

## Artifacts

* Diff: `report/AG-3O-2-1_diff.patch`
* Commit Log: `report/AG-3O-2-1_last_commit.txt`
