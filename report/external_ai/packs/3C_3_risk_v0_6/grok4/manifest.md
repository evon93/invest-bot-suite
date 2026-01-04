# Grok4 Audit Pack — RiskManager v0.6 (3C.3)

## Context

This pack contains the implementation of **RiskManager v0.6 (event-native)** for the invest-bot-suite project. v0.6 wraps the existing v0.4 with an event-driven interface using typed contracts.

## Audit Focus

**Architecture + Edge Cases + Test Matrix**

Please review for:

1. **Architecture decisions**: Is the delegation to v0.4 clean? Should v0.6 have its own logic?
2. **Edge cases**: What happens with invalid intents, missing NAV, zero qty?
3. **Test coverage**: Fill the test matrix below with missing scenarios.

## How to Use This Pack

### Option A: File Upload

1. Upload all files from `txt/` folder (rename .txt extension if needed)
2. Paste the manifest for context

### Option B: Copy-Paste

1. Copy the content from `payload.md` directly into chat
2. All code is embedded in fenced blocks

## Files Included

| File | Description |
|------|-------------|
| `risk_manager_v0_6.py.txt` | Main implementation |
| `risk_manager_v_0_4.py.txt` | Delegated v0.4 logic |
| `events_v1.py.txt` | Contract definitions |
| `risk_input_adapter.py.txt` | Adapter for OrderIntent→dict |
| `run_live_integration_3B.py.txt` | Runner with --risk-version flag |
| `risk_rules_prod.yaml.txt` | Risk configuration |
| `test_risk_manager_v0_6_contract.py.txt` | Contract tests |
| `test_risk_manager_v0_6_compat_v0_4_parity.py.txt` | Parity tests |
| `test_contracts_events_v1_roundtrip.py.txt` | Events roundtrip tests |
| `test_risk_input_adapter.py.txt` | Adapter tests |
| `AG-3C-3-1_diff.patch.txt` | Diff of changes |

## Test Matrix (Please Fill)

| Scenario | Expected | Tested? | Notes |
|----------|----------|---------|-------|
| Valid BUY intent | allowed=True | ✅ | |
| Valid SELL intent | allowed=True | ✅ | |
| Invalid symbol (empty) | allowed=False, reason=INVALID | ✅ | |
| Invalid side (HOLD) | allowed=False, reason=ADAPTER_ERROR | | |
| qty=0 | allowed=False | | |
| qty<0 | allowed=False | | |
| notional without NAV | uses default_weight | | |
| LIMIT order no price | | | |
| v0.4 parity | allowed matches | ✅ | |
| ... | | | |

## Questions for Grok4

1. Are there edge cases in `_normalize_reasons()` not covered?
2. Should `assess()` accept a pre-validated intent or always call `validate()`?
3. What's the right behavior for short positions (SELL with no existing position)?
