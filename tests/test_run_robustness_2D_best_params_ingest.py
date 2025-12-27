"""
tests/test_run_robustness_2D_best_params_ingest.py

Unit tests for best_params ingest logic in run_robustness_2D.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_robustness_2D import (
    extract_params_dotted,
    flatten_nested_params,
)


# =============================================================================
# Tests: flatten_nested_params
# =============================================================================

def test_flatten_nested_params_simple():
    """Test flattening a simple nested dict."""
    params = {"kelly": {"cap_factor": 0.7}}
    result = flatten_nested_params(params)
    assert result == {"kelly.cap_factor": 0.7}


def test_flatten_nested_params_multiple():
    """Test flattening multiple sections."""
    params = {
        "kelly": {"cap_factor": 0.7, "min_trade": 20},
        "stop_loss": {"atr_multiplier": 2.0},
    }
    result = flatten_nested_params(params)
    assert result == {
        "kelly.cap_factor": 0.7,
        "kelly.min_trade": 20,
        "stop_loss.atr_multiplier": 2.0,
    }


def test_flatten_nested_params_empty():
    """Test flattening empty dict."""
    result = flatten_nested_params({})
    assert result == {}


def test_flatten_nested_params_non_dict_values():
    """Test that non-dict section values are skipped."""
    params = {
        "kelly": {"cap_factor": 0.7},
        "scalar_value": 42,  # Not a dict, should be skipped
    }
    result = flatten_nested_params(params)
    assert result == {"kelly.cap_factor": 0.7}


# =============================================================================
# Tests: extract_params_dotted
# =============================================================================

def test_extract_params_dotted_from_params_dotted():
    """Test extracting from params_dotted (priority 1)."""
    best_params = {
        "params_dotted": {"kelly.cap_factor": 0.05, "stop_loss.atr_multiplier": 1.5},
        "params": {"kelly": {"cap_factor": 0.99}},  # Should be ignored
    }
    result = extract_params_dotted(best_params)
    assert result == {"kelly.cap_factor": 0.05, "stop_loss.atr_multiplier": 1.5}


def test_extract_params_dotted_from_nested_params():
    """Test extracting from nested params when params_dotted is missing."""
    best_params = {
        "params": {"kelly": {"cap_factor": 0.05}, "stop_loss": {"atr_multiplier": 1.5}},
    }
    result = extract_params_dotted(best_params)
    assert result == {"kelly.cap_factor": 0.05, "stop_loss.atr_multiplier": 1.5}


def test_extract_params_dotted_empty_best_params():
    """Test extracting from empty best_params."""
    result = extract_params_dotted({})
    assert result == {}


def test_extract_params_dotted_empty_params_dotted():
    """Test that empty params_dotted falls back to params."""
    best_params = {
        "params_dotted": {},  # Empty, should fall back
        "params": {"kelly": {"cap_factor": 0.05}},
    }
    result = extract_params_dotted(best_params)
    assert result == {"kelly.cap_factor": 0.05}


def test_extract_params_dotted_none_params_dotted():
    """Test that None params_dotted falls back to params."""
    best_params = {
        "params_dotted": None,
        "params": {"kelly": {"cap_factor": 0.05}},
    }
    result = extract_params_dotted(best_params)
    assert result == {"kelly.cap_factor": 0.05}


def test_extract_params_dotted_both_empty():
    """Test that both empty returns empty dict."""
    best_params = {
        "params_dotted": {},
        "params": {},
    }
    result = extract_params_dotted(best_params)
    assert result == {}


def test_extract_params_dotted_only_meta():
    """Test best_params with only meta (no params)."""
    best_params = {
        "meta": {"generated_at": "2025-01-01"},
        "performance_snapshot": {"score": 1.0},
    }
    result = extract_params_dotted(best_params)
    assert result == {}
