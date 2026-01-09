# Bridge Report: Phase 3G to Next (3H)

**From Phase**: 3G (SQLite Idempotency, Observability v0)  
**To Phase**: 3H (Orchestrator Integration / Further Hardening)  
**Date**: 2026-01-09

---

## 1. Current State (End of 3G)

The system now possesses robust "plumbing" for production-like operations:

- **Persistence**: We moved beyond simple files to SQLite (`WAL` mode) for critical idempotency checks.
- **Visibility**: We have a standardized way to emit metrics (`MetricsCollector`) without relying on external TSDBs yet.
- **Safety**: Integrations with external libs (CCXT) are gated and fail-fast.

**Stability**: High. Defaults preserved. New features are opt-in.
**CI**: Enhanced with specific smoke tests for these new capabilities.

---

## 2. Technical Debt / Open Items

| Item | Priority | Description |
| :--- | :--- | :--- |
| **Loop Instrumentation** | Medium | `run_live_3E.py` wires metrics at the *run* level. Ideally, `LoopStepper` should accept a collector to track per-message latency/status inside `run_bus_mode`. |
| **Dashboard** | Low | We have `metrics_summary.json` but no visualization. A simple static HTML dashboard (like 2I) could consume these metrics. |
| **Async SQLite** | Low | Currently tracking thread-safe synchronous SQLite. If throughput demands increase massively (>1000 msg/s), consider `aiosqlite`. |

---

## 3. Recommended Next Steps (Phase 3H)

1. **Orchestrator Control**:
    - Integrate `run_live_3E.py` as a subprocess controlled by a master orchestrator (if planned).
    - Parse `metrics_summary.json` to decide on restarts/alerts.

2. **Strategy Refinement**:
    - Now that infrastructure is robust, revisit `StrategyEngine` (v0.7) to implement more complex logic beyond SMA crossover.

3. **Deployment**:
    - Package the bot for Docker/Kubernetes deployment using the new CLI flags (`--idempotency-backend sqlite`, `--enable-metrics`).

---

## 4. Risks & Mitigations

- **Risk**: SQLite lock contention in high concurrency.
  - *Mitigation*: We track latencies via metrics. `WAL` mode usually handles this well for single-writer scenarios.
- **Risk**: Metric file growth (`metrics.ndjson`).
  - *Mitigation*: Log rotation is not implemented. For long runs, monitor disk usage or implement rotation in `MetricsWriter`.
