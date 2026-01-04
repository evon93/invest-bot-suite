# Gemini3Pro Audit Pack — RiskManager v0.6 (3C.3)

## Context

This pack contains the implementation of **RiskManager v0.6 (event-native)** for the invest-bot-suite project. v0.6 provides typed contracts with serialization helpers (`to_dict`/`from_dict`/`validate`).

## Audit Focus

**Serialization + Invariant Validation + Small Improvements (<=30 lines)**

Please review for:

1. **Serialization correctness**: Are `to_dict()` and `from_dict()` fully symmetric?
2. **Validation invariants**: Are all edge cases covered in `validate()`?
3. **Small improvements**: Suggest changes <=30 lines that improve robustness.

## How to Use This Pack

### Option A: File Upload

1. Upload all files from `txt/` folder
2. Use this manifest for context

### Option B: Copy-Paste

1. Copy content from `payload.md` into chat

## Files Included

| File | Description |
|------|-------------|
| `events_v1.py.txt` | Contract definitions (OrderIntentV1, RiskDecisionV1, etc.) |
| `risk_manager_v0_6.py.txt` | Main implementation with assess() |
| `risk_input_adapter.py.txt` | Adapter for OrderIntent→dict |
| `test_contracts_events_v1_roundtrip.py.txt` | Roundtrip tests |
| `test_risk_input_adapter.py.txt` | Adapter tests |

## Key Questions for Gemini3Pro

1. Is `_normalize_reasons()` handling all input types correctly (list, str, dict, None)?
2. Should `from_dict()` have stricter type coercion for numerical fields?
3. Are there missing invariant checks in `validate()` methods?
4. Suggest up to 3 small improvements (<=30 lines each) for better robustness.

## Expected Output Format

```markdown
## Serialization Review
- [ ] `to_dict()` is correct
- [ ] `from_dict()` handles aliases
- [ ] Roundtrip is symmetric

## Invariant Review
- [ ] All required fields validated
- [ ] Edge cases covered

## Suggested Improvements (<=30 lines each)
1. [Description] - [~X lines]
2. ...
```
