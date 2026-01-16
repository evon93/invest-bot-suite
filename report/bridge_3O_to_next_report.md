# Bridge Report: Phase 3O → Next

**Date:** 2026-01-15
**Source Phase:** 3O (Graceful Shutdown & Report Hygiene)
**Target Phase:** H1 / 4.x (Policy Refinement / Live Integration)

## 1. Current State

Phase 3O is complete. The system now supports:

- **Graceful Shutdown**: SIGINT/SIGTERM → clean exit (0), checkpoint saved.
- **Supervisor Resilience**: Child process restart with deterministic backoff; signals forwarded.
- **Report Hygiene**: Cleanup script and `.gitignore` policy for ephemeral artifacts.

**Branch**: `main` (post PR #33)
**Verification**: 750+ tests passed; CI 12/12 green.

## 2. Technical Debt

| Item | Description | Priority |
|------|-------------|----------|
| Exit Code Semantics | Non-signal failures (e.g., config error) may exit 0 if handler is set. Should distinguish controlled shutdown vs. failure. | Medium |
| Artifact Bloat | `report/` contains many historical artifacts (patches, runs). Consider compression or CI artifact upload. | Low |
| Windows SIGTERM | Supervisor SIGTERM test skips on Windows (hard kill semantics). | Low |

## 3. Recommended Next Steps (H1 / Phase 4)

### H1.1: Artifact Storage Policy

- **Goal**: Define a policy for heavy artifacts (patches, run outputs).
- **Options**:
  - Compress older artifacts (`.tar.gz` or `.zip`).
  - Upload to CI artifacts instead of tracking in git.
  - Generate digest summaries instead of full logs.

### H1.2: Exit Code Refinement

- **Goal**: Ensure `run_live_3E.py` exits non-zero for non-signal failures.
- **Test**: Add `test_failure_must_be_nonzero` that causes a config error and asserts `exit_code != 0`.
- **Implementation**: Wrap main logic in try/except; only exit 0 if `stop_controller.is_stop_requested`.

### H1.3: Adapter-Mode SIGTERM (Optional)

- **Goal**: Verify that adapter-mode also exits cleanly on SIGTERM.
- **Checklist**:
  - [ ] `run_adapter_mode` tested with SIGTERM.
  - [ ] Checkpoint saved mid-stream.
  - [ ] Resume produces same trades.

### Phase 4: Live Integration

- **Goal**: Connect to real exchange (CCXT) with network gating.
- **Prerequisite**: Ensure graceful shutdown works with network I/O (timeouts, retries).

## 4. Handoff Artifacts

- `report/ORCH_HANDOFF_post3O_close_20260115.md`
- `report/bridge_3O_to_next_report.md` (this file)
- `report/AG-3O-4-1_return.md` (closeout return packet)

## 5. Verification Command

```bash
pytest -q tests/test_graceful_shutdown_signal_3O2.py tests/test_graceful_shutdown_supervisor_3O2.py
```
