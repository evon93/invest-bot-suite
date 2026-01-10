# Bridge Report: Phase 3H → Next Phase

**Date:** 2026-01-10  
**From:** Phase 3H (Live Loop Observability & Supervision)  
**To:** Phase 3I (TBD)

---

## Phase 3H Summary

Phase 3H delivered comprehensive observability and supervision capabilities:

1. **Granular Metrics**: Per-stage latency and outcome tracking
2. **Rotation**: Controlled log rotation for 24/7 runs
3. **Dashboard**: File-first HTML visualization
4. **Supervisor**: Automatic restart with deterministic backoff
5. **CI**: smoke_3H workflow for end-to-end validation

---

## Recommended Next Steps (Phase 3I)

### Priority 1: Time Provider Enhancement

**Problem:** In simulated mode, `time_provider.now_ns()` returns fixed value, causing stage latencies to show as 0.0ms.

**Proposal:** Add monotonic clock simulation that advances based on simulated processing time.

**Impact:** Would enable meaningful latency analysis in backtests.

---

### Priority 2: Supervisor Signal Handling

**Problem:** Current supervisor doesn't handle SIGTERM/SIGINT gracefully.

**Proposal:** Add signal handlers for:

- SIGTERM: Graceful shutdown (wait for child, then exit)
- SIGINT: Same as SIGTERM
- SIGHUP: Reload config (future)

**Impact:** Production-ready supervisor behavior.

---

### Priority 3: Dashboard Enhancements

**Proposals:**

- Add timestamp of generation to dashboard
- Support filtering by date range
- Add charts (sparklines) for key metrics
- Consider optional refresh (file watching)

---

### Priority 4: Metrics Compaction

**Problem:** Rotated files accumulate indefinitely.

**Proposal:** Add optional cleanup of old rotated files:

```
--metrics-rotate-keep <int>  # Keep only N rotated files
```

---

## Technical Debt

| Item | Severity | Description |
|------|----------|-------------|
| Latencies 0.0 in simulated | Low | Expected behavior, documented |
| No signal handling in supervisor | Medium | Manual kill required for graceful stop |
| Dashboard is static | Low | Acceptable for file-first approach |
| No log compaction | Low | Disk usage grows indefinitely with rotation |

---

## Open Risks

| Risk | Mitigation |
|------|------------|
| Supervisor can't recover from corrupted state | State is overwritten each iteration; worst case is restart from 0 |
| Dashboard doesn't show live data | Design decision; use tail -f for live monitoring |
| Rotation check interval may miss exact threshold | Acceptable; threshold is eventually enforced |

---

## Files for Next Phase Reference

| Component | Files |
|-----------|-------|
| Metrics Collector | `engine/metrics_collector.py` |
| Dashboard | `tools/render_metrics_dashboard_3H.py` |
| Supervisor | `tools/supervisor_live_3E_3H.py` |
| CI | `.github/workflows/smoke_3H.yml` |
| Tests | `tests/test_loop_stepper_metrics_granular.py`, `test_metrics_rotation.py`, `test_metrics_dashboard_render.py`, `test_supervisor_3H.py` |

---

## Conclusion

Phase 3H is complete. The live loop now has:

- Full observability of each processing stage
- Controlled log management for 24/7 operation
- Visual inspection capability via dashboard
- Automatic recovery from crashes via supervisor
- CI validation of all components

Ready for Phase 3I when prioritized.
