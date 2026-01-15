# AG-3O-2-2 Return Packet: Corrective Integration & Supervisor Graceful Shutdown

## Summary

Integrated H0.1 housekeeping (cleanup script, policy), untracked ephemeral files from `report/`, and implemented graceful shutdown in `supervisor_live_3E_3H.py` (SIGTERM handling via Popen loop).

## Changes

1. **Housekeeping**:
    * Cherry-picked H0.1 (`f794a4c`).
    * Untracked all ephemeral files in `report/` (snapshots, diffs, temp logs) matching `.gitignore` rules (re-applied standard gitignore logic to index).
    * Added `report/HOUSEKEEPING_report_policy.md` and `tools/cleanup_report.py`.

2. **Supervisor**:
    * Modified `tools/supervisor_live_3E_3H.py`: Replaced blocking `subprocess.run` with `subprocess.Popen` loop in `_default_run`.
    * Logic: Monitors `stop_controller.is_stop_requested`. If detected, forwards signal to child (SIGTERM) or waits for child (SIGINT), ensuring graceful exit (code 0) and checkpoint creation.

3. **Tests**:
    * Maintained `tests/test_graceful_shutdown_signal_3O2.py`.
    * Added `tests/test_graceful_shutdown_supervisor_3O2.py`: Integration test verifying Supervisor terminates child gracefully upon SIGTERM.

4. **CI**:
    * Updated `.github/workflows/graceful_shutdown_3O.yml` to run the new supervisor test.

## Verification

* **Tests**:
  * `pytest tests/test_graceful_shutdown_signal_3O2.py tests/test_graceful_shutdown_supervisor_3O2.py` -> **3 passed** in 23.5s.
  * `pytest` (global) -> **750 passed, 11 skipped**.
* **Compile**: passed.
* **Cleanup**: Index cleaned in commit `3O.2b`.

## Artifacts

* Diff: `report/AG-3O-2-2_diff.patch`
* Commit Log: `report/AG-3O-2-2_last_commit.txt`
* Notes: `report/AG-3O-2-2_notes.md` (Cleanup details)
