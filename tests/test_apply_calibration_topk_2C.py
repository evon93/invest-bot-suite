"""
Tests for apply_calibration_topk tool.
"""
import json
import pytest
from pathlib import Path

import yaml

from tools.apply_calibration_topk import (
    load_best_params,
    validate_params,
    apply_params,
    apply_calibration,
)


# === Fixtures ===

@pytest.fixture
def minimal_base_yaml() -> dict:
    """Minimal base YAML structure."""
    return {
        "stop_loss": {
            "atr_multiplier": 2.5,
            "min_stop_pct": 0.02,
            "lookback_days": 30,
        },
        "max_drawdown": {
            "soft_limit_pct": 0.05,
            "hard_limit_pct": 0.08,
            "lookback_days": 90,
            "size_multiplier_soft": 0.5,
        },
        "kelly": {
            "cap_factor": 0.5,
            "min_trade_size_eur": 20,
        },
    }


@pytest.fixture
def minimal_best_params() -> dict:
    """Minimal best_params structure."""
    return {
        "meta": {
            "source_combo_id": "test_combo",
        },
        "params": {
            "stop_loss": {
                "atr_multiplier": 2.0,
                "min_stop_pct": 0.03,
            },
            "max_drawdown": {
                "soft_limit_pct": 0.04,
                "hard_limit_pct": 0.10,
                "size_multiplier_soft": 0.6,
            },
            "kelly": {
                "cap_factor": 0.7,
            },
        },
    }


# === Test apply_generates_candidate_file ===

def test_apply_generates_candidate_file(tmp_path: Path, minimal_base_yaml, minimal_best_params):
    """Test that apply_calibration generates candidate file."""
    # Create input files
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.dump(minimal_base_yaml), encoding="utf-8")
    
    best_path = tmp_path / "best.json"
    best_path.write_text(json.dumps(minimal_best_params), encoding="utf-8")
    
    out_path = tmp_path / "candidate.yaml"
    patch_path = tmp_path / "diff.patch"
    
    # Apply
    result = apply_calibration(best_path, base_path, out_path, patch_path)
    
    # Check file was created
    assert out_path.exists()
    assert patch_path.exists()
    
    # Check changes were applied
    candidate = yaml.safe_load(out_path.read_text(encoding="utf-8"))
    assert candidate["stop_loss"]["atr_multiplier"] == 2.0
    assert candidate["kelly"]["cap_factor"] == 0.7
    
    # Check other values preserved
    assert candidate["stop_loss"]["lookback_days"] == 30
    assert candidate["kelly"]["min_trade_size_eur"] == 20


# === Test apply_is_idempotent ===

def test_apply_is_idempotent(tmp_path: Path, minimal_base_yaml, minimal_best_params):
    """Test that running apply twice produces same result."""
    base_path = tmp_path / "base.yaml"
    base_path.write_text(yaml.dump(minimal_base_yaml), encoding="utf-8")
    
    best_path = tmp_path / "best.json"
    best_path.write_text(json.dumps(minimal_best_params), encoding="utf-8")
    
    out_path = tmp_path / "candidate.yaml"
    
    # Run twice
    apply_calibration(best_path, base_path, out_path, None)
    first_content = out_path.read_text(encoding="utf-8")
    
    apply_calibration(best_path, base_path, out_path, None)
    second_content = out_path.read_text(encoding="utf-8")
    
    assert first_content == second_content


# === Test apply_rejects_invalid_ranges ===

def test_apply_rejects_invalid_ranges_hard_less_than_soft():
    """Test that hard < soft is rejected."""
    params = {
        "stop_loss": {"atr_multiplier": 2.0, "min_stop_pct": 0.02},
        "max_drawdown": {
            "soft_limit_pct": 0.10,  # soft > hard
            "hard_limit_pct": 0.05,
            "size_multiplier_soft": 0.5,
        },
        "kelly": {"cap_factor": 0.5},
    }
    errors = validate_params(params)
    assert any("hard_limit_pct" in e and "soft_limit_pct" in e for e in errors)


def test_apply_rejects_invalid_atr_multiplier():
    """Test that atr_multiplier <= 0 is rejected."""
    params = {
        "stop_loss": {"atr_multiplier": 0, "min_stop_pct": 0.02},
        "max_drawdown": {
            "soft_limit_pct": 0.05,
            "hard_limit_pct": 0.10,
            "size_multiplier_soft": 0.5,
        },
        "kelly": {"cap_factor": 0.5},
    }
    errors = validate_params(params)
    assert any("atr_multiplier" in e for e in errors)


def test_apply_rejects_invalid_min_stop_pct():
    """Test that min_stop_pct outside (0,1) is rejected."""
    params = {
        "stop_loss": {"atr_multiplier": 2.0, "min_stop_pct": 1.5},
        "max_drawdown": {
            "soft_limit_pct": 0.05,
            "hard_limit_pct": 0.10,
            "size_multiplier_soft": 0.5,
        },
        "kelly": {"cap_factor": 0.5},
    }
    errors = validate_params(params)
    assert any("min_stop_pct" in e for e in errors)


# === Test apply_missing_path_raises ===

def test_apply_missing_section_raises(tmp_path: Path, minimal_best_params):
    """Test that missing section in base YAML raises error."""
    # Base without max_drawdown section
    base = {
        "stop_loss": {
            "atr_multiplier": 2.5,
            "min_stop_pct": 0.02,
        },
        "kelly": {
            "cap_factor": 0.5,
        },
        # missing max_drawdown
    }
    
    with pytest.raises(ValueError, match="missing section"):
        apply_params(base, minimal_best_params["params"])


def test_apply_missing_key_raises(tmp_path: Path, minimal_best_params):
    """Test that missing key in base YAML raises error."""
    # Base without max_drawdown.size_multiplier_soft
    base = {
        "stop_loss": {
            "atr_multiplier": 2.5,
            "min_stop_pct": 0.02,
        },
        "max_drawdown": {
            "soft_limit_pct": 0.05,
            "hard_limit_pct": 0.08,
            # missing size_multiplier_soft
        },
        "kelly": {
            "cap_factor": 0.5,
        },
    }
    
    with pytest.raises(ValueError, match="missing key"):
        apply_params(base, minimal_best_params["params"])


# === Test load_best_params validation ===

def test_load_best_params_rejects_missing_params(tmp_path: Path):
    """Test that best_params without 'params' key is rejected."""
    best_path = tmp_path / "bad.json"
    best_path.write_text('{"meta": {}}', encoding="utf-8")
    
    with pytest.raises(ValueError, match="missing 'params'"):
        load_best_params(best_path)
