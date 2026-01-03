"""
test_ranking_stability_2G.py — QA tests for ranking stability logic (AG-2G-1-QA)

Tests edge cases: identical rankings, inverted rankings, small N.
"""
import pytest
import pandas as pd
import numpy as np
from tools.run_calibration_2B import compute_ranking_stability

class TestRankingStabilityQA:
    
    def test_identical_rankings(self):
        """Identical scores across seeds should yield stability 1.0."""
        # 3 seeds, 5 combos, perfect correlation
        seeds = [1, 2, 3]
        results = []
        for s in seeds:
            for i in range(5):
                results.append({
                    "combo_id": f"c{i}", 
                    "seed": s, 
                    "score": float(i) # Higher i = higher score
                })
        
        metrics = compute_ranking_stability(results, seeds)
        assert metrics["spearman_mean"] == 1.0
        assert metrics["spearman_min"] == 1.0
        assert metrics["topk_overlap"] == 1.0

    def test_inverted_rankings(self):
        """Perfectly inverted rankings between 2 seeds should yield -1.0."""
        seeds = [1, 2]
        results = []
        # Seed 1: 0..4 (ascending)
        for i in range(5):
            results.append({"combo_id": f"c{i}", "seed": 1, "score": float(i)})
        # Seed 2: 4..0 (descending)
        for i in range(5):
            results.append({"combo_id": f"c{i}", "seed": 2, "score": float(4-i)})
            
        metrics = compute_ranking_stability(results, seeds)
        assert metrics["spearman_mean"] == -1.0
        assert metrics["spearman_min"] == -1.0
        # TopK overlap might not be 0 because the set of items is the same even if order is inverted.
        # With N=5 and K=10, both have sets {c0..c4}. Overlap = 1.0. Correct.
        assert metrics["topk_overlap"] == 1.0

    def test_inverted_rankings_topk_disjoint(self):
        """Disjoint top sets should yield 0 overlap."""
        # N=20. Seed 1 likes c0..c9 (high scores), Seed 2 likes c10..c19.
        seeds = [1, 2]
        results = []
        for i in range(20):
            # Seed 1: c0..c9 high, c10..c19 low
            s1 = 100 if i < 10 else 0
            # Seed 2: c0..c9 low, c10..c19 high
            s2 = 0 if i < 10 else 100
            
            results.append({"combo_id": f"c{i}", "seed": 1, "score": float(s1 + i)}) # Add i to avoid ties
            results.append({"combo_id": f"c{i}", "seed": 2, "score": float(s2 + i)})
            
        metrics = compute_ranking_stability(results, seeds)
        # Spearman should be low/negative
        assert metrics["spearman_mean"] < 0
        # TopK overlap (K=10) should be 0 because sets are disjoint
        assert metrics["topk_overlap"] == 0.0

    def test_n_less_than_2(self):
        """N=1 should handle gracefully (returns 0.0 or 1.0 depending on interpretation)."""
        seeds = [1, 2]
        results = [
            {"combo_id": "c1", "seed": 1, "score": 10},
            {"combo_id": "c1", "seed": 2, "score": 10},
        ]
        metrics = compute_ranking_stability(results, seeds)
        # N=1 means correlation undefined. Code returns 0.0 if correlations list empty.
        # TopK sets {c1} vs {c1} -> overlap 1.0
        assert metrics["spearman_mean"] == 0.0
        assert metrics["topk_overlap"] == 1.0

    def test_seeds_missing_data(self):
        """Handles missing seeds/data gracefully."""
        seeds = [1, 2, 3] # Seed 3 has no data
        results = []
        for s in [1, 2]:
            for i in range(5):
                results.append({"combo_id": f"c{i}", "seed": s, "score": float(i)})
        
        metrics = compute_ranking_stability(results, seeds)
        # Should compare 1 vs 2, ignore 3.
        assert metrics["spearman_mean"] == 1.0
