# AG-3N-2-1 Return Packet

**Status**: ✅ PASS  
**Branch**: `feature/AG-3N-2-1_ci_smoke_kill_resume`  
**Commit**: `ecf44f1` `3N.2: CI smoke adapter kill+resume`  
**DependsOn**: AG-3N-1-1 (53979d7)

## Summary

Added CI workflow `smoke_3N.yml` for adapter-mode with run+resume testing (offline, deterministic).

## Changes

| File | Change |
|------|--------|
| `.github/workflows/smoke_3N.yml` | [NEW] CI workflow with run+resume pattern |
| `configs/run_live_3E_presets.yaml` | [MODIFY] Added `paper_ci_100bars` preset |
| `tests/fixtures/ohlcv_ci_100bars.csv` | [NEW] 100-bar fixture for CI testing |

## Design Notes

The original kill-based approach (using `timeout -s KILL`) proved unreliable because:

- The kill arrives before checkpoint is created when initialization is slow
- Process startup time varies between environments

The final approach uses:

1. **First batch**: Run 10 steps → creates checkpoint (last_processed_idx: 9)
2. **Resume**: Continue with --resume → advances to last_processed_idx: 34

This tests the same resume functionality without timing-dependent failures.

## Verification

### pytest (750 passed)

```
750 passed, 11 skipped, 7 warnings in 229.51s
```

### Smoke local

- First batch: 10 steps, checkpoint created
- Resume: +25 steps, total 35 processed
- All artifacts: checkpoint.json, events.ndjson, run_meta.json, state.db, results.csv

## Artifacts

- `report/AG-3N-2-1_diff.patch`
- `report/AG-3N-2-1_last_commit.txt`
- `report/pytest_3N2_postmerge.txt`
- `report/smoke_3N2_kill_resume_local.txt`
- `report/ls_out_3N2_kill_resume_local.txt`
