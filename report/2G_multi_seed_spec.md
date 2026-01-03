# 2G Multi-Seed Calibration Specification

## Overview

This specification details the multi-seed robustness features implemented in `tools/run_calibration_2B.py`. The goal is to evaluate strategy parameter combinations across multiple random seeds to measure performance stability and reduce overfitting to specific market noise.

## 1. Inputs & Outputs

### Inputs

- **`--seeds` CLI**: A comma-separated list of integers (e.g., `--seeds 42,123,456`).
- **Grid Config**: The standard YAML configuration defining parameter ranges.

### Outputs

| File | Description |
|------|-------------|
| `results_by_seed.csv` | Granular results. One row per `(combo_id, seed)` pair. Contains individual run metrics. |
| `results_agg.csv` | Aggregated results. One row per `combo_id`. Contains statistics across seeds. |
| `run_meta.json` | Metadata including the list of seeds used, total runtime, and **ranking stability** metrics. |

## 2. Aggregation Logic

For each parameter combination (`combo_id`), metrics are aggregated across all `N` seeds.

### score_robust

Defined as the **5th percentile (P05)** of the `score` distribution across seeds.

- **Formula**: `score_robust = percentile(scores, 5)`
- **Rationale**: Penalizes strategies that perform well on average but fail catastrophically on some seeds. A robust strategy should have a decent "worst-case" (or near worst-case) performance.

### Aggregated Metrics

For each metric column (e.g., `sharpe_ratio`, `cagr`, `max_drawdown`), the following statistics are computed:

1. **Mean**: Average value.
2. **Median**: P50 value.
3. **P05 (Worst 5%)**: Lower bound performance estimate.
4. **P95 (Best 5%)**: Upper bound performance estimate.
5. **Worst**:
   - For **Drawdown**: Minimum value (e.g., -0.30 is worse than -0.10). _Note: Drawdowns are negative numbers._
   - For **Profit/Sharpe/Etc**: Minimum value (e.g., 0.5 Sharpe is worse than 1.5).

### Nuances

- **NaN / Missing Data**: Rows with missing metric values are dropped before aggregation (`dropna()`). If all seeds yield NaN for a metric, the aggregate is NaN.
- **Zero Trades**: If a run produces zero trades, metrics might be NaN or 0.0 depending on the backtester logic. Aggregation handles these as values if present, or ignores them if NaN.

## 3. Stability Metrics

Ranking stability measures how consistently the strategy rankings are preserved across different seeds. High stability implies that "good" parameters are consistently good regardless of the seed.

### Spearman Correlation

- **Computed via**: Pearson correlation on **ranks** (to avoid SciPy dependency).
- It calculates the pairwise correlation of rankings between every pair of seeds.
- **`spearman_mean`**: Average of all pairwise correlations.
- **`spearman_min`**: Minimum of all pairwise correlations.
- **Range**: [-1.0, 1.0]. 1.0 = identical ranking.

### Top-K Overlap

- **K**: 10
- Measures the intersection of the top-10 strategies between seed pairs.
- **Formula**: Jaccard Index $J(A,B) = \frac{|A \cap B|}{|A \cup B|}$
- **`topk_overlap`**: Average pairwise Jaccard index.
- **Range**: [0.0, 1.0]. 1.0 = same top-10 set (order independent).

## 4. Reproducibility

- **RNG Reset**: The NumPy random number generator (`np.random.seed(s)`) is reset at the start of _each_ seed's loop.
- **Determinism**: Running with the same list of seeds and configuration matches bit-for-bit (verified via tests).
