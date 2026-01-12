# Bridge 3J → 3K Report

## Phase 3J Summary

Strategy v0.8 selector and offline validation infrastructure completed.

**Key Deliverables**:

- Strategy registry pattern for version selection
- EMA crossover strategy (v0.8) with determinism guarantees
- Offline validation harness and live smoke tests
- CI gate for strategy validation

## Proposed Phase 3K: Market Data + Execution Adapters

### Objective

Introduce real/sandbox market data feeds and execution adapters for paper → realish → production path.

### Scope Items

| ID | Description | Priority |
|----|-------------|----------|
| 3K-1 | MarketDataAdapter interface | HIGH |
| 3K-2 | CCXT sandbox data feed integration | HIGH |
| 3K-3 | ExecutionAdapter interface standardization | MEDIUM |
| 3K-4 | Gated realish mode with sandbox orders | MEDIUM |
| 3K-5 | Latency simulation improvements | LOW |

### Risks

1. **API Rate Limits**: CCXT sandbox may have restrictions
2. **Data Quality**: Sandbox data may differ from production
3. **Network Dependencies**: Tests may flake on CI without mocks

### Suggested Tests

- MarketDataAdapter mock tests
- CCXT sandbox connection smoke (gated)
- Data format validation (OHLCV schema)
- Latency simulation determinism

### Dependencies

- Phase 3J (complete) ✅
- CCXT library (already in deps)
- .env config for sandbox credentials

## Transition Notes

- main branch is stable at `6d18465`
- All 3J tests pass (615 passed)
- Strategy v0.8 is functional but uses placeholder sizing (qty=1.0)
