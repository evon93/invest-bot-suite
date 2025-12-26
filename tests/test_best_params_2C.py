"""
Tests for best_params_2C schema and builder.
"""
import json
import pytest
from pathlib import Path

from tools.best_params_schema_2C import (
    validate_topk_payload,
    validate_candidate,
    dotted_to_nested,
    select_best_candidate,
)
from tools.build_best_params_2C import build_best_params


# === Test dotted_to_nested ===

def test_dotted_to_nested_conversion():
    """Test dotted keys are converted to nested structure."""
    dotted = {
        "stop_loss.atr_multiplier": 2.0,
        "stop_loss.min_stop_pct": 0.02,
        "max_drawdown.soft_limit_pct": 0.05,
        "max_drawdown.hard_limit_pct": 0.1,
        "kelly.cap_factor": 0.5,
    }
    result = dotted_to_nested(dotted)
    
    assert result == {
        "stop_loss": {
            "atr_multiplier": 2.0,
            "min_stop_pct": 0.02,
        },
        "max_drawdown": {
            "soft_limit_pct": 0.05,
            "hard_limit_pct": 0.1,
        },
        "kelly": {
            "cap_factor": 0.5,
        },
    }


# === Test selector ===

def _make_candidate(rank: int, score: float, combo_id: str = None) -> dict:
    """Helper to create a valid candidate."""
    return {
        "rank": rank,
        "combo_id": combo_id or f"combo_{rank}",
        "score": score,
        "sharpe_ratio": score * 0.8,
        "cagr": score * 0.1,
        "max_drawdown": -0.1,
        "calmar_ratio": score * 0.5,
        "params": {
            "stop_loss.atr_multiplier": 2.0,
            "stop_loss.min_stop_pct": 0.02,
            "max_drawdown.soft_limit_pct": 0.05,
            "max_drawdown.hard_limit_pct": 0.1,
            "max_drawdown.size_multiplier_soft": 0.5,
            "kelly.cap_factor": 0.7,
        },
    }


def test_select_best_by_rank_verified():
    """Test selection by verified rank 1."""
    candidates = [
        _make_candidate(1, 1.0),
        _make_candidate(2, 0.5),
        _make_candidate(3, 0.3),
    ]
    best, meta = select_best_candidate(candidates)
    
    assert best["rank"] == 1
    assert best["score"] == 1.0
    assert meta["selection_method"] == "rank_1_verified"


def test_rank_inconsistent_raises_without_force():
    """Test that inconsistent ranks raise ValueError without force."""
    candidates = [
        _make_candidate(1, 0.5),  # rank 1 but NOT max score
        _make_candidate(2, 1.0),  # higher score
    ]
    
    with pytest.raises(ValueError, match="Rank inconsistent"):
        select_best_candidate(candidates)


def test_rank_inconsistent_force_selects_sorted():
    """Test that force=True selects by sorted score despite rank."""
    candidates = [
        _make_candidate(1, 0.5),  # rank 1 but NOT max score
        _make_candidate(2, 1.0),  # higher score
    ]
    
    best, meta = select_best_candidate(candidates, force=True)
    
    assert best["score"] == 1.0
    assert best["rank"] == 2
    assert meta["selection_method"] == "force_score_sorted"


def test_no_candidate_score_above_eps_raises():
    """Test circuit breaker when no score > eps."""
    candidates = [
        _make_candidate(1, 0.0),
        _make_candidate(2, 0.0),
    ]
    
    with pytest.raises(ValueError, match="Circuit breaker"):
        select_best_candidate(candidates)


def test_allow_all_nonpositive_uses_tiebreakers():
    """Test that allow_all_nonpositive uses tiebreakers when all scores <= eps."""
    candidates = [
        _make_candidate(1, 0.0, "aaa"),
        _make_candidate(2, 0.0, "bbb"),
    ]
    # Make rank 2 have better sharpe
    candidates[1]["sharpe_ratio"] = 0.5
    
    best, meta = select_best_candidate(candidates, allow_all_nonpositive=True)
    
    # Should select rank 1 (verified) even though rank 2 has better sharpe
    # because rank is valid and coherent (both have same score)
    assert best["rank"] == 1
    assert meta["selection_method"] == "rank_1_verified"


def test_invalid_ranks_uses_sorted():
    """Test that invalid/missing ranks uses sorted selection."""
    candidates = [
        {"rank": None, "combo_id": "a", "score": 0.5, "sharpe_ratio": 0.4,
         "cagr": 0.1, "max_drawdown": -0.1, "calmar_ratio": 0.3,
         "params": _make_candidate(1, 1.0)["params"]},
        {"rank": None, "combo_id": "b", "score": 1.0, "sharpe_ratio": 0.8,
         "cagr": 0.1, "max_drawdown": -0.1, "calmar_ratio": 0.5,
         "params": _make_candidate(1, 1.0)["params"]},
    ]
    
    best, meta = select_best_candidate(candidates)
    
    assert best["score"] == 1.0
    assert best["combo_id"] == "b"
    assert meta["selection_method"] == "score_sorted_tiebreaker"


# === Test builder ===

def test_builder_writes_expected_shape(tmp_path: Path):
    """Test that builder writes JSON with expected structure."""
    # Create input topk.json
    topk = {
        "score_formula": "1.0*sharpe_ratio + 0.5*cagr",
        "top_k": 3,
        "candidates": [_make_candidate(1, 1.0, "test_combo")],
    }
    input_path = tmp_path / "topk.json"
    input_path.write_text(json.dumps(topk), encoding="utf-8")
    
    output_path = tmp_path / "output" / "best_params.json"
    
    payload = build_best_params(input_path, output_path)
    
    # Check file was written
    assert output_path.exists()
    
    # Check structure
    assert "meta" in payload
    assert "performance_snapshot" in payload
    assert "params" in payload
    assert "params_dotted" in payload
    
    # Check meta fields
    meta = payload["meta"]
    assert meta["source_combo_id"] == "test_combo"
    assert meta["selection_method"] == "rank_1_verified"
    assert meta["top_k"] == 3
    
    # Check params are nested
    assert "stop_loss" in payload["params"]
    assert "atr_multiplier" in payload["params"]["stop_loss"]


# === Test validators ===

def test_validate_topk_payload_valid():
    """Test valid payload passes validation."""
    topk = {
        "score_formula": "1.0*sharpe",
        "top_k": 5,
        "candidates": [{}],  # content doesn't matter here
    }
    errors = validate_topk_payload(topk)
    assert errors == []


def test_validate_topk_payload_invalid():
    """Test invalid payload returns errors."""
    topk = {
        "score_formula": "",  # empty
        "top_k": 0,  # invalid
        "candidates": [],  # empty
    }
    errors = validate_topk_payload(topk)
    assert len(errors) == 3


def test_validate_candidate_valid():
    """Test valid candidate passes validation."""
    c = _make_candidate(1, 1.0)
    errors = validate_candidate(c)
    assert errors == []


def test_validate_candidate_missing_params():
    """Test candidate with missing params fails."""
    c = {
        "combo_id": "test",
        "score": 1.0,
        "sharpe_ratio": 0.8,
        "cagr": 0.1,
        "max_drawdown": -0.1,
        "calmar_ratio": 0.5,
        "params": {},  # missing all
    }
    errors = validate_candidate(c)
    assert len(errors) >= 6  # at least 6 missing params
