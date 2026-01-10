# Orchestrator Handoff Report - Phase 3H Closure

**Date:** 2026-01-10  
**Phase:** 3H - Live Loop Observability & Supervision  
**Status:** ✅ COMPLETED

---

## Executive Summary

Phase 3H implemented granular observability for the live trading loop, including per-stage metrics collection, log rotation, HTML dashboard rendering, and a 24/7 process supervisor. All features maintain determinism for simulated runs and require no external dependencies.

---

## Deliverables

### 1. Granular Metrics (AG-3H-1-1) - `ccbb2e8`

**What:** Per-step/per-stage metrics collection in the trading loop.

**Files Modified:**

- `engine/metrics_collector.py`: Added `record_stage()`, `get_stage_events()`, `stages_by_name`, `outcomes_by_stage`
- `engine/loop_stepper.py`: Instrumented `run_bus_mode()` for strategy/risk/exec/position stages
- `tools/run_live_3E.py`: Wired `metrics_collector` to stepper

**New Metrics:**

- `stages_by_name`: count, p50_ms, p95_ms per stage
- `outcomes_by_stage`: ok/rejected/error counters per stage
- `stage_events_count`: total stage events

**Output Files:**

- `metrics.ndjson`: NDJSON stream of stage events
- `metrics_summary.json`: Aggregated summary (includes stage metrics)

---

### 2. Metrics Rotation (AG-3H-2-1) - `ec6db3a`

**What:** Controlled rotation of `metrics.ndjson` for 24/7 runs.

**New CLI Flags:**

```
--metrics-rotate-max-mb <int>    # Max MB before rotation
--metrics-rotate-max-lines <int> # Max lines before rotation
```

**Behavior:**

- Disabled by default (backward compatible)
- Atomic rotation: close → rename to `.N` → reopen
- Files named: `metrics.ndjson.1`, `.2`, `.3`, ...
- Check interval: every 100 writes (or every write if max_lines < 100)

**Note:** `metrics_summary.json` reflects total since process start (not reset by rotation).

---

### 3. Metrics Dashboard (AG-3H-3-1) - `cdc4e88`

**What:** Self-contained HTML dashboard for metrics visualization.

**Script:** `tools/render_metrics_dashboard_3H.py`

**CLI:**

```bash
python tools/render_metrics_dashboard_3H.py \
  --run-dir <path> \
  --out <file> \
  --tail-lines <int>
```

**Sections:**

- Overview (processed, filled, rejected, errors)
- Latency (P50, P95)
- Stages table (count, latencies, outcomes)
- Errors & Rejections by reason
- Recent Events (tail of NDJSON)

**Features:**

- No external dependencies
- CSS inline (self-contained)
- Reads rotated files in chronological order
- HTML escaping for XSS prevention

---

### 4. Process Supervisor (AG-3H-4-1) - `3e3a9ab`

**What:** 24/7 supervisor wrapper with automatic restart and backoff.

**Script:** `tools/supervisor_live_3E_3H.py`

**CLI:**

```bash
python tools/supervisor_live_3E_3H.py \
  --run-dir <path> \
  --max-restarts <int> \
  --backoff-base-s <float> \
  --backoff-cap-s <float> \
  -- python tools/run_live_3E.py <args>
```

**Backoff Formula:**

```
delay = min(cap, base * 2^attempt)  # No jitter (deterministic)
```

**Outputs:**

- `supervisor_state.json`: Persistent state (attempt, exit code, delay, cmdline)
- `supervisor.log`: Append-only log

---

### 5. CI Smoke Test (AG-3H-6-1) - `520fffe`

**Workflow:** `.github/workflows/smoke_3H.yml`

**Steps:**

1. pytest -q
2. run_live_3E with `--enable-metrics --metrics-rotate-max-lines 5`
3. render_metrics_dashboard_3H
4. Verify artifacts exist
5. Upload artifacts

---

## Local Execution Examples

### Run with Metrics + Rotation

```bash
python tools/run_live_3E.py \
  --run-dir report/my_run \
  --clock simulated \
  --exchange paper \
  --seed 42 \
  --enable-metrics \
  --metrics-rotate-max-lines 100 \
  --max-steps 50
```

### Render Dashboard

```bash
python tools/render_metrics_dashboard_3H.py \
  --run-dir report/my_run \
  --out report/my_run/dashboard.html
```

### Run with Supervisor

```bash
python tools/supervisor_live_3E_3H.py \
  --run-dir report/supervised_run \
  --max-restarts 100 \
  --backoff-base-s 1.0 \
  --backoff-cap-s 60 \
  -- python tools/run_live_3E.py --max-steps 1000 --enable-metrics
```

---

## Expected Artifacts (run_dir)

| File | Description |
|------|-------------|
| `metrics.ndjson` | Current stage events |
| `metrics.ndjson.1`, `.2`, ... | Rotated files (if rotation enabled) |
| `metrics_summary.json` | Aggregated metrics |
| `dashboard.html` | HTML dashboard (if rendered) |
| `supervisor_state.json` | Supervisor state (if using supervisor) |
| `supervisor.log` | Supervisor log (if using supervisor) |

---

## Known Limitations

1. **Latencies are 0.0 in simulated mode**: The `time_provider` doesn't advance between calls in simulated mode, so stage latencies show as 0.0ms. Real latencies only appear with `--clock real`.

2. **Rotation disabled by default**: For backward compatibility, rotation only activates when `--metrics-rotate-max-mb` or `--metrics-rotate-max-lines` is specified.

3. **Supervisor is not a system daemon**: The supervisor is a Python script, not a systemd service. For production, consider wrapping with systemd or similar.

4. **Dashboard is static**: The dashboard is a one-time render, not a live-updating UI.

---

## Verification

```bash
# Run tests
python -m pytest -q

# Smoke test with all 3H features
python tools/run_live_3E.py --run-dir /tmp/test3h --enable-metrics --metrics-rotate-max-lines 5 --max-steps 20 --clock simulated --exchange paper --seed 42
python tools/render_metrics_dashboard_3H.py --run-dir /tmp/test3h

# Check outputs
ls /tmp/test3h/
```

---

## Commits Summary

| Ticket | Commit | Description |
|--------|--------|-------------|
| AG-3H-1-1 | `ccbb2e8` | Granular metrics per-step/per-stage |
| AG-3H-2-1 | `ec6db3a` | Metrics rotation |
| AG-3H-3-1 | `cdc4e88` | HTML dashboard |
| AG-3H-4-1 | `3e3a9ab` | 24/7 supervisor |
| AG-3H-6-1 | `520fffe` | CI smoke_3H workflow |

---

## Next Phase Recommendation

See `bridge_3H_to_next_report.md` for Phase 3I proposals.
