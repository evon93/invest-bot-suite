# Bridge Report: Phase 3M to Next Phase

**From:** Phase 3M (Adapter Mode E2E & Resilience)
**To:** Next Phase (3N/3O/4A)
**Date:** 2026-01-14

## 1. State of the System

The `Orchestrator` (`run_live_3E.py`) is now capable of running in two distinct robust modes:

1. **Bus Mode**: Using `DataFrame` bridge (legacy/batch optimized).
2. **Adapter Mode**: Direct event stream consumption (low latency optimized) with full Strategy/Risk/Exec pipeline and crash recovery.

Both modes share the same `ExchangeAdapter` interfaces (Paper/Stub) and `risk_manager` sizing logic.

## 2. What Remains to be Done (Gap Analysis)

### Operational

- **CLI Complexity**: `tools/run_live_3E.py` has many flags. A unified config file approach or simpler aliases would help reliability.
- **Smoke Gating in CI**: Currently smoke tests are manual/local. Adding specific adapter-mode resume scenarios to CI would prevent regression.

### Technical Debt

- **Report Hygiene**: `report/` folder is cluttered.
- **Test Coverage**: While `3M` added targeted tests, edge cases like "resume exactly at bar close" vs "resume mid-bar" (if sub-bar granularity added) need future attention.

## 3. Implementation Suggestions for Next Phase

### A. Report Cleanup (Phase 3O)

- Archive old `report/*` files to `archive/` or delete.
- Enforce gitignore policies strictly.

### B. CI Integration

- Add a job that runs `run_live_3E.py --data-mode adapter ...` then kills it, then resumes, and asserts final state.

### C. Live deployment prep (Phase 4)

- Validate `adapter-mode` with real CCXT generic adapter (read-only first).
- Verify `checkpoint.json` behavior on real system crashes (OOM, SIGKILL).

## 4. Critical Files to Watch

- `engine/loop_stepper.py`: Core logic for both modes.
- `tools/run_live_3E.py`: CLI entry point.
- `engine/checkpoint.py`: Persistence logic.
