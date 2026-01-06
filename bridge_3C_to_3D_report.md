# Bridge Report: 3C -> 3D

**From:** Phase 3C (Event Loop & Hardening)
**To:** Phase 3D (Live Integration & Bus)

## Context

Phase 3C built the hardened "engine room": a deterministic loop that steps through bars, invokes strategy, checks risk, simulates execution, and updates state. It proved that the **contracts (V1)** and **state management (SQLite)** are robust enough for production-like simulations.

## 3D Objectives (Preview)

Phase 3D will likely focus on **unbinding** the components into a loosely coupled system (or preparing for it) and conducting "live" tests on real market data (paper trading).

## Technical Debt & Recommendations from 3C

### 1. Risk Rules Loading

- **Current:** `LoopStepper` initializes `RiskManagerV04` with empty/minimal rules in smoke tests.
- **3D Rec:** Implement proper loading of `risk_rules.yaml` in the runner. Ensure the runner fails fast if critical rules (e.g., hard stops) are missing.

### 2. From Loop to Bus

- **Current:** `LoopStepper` calls `risk_manager.assess()` and `execution.simulate()` synchronously.
- **3D Rec:** Create "Bridge Adapters" that serialise `OrderIntentV1` to JSON and push to a queue (e.g., Redis List/PubSub or Kafka topic) and listen for `RiskDecisionV1`.
- **Constraint:** Keep `LoopStepper` logic as the "Orchestrator" pattern if we want to maintain deterministic backtesting capability, or split it if we go full async.

### 3. Traceability

- **Current:** `trace_id` is propagated.
- **3D Rec:** Log `trace_id` in every log line (structured logging) to debug distributed calls.

### 4. Metrics

- **Current:** Basic metrics (events count, fills).
- **3D Rec:** Latency histograms (time from OrderIntent to ExecutionReport). Rejection classification (Risk vs Exchange).

## Critical Artifacts for 3D

- `contracts/events_v1.py`: The bible for communication.
- `engine/loop_stepper.py`: The reference implementation of the lifecycle.
- `.github/workflows/smoke_3C.yml`: The baseline for CI stability.

## Handover Packet

- See `report/ORCH_HANDOFF_post3C_close_20260104.md` for the full manifest.
