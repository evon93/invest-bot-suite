"""
test_calibration_2B_override_wiring.py

Tests para verificar que los overrides del grid se aplican correctamente
y producen effective_config_hash distintos.
"""
import pytest
import sys
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.run_calibration_2B import (
    apply_overlay,
    compute_rules_hash,
    flatten_grid,
)


class TestOverlayWiring:
    """Tests for verify that grid overrides are applied correctly."""

    def test_apply_overlay_changes_kelly_cap_factor(self):
        """Overlay with kelly.cap_factor should change effective value."""
        base = {
            "kelly": {"cap_factor": 0.7, "min_trade_size_eur": 20},
            "max_drawdown": {"soft_limit_pct": 0.05, "hard_limit_pct": 0.10},
        }
        overlay = {"kelly.cap_factor": 1.3}
        
        result = apply_overlay(base, overlay)
        
        assert result["kelly"]["cap_factor"] == 1.3
        assert result["kelly"]["min_trade_size_eur"] == 20  # unchanged

    def test_apply_overlay_changes_multiple_sections(self):
        """Overlay can change values in multiple sections."""
        base = {
            "kelly": {"cap_factor": 0.7},
            "max_drawdown": {"soft_limit_pct": 0.05},
            "stop_loss": {"atr_multiplier": 2.0},
        }
        overlay = {
            "kelly.cap_factor": 0.9,
            "max_drawdown.soft_limit_pct": 0.08,
            "stop_loss.atr_multiplier": 3.0,
        }
        
        result = apply_overlay(base, overlay)
        
        assert result["kelly"]["cap_factor"] == 0.9
        assert result["max_drawdown"]["soft_limit_pct"] == 0.08
        assert result["stop_loss"]["atr_multiplier"] == 3.0

    def test_different_overlays_produce_different_hashes(self):
        """Two different overlays should produce different effective_config_hash."""
        base = {
            "kelly": {"cap_factor": 0.7},
            "max_drawdown": {"soft_limit_pct": 0.05, "hard_limit_pct": 0.10},
            "stop_loss": {"atr_multiplier": 2.0},
        }
        
        overlay_a = {"kelly.cap_factor": 0.1}
        overlay_b = {"kelly.cap_factor": 0.9}
        
        result_a = apply_overlay(base, overlay_a)
        result_b = apply_overlay(base, overlay_b)
        
        hash_a = compute_rules_hash(result_a)
        hash_b = compute_rules_hash(result_b)
        
        # Hashes MUST be different
        assert hash_a != hash_b, (
            f"Hashes should differ for different overlays: "
            f"overlay_a={overlay_a} overlay_b={overlay_b}"
        )

    def test_identical_overlays_produce_same_hash(self):
        """Same overlay should produce identical hash."""
        base = {
            "kelly": {"cap_factor": 0.7},
            "max_drawdown": {"soft_limit_pct": 0.05},
            "stop_loss": {"atr_multiplier": 2.0},
        }
        
        overlay = {"kelly.cap_factor": 0.9}
        
        result_1 = apply_overlay(base, overlay)
        result_2 = apply_overlay(base, overlay)
        
        assert compute_rules_hash(result_1) == compute_rules_hash(result_2)

    def test_flatten_grid_produces_combos(self):
        """flatten_grid should produce correct number of combinations."""
        grid = {
            "kelly": {"cap_factor": [0.7, 0.9]},
            "stop_loss": {"atr_multiplier": [2.0, 3.0]},
        }
        
        combos = flatten_grid(grid)
        
        assert len(combos) == 4  # 2 x 2

    def test_flatten_grid_combos_are_unique(self):
        """Each combo from grid should be unique."""
        grid = {
            "kelly": {"cap_factor": [0.7, 0.9, 1.1]},
            "max_drawdown": {"soft_limit_pct": [0.05, 0.08]},
        }
        
        combos = flatten_grid(grid)
        combo_tuples = [tuple(sorted(c.items())) for c in combos]
        
        assert len(combo_tuples) == len(set(combo_tuples)), "Combos should be unique"


class TestHashDiversity:
    """Integration tests for hash diversity across grid."""

    def test_mini_grid_produces_diverse_hashes(self):
        """A mini-grid should produce at least N distinct hashes."""
        base = {
            "kelly": {"cap_factor": 0.7},
            "max_drawdown": {
                "soft_limit_pct": 0.05,
                "hard_limit_pct": 0.10,
                "size_multiplier_soft": 0.5,
            },
            "stop_loss": {"atr_multiplier": 2.0, "min_stop_pct": 0.02},
        }
        
        grid = {
            "kelly": {"cap_factor": [0.7, 1.3]},
            "max_drawdown": {"soft_limit_pct": [0.05, 0.08]},
        }
        
        combos = flatten_grid(grid)
        hashes = set()
        
        for c in combos:
            result = apply_overlay(base, c)
            h = compute_rules_hash(result)
            hashes.add(h)
        
        # Should have as many unique hashes as combos
        assert len(hashes) == len(combos), (
            f"Expected {len(combos)} unique hashes, got {len(hashes)}"
        )
