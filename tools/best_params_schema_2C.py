"""
Best Params Schema & Selector for 2C.

Validates topk.json payloads and selects best candidate deterministically.
"""
from __future__ import annotations

import math
from typing import Any

# Required dotted param keys with their validation rules
REQUIRED_DOTTED_PARAMS = {
    "stop_loss.atr_multiplier": lambda v: isinstance(v, (int, float)) and v > 0,
    "stop_loss.min_stop_pct": lambda v: isinstance(v, (int, float)) and 0 < v < 1,
    "max_drawdown.soft_limit_pct": lambda v: isinstance(v, (int, float)) and 0 < v < 1,
    "max_drawdown.hard_limit_pct": lambda v: isinstance(v, (int, float)) and 0 < v < 1,
    "max_drawdown.size_multiplier_soft": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
    "kelly.cap_factor": lambda v: isinstance(v, (int, float)) and 0 <= v <= 1,
}

REQUIRED_METRICS = ["sharpe_ratio", "cagr", "max_drawdown", "calmar_ratio"]


def _is_finite(v: Any) -> bool:
    """Check if value is a finite float/int."""
    return isinstance(v, (int, float)) and math.isfinite(v)


def validate_topk_payload(topk: dict) -> list[str]:
    """
    Validate root-level structure of topk.json.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    # score_formula
    sf = topk.get("score_formula")
    if not isinstance(sf, str) or not sf.strip():
        errors.append("score_formula must be a non-empty string")
    
    # top_k
    tk = topk.get("top_k")
    if not isinstance(tk, int) or tk < 1:
        errors.append("top_k must be an integer >= 1")
    
    # candidates
    cands = topk.get("candidates")
    if not isinstance(cands, list) or len(cands) == 0:
        errors.append("candidates must be a non-empty list")
    
    return errors


def validate_candidate(c: dict) -> list[str]:
    """
    Validate a single candidate entry.
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    
    # combo_id
    cid = c.get("combo_id")
    if not isinstance(cid, str) or not cid.strip():
        errors.append("combo_id must be a non-empty string")
    
    # params dict
    params = c.get("params")
    if not isinstance(params, dict):
        errors.append("params must be a dict")
    else:
        # Validate each required dotted param
        for key, validator in REQUIRED_DOTTED_PARAMS.items():
            val = params.get(key)
            if val is None:
                errors.append(f"params missing required key: {key}")
            elif not validator(val):
                errors.append(f"params.{key} invalid value: {val}")
        
        # Check hard >= soft for drawdown
        soft = params.get("max_drawdown.soft_limit_pct")
        hard = params.get("max_drawdown.hard_limit_pct")
        if isinstance(soft, (int, float)) and isinstance(hard, (int, float)):
            if hard < soft:
                errors.append(
                    f"max_drawdown.hard_limit_pct ({hard}) must be >= soft_limit_pct ({soft})"
                )
    
    # Metrics: must be finite floats
    for metric in REQUIRED_METRICS:
        val = c.get(metric)
        if not _is_finite(val):
            errors.append(f"{metric} must be a finite number, got: {val}")
    
    # max_drawdown must be <= 0
    md = c.get("max_drawdown")
    if _is_finite(md) and md > 0:
        errors.append(f"max_drawdown must be <= 0, got: {md}")
    
    return errors


def dotted_to_nested(dotted: dict) -> dict:
    """
    Convert dotted keys to nested dict structure.
    
    Example:
        {"stop_loss.atr_multiplier": 2.0} -> {"stop_loss": {"atr_multiplier": 2.0}}
    """
    result: dict = {}
    for key, value in dotted.items():
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def select_best_candidate(
    candidates: list[dict],
    *,
    eps: float = 1e-4,
    force: bool = False,
    allow_all_nonpositive: bool = False,
) -> tuple[dict, dict]:
    """
    Select best candidate deterministically.
    
    Args:
        candidates: List of candidate dicts from topk.json
        eps: Threshold for considering score as positive
        force: If True, use sorted selection even when rank is inconsistent
        allow_all_nonpositive: If True, allow selection when all scores <= eps
    
    Returns:
        Tuple of (best_candidate, selection_meta)
    
    Raises:
        ValueError: If no valid candidate can be selected (circuit breaker)
    """
    if not candidates:
        raise ValueError("No candidates provided")
    
    # Filter candidates with finite scores
    valid = [c for c in candidates if _is_finite(c.get("score"))]
    if not valid:
        raise ValueError("No candidates with finite score")
    
    # Check if any score > eps
    has_positive_score = any(c["score"] > eps for c in valid)
    
    if not has_positive_score and not allow_all_nonpositive:
        raise ValueError(
            f"Circuit breaker: no candidate has score > {eps}. "
            "Use allow_all_nonpositive=True to override."
        )
    
    # Check if ranks are valid
    ranks = [c.get("rank") for c in valid]
    ranks_valid = (
        all(isinstance(r, int) and r > 0 for r in ranks)
        and len(set(ranks)) == len(ranks)  # unique
        and min(ranks) == 1
    )
    
    selection_meta: dict = {}
    
    if ranks_valid:
        # Find rank 1
        rank1 = next((c for c in valid if c["rank"] == 1), None)
        if rank1 is None:
            raise ValueError("Rank 1 not found despite valid ranks")
        
        # Check if rank1 has score > eps
        if rank1["score"] <= eps and not allow_all_nonpositive:
            raise ValueError(
                f"Rank 1 has score <= {eps} ({rank1['score']}). "
                "Use allow_all_nonpositive=True to override."
            )
        
        # Verify coherence: rank1.score should be max(score)
        max_score = max(c["score"] for c in valid)
        score_diff = abs(rank1["score"] - max_score)
        
        if score_diff > eps:
            # Rank inconsistent with scores
            if not force:
                raise ValueError(
                    f"Rank inconsistent: rank1.score={rank1['score']:.6f} "
                    f"but max(score)={max_score:.6f}. Use force=True to override."
                )
            # Force: select by sorted scores
            sorted_cands = _sort_candidates(valid)
            best = sorted_cands[0]
            selection_meta = {
                "selection_method": "force_score_sorted",
                "warning": "rank was inconsistent with scores",
            }
        else:
            # Coherent: select rank 1
            best = rank1
            selection_meta = {"selection_method": "rank_1_verified"}
    else:
        # Ranks invalid/absent: sort by tiebreakers
        sorted_cands = _sort_candidates(valid)
        best = sorted_cands[0]
        selection_meta = {"selection_method": "score_sorted_tiebreaker"}
    
    selection_meta["selected_rank"] = best.get("rank")
    selection_meta["selected_combo_id"] = best.get("combo_id")
    selection_meta["selected_score"] = best.get("score")
    
    return best, selection_meta


def _sort_candidates(candidates: list[dict]) -> list[dict]:
    """
    Sort candidates by: score desc, sharpe desc, cagr desc, 
    calmar desc, max_drawdown desc (closer to 0), combo_id asc.
    """
    def sort_key(c: dict) -> tuple:
        return (
            -c.get("score", float("-inf")),
            -c.get("sharpe_ratio", float("-inf")),
            -c.get("cagr", float("-inf")),
            -c.get("calmar_ratio", float("-inf")),
            -c.get("max_drawdown", float("-inf")),  # closer to 0 is better
            c.get("combo_id", ""),
        )
    return sorted(candidates, key=sort_key)
