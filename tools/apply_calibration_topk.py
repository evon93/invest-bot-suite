#!/usr/bin/env python3
"""
Apply best params from calibration to risk_rules.yaml.

Generates risk_rules_candidate.yaml with updated params.
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


# Paths to apply from best_params (nested structure)
APPLY_PATHS = [
    ("stop_loss", "atr_multiplier"),
    ("stop_loss", "min_stop_pct"),
    ("max_drawdown", "soft_limit_pct"),
    ("max_drawdown", "hard_limit_pct"),
    ("max_drawdown", "size_multiplier_soft"),
    ("kelly", "cap_factor"),
]


def load_best_params(path: Path) -> dict:
    """Load and validate best_params JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Validate minimal structure
    if "params" not in data:
        raise ValueError("best_params missing 'params' key")
    
    params = data["params"]
    for section, key in APPLY_PATHS:
        if section not in params:
            raise ValueError(f"best_params missing section: {section}")
        if key not in params[section]:
            raise ValueError(f"best_params missing key: {section}.{key}")
    
    return data


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_params(params: dict) -> list[str]:
    """Validate param values are in valid ranges."""
    errors = []
    
    sl = params.get("stop_loss", {})
    md = params.get("max_drawdown", {})
    k = params.get("kelly", {})
    
    # atr_multiplier > 0
    atr = sl.get("atr_multiplier")
    if atr is not None and atr <= 0:
        errors.append(f"atr_multiplier must be > 0, got {atr}")
    
    # min_stop_pct in (0, 1)
    msp = sl.get("min_stop_pct")
    if msp is not None and not (0 < msp < 1):
        errors.append(f"min_stop_pct must be in (0, 1), got {msp}")
    
    # soft_limit_pct in (0, 1)
    soft = md.get("soft_limit_pct")
    if soft is not None and not (0 < soft < 1):
        errors.append(f"max_drawdown.soft_limit_pct must be in (0, 1), got {soft}")
    
    # hard_limit_pct in (0, 1)
    hard = md.get("hard_limit_pct")
    if hard is not None and not (0 < hard < 1):
        errors.append(f"max_drawdown.hard_limit_pct must be in (0, 1), got {hard}")
    
    # hard >= soft
    if soft is not None and hard is not None and hard < soft:
        errors.append(f"hard_limit_pct ({hard}) must be >= soft_limit_pct ({soft})")
    
    # size_multiplier_soft in [0, 1]
    sms = md.get("size_multiplier_soft")
    if sms is not None and not (0 <= sms <= 1):
        errors.append(f"size_multiplier_soft must be in [0, 1], got {sms}")
    
    # cap_factor in [0, 1]
    cf = k.get("cap_factor")
    if cf is not None and not (0 <= cf <= 1):
        errors.append(f"kelly.cap_factor must be in [0, 1], got {cf}")
    
    return errors


def apply_params(base: dict, new_params: dict) -> tuple[dict, list[tuple[str, Any, Any]]]:
    """
    Apply new params to base config.
    
    Returns (updated_config, list of (path, old_value, new_value)).
    """
    import copy
    result = copy.deepcopy(base)
    changes = []
    
    for section, key in APPLY_PATHS:
        if section not in result:
            raise ValueError(f"Base YAML missing section: {section}")
        if key not in result[section]:
            raise ValueError(f"Base YAML missing key: {section}.{key}")
        
        old_val = result[section][key]
        new_val = new_params[section][key]
        
        if old_val != new_val:
            changes.append((f"{section}.{key}", old_val, new_val))
            result[section][key] = new_val
    
    return result, changes


def generate_patch(base_path: Path, candidate_path: Path, patch_path: Path) -> bool:
    """
    Generate unified diff patch.
    
    Returns True if diff was generated, False if files are identical.
    """
    # Try git diff --no-index first
    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--no-color", 
             str(base_path), str(candidate_path)],
            capture_output=True,
            text=True,
        )
        # git diff --no-index returns 1 if different, 0 if same
        if result.returncode == 0:
            # Files identical
            patch_path.write_text("# No differences\n", encoding="utf-8")
            return False
        else:
            patch_path.write_text(result.stdout, encoding="utf-8")
            return True
    except Exception:
        # Fallback to difflib
        base_lines = base_path.read_text(encoding="utf-8").splitlines(keepends=True)
        cand_lines = candidate_path.read_text(encoding="utf-8").splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            base_lines, cand_lines,
            fromfile=str(base_path),
            tofile=str(candidate_path),
        )
        diff_text = "".join(diff)
        
        if not diff_text:
            patch_path.write_text("# No differences\n", encoding="utf-8")
            return False
        
        patch_path.write_text(diff_text, encoding="utf-8")
        return True


def apply_calibration(
    best_path: Path,
    base_path: Path,
    out_path: Path,
    patch_path: Path | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict:
    """
    Apply calibration params to base YAML.
    
    Returns the applied changes summary.
    """
    # Load inputs
    best_data = load_best_params(best_path)
    new_params = best_data["params"]
    base = load_yaml(base_path)
    
    # Validate
    errors = validate_params(new_params)
    if errors:
        raise ValueError(f"Invalid params: {errors}")
    
    # Apply
    result, changes = apply_params(base, new_params)
    
    if verbose:
        print(f"Applying {len(changes)} changes:")
        for path, old, new in changes:
            print(f"  {path}: {old} -> {new}")
    
    if dry_run:
        print("Dry run - not writing files")
    else:
        # Write candidate YAML
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use yaml.dump with default_flow_style=False for readability
        yaml_content = yaml.dump(result, default_flow_style=False, 
                                  allow_unicode=True, sort_keys=False)
        
        # Check idempotence
        if out_path.exists():
            existing = out_path.read_text(encoding="utf-8")
            if existing == yaml_content:
                if verbose:
                    print(f"Output unchanged, skipping write: {out_path}")
            else:
                out_path.write_text(yaml_content, encoding="utf-8")
                if verbose:
                    print(f"Written: {out_path}")
        else:
            out_path.write_text(yaml_content, encoding="utf-8")
            if verbose:
                print(f"Written: {out_path}")
        
        # Generate patch
        if patch_path:
            has_diff = generate_patch(base_path, out_path, patch_path)
            if verbose:
                print(f"Patch: {patch_path} ({'has changes' if has_diff else 'no changes'})")
    
    return {
        "changes": changes,
        "source_combo_id": best_data.get("meta", {}).get("source_combo_id"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply calibration best params to risk_rules.yaml"
    )
    parser.add_argument(
        "--best",
        type=Path,
        default=Path("configs/best_params_2C.json"),
        help="Path to best_params JSON",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("risk_rules.yaml"),
        help="Path to base risk_rules YAML",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("risk_rules_candidate.yaml"),
        help="Path to output candidate YAML",
    )
    parser.add_argument(
        "--patch",
        type=Path,
        default=None,
        help="Path to write diff patch",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write files, just print changes",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    try:
        result = apply_calibration(
            args.best,
            args.base,
            args.out,
            args.patch,
            dry_run=args.dry_run,
            verbose=args.verbose or args.dry_run,
        )
        if args.verbose or args.dry_run:
            print(f"Applied {len(result['changes'])} changes from {result['source_combo_id']}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
