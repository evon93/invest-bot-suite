# DeepSeek Audit Pack — RiskManager v0.6 (3C.3)

## Context

This pack contains the implementation of **RiskManager v0.6 (event-native)** for the invest-bot-suite project. v0.6 wraps v0.4 internally and should produce equivalent risk decisions.

## Audit Focus

**Logic Audit + v0.4/v0.6 Parity + Additional Tests**

Please review for:

1. **Logic correctness**: Is the delegation to v0.4 semantically correct?
2. **Parity verification**: Do v0.4 and v0.6 produce identical `allowed` results for the same inputs?
3. **Additional test suggestions**: What test cases are missing?

## How to Use This Pack

### Option A: File Upload

1. Upload all files from `txt/` folder
2. Use this manifest for context

### Option B: Copy-Paste

1. Copy content from `payload.md` into chat

## Files Included

| File | Description |
|------|-------------|
| `risk_manager_v0_6.py.txt` | v0.6 implementation |
| `risk_manager_v_0_4.py.txt` | v0.4 implementation (delegated) |
| `risk_input_adapter.py.txt` | Adapter layer |
| `test_risk_manager_v0_6_compat_v0_4_parity.py.txt` | Parity tests |
| `risk_rules_prod.yaml.txt` | Risk configuration |
| `AG-3C-3-1_diff.patch.txt` | Changes made |

## Key Questions for DeepSeek

1. Are there cases where v0.6 would return `allowed=True` but v0.4 would return `False` (or vice versa)?
2. Is the `current_weights` handling in v0.6 consistent with v0.4?
3. What happens if `risk_rules.yaml` has unexpected keys?
4. Suggest 5 additional test cases for parity verification.

## Expected Output Format

```markdown
## Logic Audit
- [ ] Delegation is correct
- [ ] No semantic drift from v0.4

## Parity Analysis
| Scenario | v0.4 | v0.6 | Match? |
|----------|------|------|--------|
| ... | | | |

## Suggested Additional Tests
1. [Test case description]
2. ...
```
