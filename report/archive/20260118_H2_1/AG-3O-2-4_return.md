# AG-3O-2-4 Return Packet: Fix SIGTERM Race (CI Smoke)

## Context

CI failure observed in `smoke-3g`: shutdown test exited with `-15` (SIGTERM killed) instead of `0`.
Inferred Cause: Race condition where SIGTERM arrives during setup phases (before loop), and default Python handler causes termination because the custom handler exception/interrupt logic was swallowed or not yet fully effective in blocking operations.

## Changes

1. **Robust Signal Handler (`tools/run_live_3E.py`)**:
    * Wrapped handler logic in `try...except` to prevent crashes (e.g. `BrokenPipeError` on print) which could trigger default termination.
2. **Early Exit Checks (`tools/run_live_3E.py`)**:
    * Added explicit `if stop_controller.is_stop_requested: sys.exit(0)` checks:
        * Immediately after argument parsing.
        * Before potentially slow loop initialization.
        * Before entering the main execution loop (`stepper.run_...`).
3. **LoopStepper Guard (`engine/loop_stepper.py`)**:
    * Added check at the very beginning of `run_bus_mode` and `run_adapter_mode`.
    * If stop is requested before processing starts, returns status `"stopped_early"` immediately.

## Verification

* **Local Reproduction**: `pytest tests/test_graceful_shutdown_signal_3O2.py` passed locally (exit 0) both before and after fix.
* **Fix Verification**: Re-ran tests, confirming no regression (`2 passed in 15.00s`).
* **Logic**: The added checks minimize the window where a signal is handled (flag set) but execution continues into a blocking state or timeout.

## Artifacts

* Diff: `report/AG-3O-2-4_diff.patch`
* Commit: `report/AG-3O-2-4_last_commit.txt`
* Evidence: `report/pytest_3O2_smoke3g_fix.txt`
