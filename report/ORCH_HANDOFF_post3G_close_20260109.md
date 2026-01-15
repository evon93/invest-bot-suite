# Orchestrator Handoff Report — Phase 3G

**Phase**: 3G (SQLite Idempotency, Observability v0, CI Smoke)  
**Date**: 2026-01-09  
**Branch**: `feature/AG-3G-7-1_closeout` (merged from features)  
**Baseline Commit**: (to be filled in final merge)

---

## 1. Executive Summary

Phase 3G has hardened the execution infrastructure by enhancing persistence, observability, and testing capabilities without modifying the core risk/strategy logic.

**Key Achievements:**

1. **SQLite Idempotency Store**: Robust, ACID-compliant persistence for operation keys using WAL mode. Replaces/augments the file-based JSONL store.
2. **Observability v0**: Real-time metrics collection (latency, counters, breakdown by reason) with file-first persistence (`metrics.ndjson`, `metrics_summary.json`).
3. **CCXT Sandbox Integration**: A "gated" adapter that safely handles CCXT dependencies (fail-fast if missing) and enables idempotent interaction with exchanges.
4. **CI 3G Smoke Gate**: Dedicated GitHub Actions workflow to verify the new runner capabilities (metrics, SQLite wiring) in a clean environment.

---

## 2. Delivered Features

| Ticket | Feature | Description | Key Artifacts |
| :--- | :--- | :--- | :--- |
| **3G.1** | `CcxtSandboxAdapter` | CCXT integration with lazy loading, error classification, and fail-fast validation. | `engine/ccxt_sandbox_adapter.py` |
| **3G.2** | `SQLiteIdempotencyStore` | SQLite implementation with concurrent access (`WAL`, `INSERT OR IGNORE`). Wiring via `--idempotency-backend`. | `engine/idempotency.py` `tools/run_live_3E.py` |
| **3G.3** | `MetricsCollector` | Instrumentación real-time (start/end) y persistencia file-first. Wiring via `--enable-metrics`. | `engine/metrics_collector.py` `metrics_summary.json` |
| **3G.4** | CI Smoke Gate 3G | Workflow automatizado para validar el runner live con metricas activadas. | `.github/workflows/smoke_3G.yml` |

---

## 3. Usage & Verification

### SQLite Idempotency

To use SQLite instead of the default JSONL file:

```bash
python tools/run_live_3E.py --run-dir /tmp/run_sqlite --idempotency-backend sqlite
```

*Creates `/tmp/run_sqlite/idempotency.db`*

### Observability Metrics

To enable metrics collection:

```bash
python tools/run_live_3E.py --run-dir /tmp/run_metrics --enable-metrics
```

*Creates `/tmp/run_metrics/metrics_summary.json` and `metrics.ndjson`*

### CI Verification

The new features are verified by `.github/workflows/smoke_3G.yml`, which runs a simplified live simulation with metrics enabled to ensure artifacts are generated correctly.

---

## 4. Known Limitations

- **Instrumentación Granular**: The current loop wiring tracks run-level metrics. Per-message instrumentation requires deeper changes in `LoopStepper` (deferred to future phases).
- **Default Behavior**: The runner defaults to `idempotency-backend=file` and metrics **disabled** to maintain backward compatibility.
- **CCXT Dependency**: The adapter is present but `ccxt` package is optional; functionality degrades gracefully if likely missing.

---

## 5. Artifacts Checklist

- [x] `engine/idempotency.py` (SQLiteStore)
- [x] `engine/metrics_collector.py` (Observability)
- [x] `.github/workflows/smoke_3G.yml` (CI)
- [x] `tests/test_idempotency_store_sqlite.py`
- [x] `tests/test_metrics_collector_v0.py`
- [x] `tests/test_run_live_metrics_wiring.py`
