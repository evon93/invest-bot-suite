# Bridge Report: Phase 3I to Next Phase

**From:** Phase 3I (TimeSignalsRetention)
**To:** Next Phase (Orchestration/Strategy/Validation)
**Date:** 2026-01-11

## 1. Technical Debt & Observations

These items were identified during Phase 3I development and DeepSeek audits but were out of scope for immediate resolution.

### 1.1. Metrics Collector

- **Thread Safety:** The current `MetricsWriter` is designed for the existing single-threaded (or GIL-bound) asyncio/sync architecture. DeepSeek audit noted that purely concurrent threaded usage might require explicit locking.
- **Error Logging:** `_cleanup_rotated` suppresses `OSError` without logging.
- **Configurable Retention:** Current `metrics-rotate-keep` is count-based. Size-based retention (total MB) or time-based (age) is not implemented.

### 1.2. Dashboard

- **UX:** The auto-refresh is a full page reload.
- **History:** No historical comparison between runs yet.

## 2. Backlog Recommendations (External Audit Inputs)

Based on DeepSeek audits (AG-3I-1-2-DS, AG-3I-3-1-DS):

| Priority | Component | Item | Rationale |
|----------|-----------|------|-----------|
| P3 | Engine | **Batch Latency Config** | Allow configurable latencies per stage (currently constants) via `runtime_config`. |
| P3 | Metrics | **Per-item Trace IDs** | Log trace IDs for *every* item in a batch if debugging granularity is insufficient. |
| P4 | Metrics | **Retention by Size** | Add `--metrics-rotate-max-total-mb` to bound disk usage strictly by size, not just file count. |
| P4 | Dashboard | **Countdown Timer** | Add JS countdown visual for the auto-refresh to improve UX. |

## 3. Transition Checklist

- [ ] Merge `feature/AG-3I-7-1_closeout` to `main`.
- [ ] Ensure `smoke_3I.yml` runs successfully on main.
- [ ] Review `registro_de_estado_invest_bot.md` for complete history.

## 4. Next Phase Focus

With the core "Live Runner" infrastructure (Time, Signals, Metrics, Supervisor, Dashboard) now robust:

- **Strategy Implementation:** Move from dummy `StrategyV0_7` to real alpha logic.
- **Execution Adapters:** Implement/harden `Realish` adapter or generic CCXT connector integration.
