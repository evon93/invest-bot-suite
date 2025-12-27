"""
tests/test_validate_robustness_2D_config.py

Tests for robustness_2D.yaml validator.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

# Add project root to path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.validate_robustness_2D_config import (
    validate_config,
    validate_required_keys,
    validate_ranges,
    validate_seeds,
    validate_modes_coherence,
    validate_param_perturbations,
    get_nested_value,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def valid_config():
    """Minimal valid configuration."""
    return {
        "meta": {
            "schema_version": "1.0.0",
            "description": "Test config",
        },
        "baseline": {
            "risk_rules_path": "risk_rules.yaml",
            "candidate_params_path": "configs/best_params_2C.json",
        },
        "engine": {
            "reproducibility": {
                "default_seed": 42,
                "seed_list": [42, 123],
            },
            "modes": {
                "quick": {
                    "max_scenarios": 20,
                    "timeout_minutes": 10,
                },
                "full": {
                    "max_scenarios": 500,
                    "timeout_minutes": 120,
                },
            },
        },
        "risk_constraints": {
            "gates": {
                "max_drawdown_absolute": -0.15,
            },
        },
        "sweep": {
            "param_perturbations": {
                "kelly.cap_factor": {
                    "type": "range",
                    "min": 0.5,
                    "max": 0.9,
                },
            },
            "data_perturbations": {
                "window_shifts": {
                    "type": "range",
                    "min": -30,
                    "max": 30,
                },
            },
        },
        "output": {
            "directory": "report/robustness_2D",
            "files": {
                "results": "results.csv",
            },
        },
        "scoring": {
            "enabled": True,
            "weights": {
                "sharpe_ratio": 1.0,
                "cagr": 0.5,
            },
        },
    }


@pytest.fixture
def temp_config_file(valid_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(valid_config, f)
        return Path(f.name)


# =============================================================================
# Tests: get_nested_value
# =============================================================================

def test_get_nested_value_simple():
    data = {"a": {"b": {"c": 42}}}
    assert get_nested_value(data, "a.b.c") == 42


def test_get_nested_value_missing():
    data = {"a": {"b": 1}}
    assert get_nested_value(data, "a.c") is None


def test_get_nested_value_top_level():
    data = {"top": "value"}
    assert get_nested_value(data, "top") == "value"


# =============================================================================
# Tests: validate_required_keys
# =============================================================================

def test_validate_required_keys_valid(valid_config):
    errors = validate_required_keys(valid_config)
    assert len(errors) == 0


def test_validate_required_keys_missing_top_level():
    config = {"meta": {"schema_version": "1.0"}}
    errors = validate_required_keys(config)
    assert any("baseline" in e for e in errors)


def test_validate_required_keys_missing_nested():
    config = {
        "meta": {},  # Missing schema_version and description
        "baseline": {},
        "engine": {},
        "risk_constraints": {},
        "sweep": {},
        "output": {},
        "scoring": {},
    }
    errors = validate_required_keys(config)
    assert any("meta.schema_version" in e for e in errors)


# =============================================================================
# Tests: validate_ranges
# =============================================================================

def test_validate_ranges_valid(valid_config):
    errors = validate_ranges(valid_config)
    assert len(errors) == 0


def test_validate_ranges_out_of_range():
    config = {
        "engine": {
            "reproducibility": {
                "default_seed": -1,  # Invalid: must be >= 0
            },
            "modes": {
                "quick": {"max_scenarios": 0},  # Invalid: must be >= 1
                "full": {"max_scenarios": 500},
            },
        },
    }
    errors = validate_ranges(config)
    assert len(errors) >= 2


# =============================================================================
# Tests: validate_seeds
# =============================================================================

def test_validate_seeds_valid(valid_config):
    errors = validate_seeds(valid_config)
    assert len(errors) == 0


def test_validate_seeds_empty_list():
    config = {
        "engine": {
            "reproducibility": {
                "default_seed": 42,
                "seed_list": [],
            },
        },
    }
    errors = validate_seeds(config)
    assert any("cannot be empty" in e for e in errors)


def test_validate_seeds_default_not_in_list():
    config = {
        "engine": {
            "reproducibility": {
                "default_seed": 999,
                "seed_list": [42, 123],
            },
        },
    }
    errors = validate_seeds(config)
    assert any("not in seed_list" in e for e in errors)


def test_validate_seeds_non_int():
    config = {
        "engine": {
            "reproducibility": {
                "default_seed": 42,
                "seed_list": [42, "abc"],
            },
        },
    }
    errors = validate_seeds(config)
    assert any("must be int" in e for e in errors)


# =============================================================================
# Tests: validate_modes_coherence
# =============================================================================

def test_validate_modes_coherence_valid(valid_config):
    errors = validate_modes_coherence(valid_config)
    assert len(errors) == 0


def test_validate_modes_quick_more_intensive():
    config = {
        "engine": {
            "modes": {
                "quick": {"max_scenarios": 1000, "timeout_minutes": 60},
                "full": {"max_scenarios": 100, "timeout_minutes": 30},
            },
        },
    }
    errors = validate_modes_coherence(config)
    assert len(errors) == 2
    assert any("max_scenarios" in e for e in errors)
    assert any("timeout_minutes" in e for e in errors)


# =============================================================================
# Tests: validate_param_perturbations
# =============================================================================

def test_validate_param_perturbations_valid(valid_config):
    errors = validate_param_perturbations(valid_config)
    assert len(errors) == 0


def test_validate_param_perturbations_invalid_type():
    config = {
        "sweep": {
            "param_perturbations": {
                "kelly.cap_factor": {
                    "type": "invalid",
                },
            },
        },
    }
    errors = validate_param_perturbations(config)
    assert any("'range' or 'list'" in e for e in errors)


def test_validate_param_perturbations_min_greater_than_max():
    config = {
        "sweep": {
            "param_perturbations": {
                "kelly.cap_factor": {
                    "type": "range",
                    "min": 0.9,
                    "max": 0.5,
                },
            },
        },
    }
    errors = validate_param_perturbations(config)
    assert any("min > max" in e for e in errors)


# =============================================================================
# Tests: validate_config (integration)
# =============================================================================

def test_validate_config_valid(temp_config_file):
    errors, warnings = validate_config(temp_config_file)
    assert len(errors) == 0


def test_validate_config_file_not_found():
    errors, warnings = validate_config(Path("/nonexistent/config.yaml"))
    assert len(errors) == 1
    assert "not found" in errors[0]


def test_validate_config_invalid_yaml():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write("invalid: yaml: content: :")
        path = Path(f.name)
    
    errors, warnings = validate_config(path)
    assert len(errors) >= 1


def test_validate_config_real_file():
    """Test with actual robustness_2D.yaml if it exists."""
    config_path = Path("configs/robustness_2D.yaml")
    if config_path.exists():
        errors, warnings = validate_config(config_path)
        assert len(errors) == 0, f"Real config has errors: {errors}"
