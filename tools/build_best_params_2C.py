#!/usr/bin/env python3
"""
CLI Builder for best_params_2C.json.

Reads topk.json, validates, selects best candidate, and writes normalized output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.best_params_schema_2C import (
    validate_topk_payload,
    validate_candidate,
    dotted_to_nested,
    select_best_candidate,
)


def get_git_head() -> str:
    """Get current git HEAD commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def compute_sha256(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def build_best_params(
    input_path: Path,
    output_path: Path,
    *,
    eps: float = 1e-4,
    force: bool = False,
    allow_all_nonpositive: bool = False,
    print_selection: bool = False,
) -> dict:
    """
    Build best_params_2C.json from topk.json.
    
    Returns the generated payload dict.
    """
    # Load input
    with open(input_path, "r", encoding="utf-8") as f:
        raw_content = f.read()
        topk = json.loads(raw_content)
    
    # Validate root
    root_errors = validate_topk_payload(topk)
    if root_errors:
        raise ValueError(f"Invalid topk payload: {root_errors}")
    
    # Validate all candidates
    candidates = topk["candidates"]
    all_errors = []
    for i, c in enumerate(candidates):
        errs = validate_candidate(c)
        if errs:
            all_errors.append(f"Candidate {i} ({c.get('combo_id', '?')}): {errs}")
    
    if all_errors:
        raise ValueError(f"Invalid candidates:\n" + "\n".join(all_errors))
    
    # Select best
    best, selection_meta = select_best_candidate(
        candidates,
        eps=eps,
        force=force,
        allow_all_nonpositive=allow_all_nonpositive,
    )
    
    if print_selection:
        print(f"Selected: rank={best.get('rank')}, combo_id={best.get('combo_id')}")
        print(f"  score={best.get('score'):.6f}")
        print(f"  method={selection_meta.get('selection_method')}")
    
    # Build output payload
    params_dotted = best["params"]
    params_nested = dotted_to_nested(params_dotted)
    
    payload = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_head": get_git_head(),
            "source_file": str(input_path),
            "source_combo_id": best["combo_id"],
            "selected_rank": best.get("rank"),
            "selection_method": selection_meta["selection_method"],
            "seed": 42,
            "top_k": topk["top_k"],
            "topk_sha256": compute_sha256(raw_content),
            "score_formula": topk["score_formula"],
        },
        "performance_snapshot": {
            "score": best.get("score", 0.0),
            "sharpe_ratio": best.get("sharpe_ratio", 0.0),
            "cagr": best.get("cagr", 0.0),
            "max_drawdown": best.get("max_drawdown", 0.0),
            "calmar_ratio": best.get("calmar_ratio", 0.0),
        },
        "params": params_nested,
        "params_dotted": params_dotted,
    }
    
    # Write output (idempotent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    new_content = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    
    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        # Compare ignoring meta.generated_at for idempotence
        existing_payload = json.loads(existing)
        existing_payload.get("meta", {}).pop("generated_at", None)
        new_payload_cmp = json.loads(new_content)
        new_payload_cmp.get("meta", {}).pop("generated_at", None)
        
        if existing_payload == new_payload_cmp:
            if print_selection:
                print(f"Output unchanged, skipping write: {output_path}")
            return payload
    
    output_path.write_text(new_content, encoding="utf-8")
    if print_selection:
        print(f"Written: {output_path}")
    
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build best_params_2C.json from topk.json"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("report/calibration_2B/topk.json"),
        help="Input topk.json path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("configs/best_params_2C.json"),
        help="Output best_params path",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=1e-4,
        help="Threshold for positive score",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force selection by score when rank is inconsistent",
    )
    parser.add_argument(
        "--allow-all-nonpositive",
        action="store_true",
        help="Allow selection when all scores <= eps",
    )
    parser.add_argument(
        "--print",
        dest="print_selection",
        action="store_true",
        help="Print selection details",
    )
    
    args = parser.parse_args()
    
    try:
        build_best_params(
            args.input,
            args.output,
            eps=args.eps,
            force=args.force,
            allow_all_nonpositive=args.allow_all_nonpositive,
            print_selection=args.print_selection,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
