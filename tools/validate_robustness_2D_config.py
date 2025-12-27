#!/usr/bin/env python
"""
tools/validate_robustness_2D_config.py

Validates robustness_2D.yaml configuration without running scenarios.

Usage:
    python tools/validate_robustness_2D_config.py
    python tools/validate_robustness_2D_config.py --config configs/robustness_2D.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# Required top-level keys
REQUIRED_KEYS = ["meta", "baseline", "engine", "risk_constraints", "sweep", "output", "scoring"]

# Required nested keys
REQUIRED_NESTED = {
    "meta": ["schema_version", "description"],
    "baseline": ["risk_rules_path", "candidate_params_path"],
    "engine": ["reproducibility", "modes"],
    "engine.reproducibility": ["default_seed", "seed_list"],
    "engine.modes": ["quick", "full"],
    "risk_constraints": ["gates"],
    "sweep": ["param_perturbations", "data_perturbations"],
    "output": ["directory", "files"],
    "scoring": ["enabled", "weights"],
}

# Valid ranges for numeric values
VALID_RANGES = {
    "engine.reproducibility.default_seed": (0, 2**31),
    "engine.modes.quick.max_scenarios": (1, 100),
    "engine.modes.full.max_scenarios": (1, 10000),
    "engine.modes.quick.timeout_minutes": (1, 60),
    "engine.modes.full.timeout_minutes": (1, 480),
    "scoring.weights.sharpe_ratio": (0, 10),
    "scoring.weights.cagr": (0, 10),
    "scoring.weights.max_drawdown_penalty": (0, 10),
}


def get_nested_value(data: dict, path: str) -> Any:
    """Get value from nested dict using dot notation."""
    keys = path.split(".")
    value = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def validate_required_keys(config: dict) -> list[str]:
    """Validate all required keys are present."""
    errors = []
    
    # Top-level keys
    for key in REQUIRED_KEYS:
        if key not in config:
            errors.append(f"Missing required top-level key: '{key}'")
    
    # Nested keys
    for parent, children in REQUIRED_NESTED.items():
        parent_value = get_nested_value(config, parent)
        if parent_value is None:
            continue  # Already reported as missing
        if not isinstance(parent_value, dict):
            errors.append(f"'{parent}' must be a dictionary")
            continue
        for child in children:
            if child not in parent_value:
                errors.append(f"Missing required key: '{parent}.{child}'")
    
    return errors


def validate_ranges(config: dict) -> list[str]:
    """Validate numeric values are within valid ranges."""
    errors = []
    
    for path, (min_val, max_val) in VALID_RANGES.items():
        value = get_nested_value(config, path)
        if value is None:
            continue  # Missing key, reported elsewhere
        if not isinstance(value, (int, float)):
            errors.append(f"'{path}' must be numeric, got {type(value).__name__}")
            continue
        if not (min_val <= value <= max_val):
            errors.append(f"'{path}' value {value} not in range [{min_val}, {max_val}]")
    
    return errors


def validate_seeds(config: dict) -> list[str]:
    """Validate seed configuration."""
    errors = []
    
    repro = get_nested_value(config, "engine.reproducibility")
    if repro is None:
        return errors
    
    default_seed = repro.get("default_seed")
    seed_list = repro.get("seed_list", [])
    
    if not isinstance(seed_list, list):
        errors.append("'engine.reproducibility.seed_list' must be a list")
        return errors
    
    if len(seed_list) == 0:
        errors.append("'engine.reproducibility.seed_list' cannot be empty")
    
    if default_seed is not None and default_seed not in seed_list:
        errors.append(f"default_seed {default_seed} not in seed_list")
    
    for i, seed in enumerate(seed_list):
        if not isinstance(seed, int):
            errors.append(f"seed_list[{i}] must be int, got {type(seed).__name__}")
    
    return errors


def validate_modes_coherence(config: dict) -> list[str]:
    """Validate quick mode is less intensive than full mode."""
    errors = []
    
    modes = get_nested_value(config, "engine.modes")
    if modes is None or not isinstance(modes, dict):
        return errors
    
    quick = modes.get("quick", {})
    full = modes.get("full", {})
    
    quick_scenarios = quick.get("max_scenarios", 0)
    full_scenarios = full.get("max_scenarios", 0)
    
    if quick_scenarios > full_scenarios:
        errors.append(
            f"quick.max_scenarios ({quick_scenarios}) > full.max_scenarios ({full_scenarios})"
        )
    
    quick_timeout = quick.get("timeout_minutes", 0)
    full_timeout = full.get("timeout_minutes", 0)
    
    if quick_timeout > full_timeout:
        errors.append(
            f"quick.timeout_minutes ({quick_timeout}) > full.timeout_minutes ({full_timeout})"
        )
    
    return errors


def validate_param_perturbations(config: dict) -> list[str]:
    """Validate parameter perturbation definitions."""
    errors = []
    
    perturbations = get_nested_value(config, "sweep.param_perturbations")
    if perturbations is None:
        return errors
    
    if not isinstance(perturbations, dict):
        errors.append("'sweep.param_perturbations' must be a dictionary")
        return errors
    
    for param_name, param_config in perturbations.items():
        if not isinstance(param_config, dict):
            errors.append(f"param_perturbations.{param_name} must be a dictionary")
            continue
        
        ptype = param_config.get("type")
        if ptype not in ("range", "list"):
            errors.append(f"param_perturbations.{param_name}.type must be 'range' or 'list'")
            continue
        
        if ptype == "range":
            for required in ("min", "max"):
                if required not in param_config:
                    errors.append(f"param_perturbations.{param_name} missing '{required}'")
            
            if "min" in param_config and "max" in param_config:
                if param_config["min"] > param_config["max"]:
                    errors.append(
                        f"param_perturbations.{param_name}: min > max"
                    )
    
    return errors


def validate_config(config_path: Path) -> tuple[list[str], list[str]]:
    """
    Validate robustness_2D.yaml configuration.
    
    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []
    
    # Load YAML
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"], []
    except FileNotFoundError:
        return [f"Config file not found: {config_path}"], []
    
    if config is None:
        return ["Empty config file"], []
    
    # Run all validations
    errors.extend(validate_required_keys(config))
    errors.extend(validate_ranges(config))
    errors.extend(validate_seeds(config))
    errors.extend(validate_modes_coherence(config))
    errors.extend(validate_param_perturbations(config))
    
    # Warnings
    if get_nested_value(config, "scoring.enabled") is False:
        warnings.append("Scoring is disabled")
    
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate robustness_2D.yaml configuration."
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default="configs/robustness_2D.yaml",
        help="Path to config file (default: configs/robustness_2D.yaml)",
    )
    
    args = parser.parse_args(argv)
    config_path = Path(args.config)
    
    print(f"Validating: {config_path}")
    print()
    
    errors, warnings = validate_config(config_path)
    
    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")
        print()
    
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
        print()
        print("VALIDATION FAILED")
        return 1
    
    print("✅ VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
