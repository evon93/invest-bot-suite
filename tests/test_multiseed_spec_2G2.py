"""
test_multiseed_spec_2G2.py — Comprehensive tests for multi-seed calibration spec (2G.2)

Covers:
1. Seed parsing edge cases.
2. Determinism (idempotency).
3. Aggregation logic consistency.
"""
import pytest
import pandas as pd
import numpy as np
import shutil
import subprocess
import sys
import hashlib
from pathlib import Path

from tools.run_calibration_2B import parse_seeds, aggregate_seed_results, run_calibration

REPO_ROOT = Path(__file__).resolve().parent.parent

class TestMultiSeedSpec:

    # --- 1. Seed Parsing Tests ---
    
    def test_parse_seeds_basic(self):
        assert parse_seeds("42") == [42]
        assert parse_seeds("1,2,3") == [1, 2, 3]

    def test_parse_seeds_formatting(self):
        assert parse_seeds(" 1 , 2 , 3 ") == [1, 2, 3]
        assert parse_seeds("42,") == [42]  # Trailing comma handling (split might give empty string)

    def test_parse_seeds_invalid_inputs(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_seeds("")
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_seeds("   ")
        with pytest.raises(ValueError, match="Invalid seed"):
            parse_seeds("abc")
        with pytest.raises(ValueError, match="Invalid seed"):
            parse_seeds("1,2,foo")
        with pytest.raises(ValueError, match="Duplicate seeds"):
            parse_seeds("1,2,1")
        with pytest.raises(ValueError, match="must be non-negative"):
            parse_seeds("-10")

    # --- 2. Determinism Tests ---

    def test_run_determinism(self, tmp_path):
        """
        Running the calibration twice with the same seeds and config
        matches bit-for-bit in output files.
        """
        output_1 = tmp_path / "run1"
        output_2 = tmp_path / "run2"
        output_1.mkdir()
        output_2.mkdir()
        
        seeds = [123, 456]
        # Quick run, minimal grid implies extremely fast execution
        
        # Run 1
        run_calibration(
            mode="quick",
            max_combinations=2,
            seeds=seeds,
            output_dir_override=str(output_1),
        )
        
        # Run 2
        run_calibration(
            mode="quick",
            max_combinations=2,
            seeds=seeds,
            output_dir_override=str(output_2),
        )
        
        # Compare results_by_seed.csv content
        csv1 = (output_1 / "results_by_seed.csv").read_text(encoding="utf-8")
        csv2 = (output_2 / "results_by_seed.csv").read_text(encoding="utf-8")
        
        # Ignore timestamp/duration diffs if any, but CSV rows strictly deterministic
        # We can drop columns 'duration_s' or 'timestamp' before comparing if they vary
        # But 'duration_s' is in the csv. Let's compare DataFrames excluding duration.
        
        df1 = pd.read_csv(output_1 / "results_by_seed.csv")
        df2 = pd.read_csv(output_2 / "results_by_seed.csv")
        
        # duration_s might vary slightly
        if "duration_s" in df1.columns:
            df1 = df1.drop(columns=["duration_s"])
        if "duration_s" in df2.columns:
            df2 = df2.drop(columns=["duration_s"])
            
        pd.testing.assert_frame_equal(df1, df2)
        
        # Compare aggregated results
        agg1 = pd.read_csv(output_1 / "results_agg.csv")
        agg2 = pd.read_csv(output_2 / "results_agg.csv")
        pd.testing.assert_frame_equal(agg1, agg2)

    # --- 3. Aggregation Consistency Tests ---

    def test_aggregation_logic_distribution(self):
        """
        Verify p05 <= median <= p95 and worst definition.
        """
        # Create synthetic results for a single combo
        combo_id = "test_combo"
        metrics = ["score", "sharpe", "drawdown"]
        
        # 20 samples: 0 to 19
        dataset = []
        for i in range(20):
            dataset.append({
                "combo_id": combo_id,
                "seed": i,
                "score": float(i),       # 0..19
                "sharpe": float(i),      # 0..19
                "drawdown": -float(i)    # 0..-19 (0 is best, -19 is worst)
            })
            
        aggregated = aggregate_seed_results(dataset, metrics)
        assert len(aggregated) == 1
        row = aggregated[0]
        
        # Score: 0..19. Median ~9.5. P05 ~ 0.95. P95 ~ 18.05.
        # Check order
        assert row["score_p05"] <= row["score_median"]
        assert row["score_median"] <= row["score_p95"]
        
        # Score robust = p05
        assert row["score_robust"] == row["score_p05"]
        # Score worst = min = 0
        assert row["score_worst"] == 0.0
        
        # Drawdown: 0..-19. 
        # Mean ~ -9.5
        # Worst = min = -19.0
        assert row["drawdown_worst"] == -19.0
        assert row["drawdown_p05"] <= row["drawdown_p95"] # -18.05 vs -0.95

    def test_aggregation_nan_handling(self):
        """
        NaNs should be ignored in aggregation.
        """
        dataset = [
            {"combo_id": "c1", "seed": 1, "score": 10.0},
            {"combo_id": "c1", "seed": 2, "score": np.nan},
            {"combo_id": "c1", "seed": 3, "score": 20.0},
        ] # Effective scores: [10.0, 20.0]
        
        aggregated = aggregate_seed_results(dataset, ["score"])
        row = aggregated[0]
        
        assert row["score_mean"] == 15.0
        assert row["n_seeds"] == 3 # All seeds counted in n_seeds header
        # Robust should be p05 of [10, 20]. (~10.5 depending on interpolation)
        assert not np.isnan(row["score_robust"])
