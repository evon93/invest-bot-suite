# Robustness 2D Specification

**Version:** 1.0.0  
**Date:** 2025-12-27  
**Status:** Draft  

---

## 1. Purpose

Validate that the calibrated parameters from Phase 2C (`best_params_2C.json`) remain robust under:

1. **Parameter perturbations**: Small variations in risk parameters
2. **Data perturbations**: Temporal window shifts and subsampling
3. **Seed variations**: Different random seeds for reproducibility

### Non-Objectives

- ❌ Modify `risk_rules.yaml` (baseline is read-only)
- ❌ Implement live trading signals
- ❌ Optimize parameters (that was Phase 2C)

---

## 2. Baseline vs Candidate Contract

### Baseline

The **baseline** is the immutable reference configuration:

```yaml
source: risk_rules.yaml
nature: read-only
modifications: FORBIDDEN
```

### Candidate

The **candidate** applies `configs/best_params_2C.json` overrides **in-memory**:

```python
# Pseudocode
candidate = deep_copy(baseline)
candidate.apply_overrides(best_params_2C["params"])
# risk_rules.yaml is NEVER written
```

**Key Invariant:** `risk_rules.yaml` remains unchanged throughout all robustness tests.

---

## 3. Scenario ID Definition

Each scenario has a **deterministic, unique identifier**:

```
scenario_id = "{mode}_{seed}_{param_hash}_{data_hash}"
```

### Components

| Component | Type | Description |
|-----------|------|-------------|
| `mode` | string | `quick` or `full` |
| `seed` | int | Random seed (default: 42) |
| `param_hash` | sha256[:8] | Hash of param perturbation JSON |
| `data_hash` | sha256[:8] | Hash of data perturbation config |

### Generation Algorithm

```python
import hashlib
import json

def generate_scenario_id(mode, seed, param_config, data_config):
    param_str = json.dumps(param_config, sort_keys=True)
    data_str = json.dumps(data_config, sort_keys=True)
    
    param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:8]
    data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:8]
    
    return f"{mode}_{seed}_{param_hash}_{data_hash}"
```

### Label Length

- Max label length: 128 characters
- If exceeded: Use full hash as fallback

---

## 4. Invariants and Validations

### Hard Invariants (Error → Abort)

| Invariant | Condition |
|-----------|-----------|
| `risk_rules.yaml` unchanged | SHA256 before == after |
| Seed reproducibility | Same seed → same results |
| Max scenarios respected | count ≤ `max_scenarios` |
| Timeout respected | duration ≤ `timeout_minutes` |

### Soft Validations (Warning → Continue)

| Validation | Condition |
|------------|-----------|
| All seeds used | count(seeds_used) == seed_list.length |
| No NaN metrics | all metrics finite |
| Reasonable runtime | duration < expected * 2 |

---

## 5. Risk Constraint Gates

### Hard Gates (Scenario Fails)

```yaml
max_drawdown_absolute: -0.15  # DD worse than -15%
min_sharpe: 0.3               # Sharpe below 0.3
min_cagr: 0.05                # CAGR below 5%
max_pct_time_hard_stop: 0.25  # Hard stop > 25% of time
```

### Soft Warnings (Logged)

```yaml
max_drawdown_soft: -0.10
min_win_rate: 0.45
max_consecutive_losses: 10
```

---

## 6. Output Layout

```
report/robustness_2D/
├── results.csv           # All scenario results
├── summary.md            # Human-readable summary
├── run_meta.json         # Execution metadata
└── errors.jsonl          # Error log (JSON lines)
```

### results.csv Columns

| Column | Type | Description |
|--------|------|-------------|
| `scenario_id` | string | Unique deterministic ID |
| `scenario_label` | string | Human-readable label |
| `mode` | string | quick/full |
| `seed` | int | Random seed |
| `params_json` | string | JSON of perturbations |
| `sharpe_ratio` | float | Sharpe ratio |
| `cagr` | float | CAGR |
| `max_drawdown` | float | Max drawdown (negative) |
| `calmar_ratio` | float | Calmar ratio |
| `win_rate` | float | Win rate |
| `pct_time_hard_stop` | float | % time in hard stop |
| `score` | float | Composite score |
| `gate_pass` | bool | All gates passed |
| `warnings` | string | Warning messages |
| `duration_seconds` | float | Scenario duration |
| `error` | string | Error if failed |

### run_meta.json Schema

```json
{
  "start_time": "ISO8601",
  "end_time": "ISO8601",
  "mode": "quick|full",
  "git_head": "commit_hash",
  "config_hash": "sha256",
  "scenarios_total": 20,
  "scenarios_passed": 18,
  "scenarios_failed": 2,
  "pass_rate": 0.9
}
```

---

## 7. Scoring Formula

### Weights (from YAML)

```yaml
weights:
  sharpe_ratio: 1.0
  cagr: 0.5
  win_rate: 0.3
  max_drawdown_penalty: 1.5
  hard_stop_penalty: 0.5
```

### Formula

```python
score = (
    weights.sharpe_ratio * sharpe_ratio
    + weights.cagr * cagr
    + weights.win_rate * win_rate
    - weights.max_drawdown_penalty * abs(max_drawdown)
    - weights.hard_stop_penalty * pct_time_hard_stop
)
```

### Aggregation

```python
# Per-param-set aggregation
aggregated_score = mean(scores_across_seeds)

# Overall robustness score
robustness_score = mean(aggregated_scores_all_perturbations)

# Confidence interval
ci_lower, ci_upper = bootstrap_ci(scores, alpha=0.05)
```

### Pass Criteria

```yaml
min_passing_scenarios: 0.8  # 80% of scenarios must pass gates
```

---

## 8. CI Gates

### Quick Mode (PR Gate)

```yaml
trigger: pull_request
max_duration: 10 minutes
pass_criteria:
  - all_hard_gates_pass: true
  - min_passing_rate: 0.8
  - no_critical_errors: true
```

### Full Mode (Nightly)

```yaml
trigger: schedule (nightly)
max_duration: 2 hours
pass_criteria:
  - all_quick_criteria: true
  - statistical_significance: true
  - confidence_interval_narrow: true
```

---

## 9. External References

| Document | Location |
|----------|----------|
| DeepSeek Contract Design | `report/external_ai/2D_02_2.1/DeepSeek_DS-2D-02-2.1_contract.pdf` |
| Grok4 Research | `report/external_ai/2D_02_2.1/Grok4_GR-2D-02-2.1_research.pdf` |
| Gemini3Pro Schema | `report/external_ai/2D_02_2.1/Gemini3Pro_GM-2D-02-2.1_schema.pdf` |

---

## 10. Backlog for Step 3 (Runner Implementation)

### P0 - Critical

- [ ] Implement `tools/run_robustness_2D.py`
- [ ] Integrate with existing backtester
- [ ] Generate `results.csv` with all columns

### P1 - Important

- [ ] Parallel scenario execution
- [ ] Progress bar and ETA
- [ ] Early abort on timeout

### P2 - Nice to Have

- [ ] Interactive HTML report
- [ ] Comparison with previous runs
- [ ] Slack/webhook notifications
