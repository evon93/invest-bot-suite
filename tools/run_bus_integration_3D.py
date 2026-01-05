"""
tools/run_bus_integration_3D.py

Bus integration runner for Phase 3D with strict risk rules validation.

Features:
- --risk-rules PATH: Path to risk rules YAML
- --strict-risk-config {0,1}: Fail-fast validation (default: 1)
- Generates run_meta.json with commit, python version, strict flag, risk_rules_path

Part of ticket AG-3D-1-1: Risk rules loading fail-fast (strict).
"""

import sys
import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from risk_rules_loader import load_risk_rules, validate_risk_rules_critical


def get_git_commit() -> str:
    """Get current git commit hash, or 'unknown' if not available."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:12]
    except Exception:
        pass
    return "unknown"


def get_python_version() -> str:
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def resolve_risk_rules_path(explicit_path: Optional[Path]) -> Path:
    """
    Resolve risk rules path with fallback logic.
    
    Priority:
    1. Explicit --risk-rules argument
    2. configs/risk_rules_prod.yaml (if exists)
    3. risk_rules.yaml (root)
    """
    if explicit_path:
        return explicit_path
    
    prod_path = PROJECT_ROOT / "configs" / "risk_rules_prod.yaml"
    if prod_path.exists():
        return prod_path
    
    default_path = PROJECT_ROOT / "risk_rules.yaml"
    return default_path


def run_3d_integration(
    risk_rules_path: Path,
    out_dir: Path,
    strict: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Run 3D integration with strict risk rules validation.
    
    Args:
        risk_rules_path: Path to risk rules YAML
        out_dir: Output directory
        strict: If True, validate critical keys before proceeding
        dry_run: If True, only validate and write meta (no actual simulation)
        
    Returns:
        Dict with run metadata
        
    Raises:
        ValueError: If strict=True and validation fails
    """
    # 1. Load risk rules
    rules = load_risk_rules(risk_rules_path)
    
    # 2. Validate if strict mode
    if strict:
        validate_risk_rules_critical(rules, path=risk_rules_path)
    
    # 3. Prepare output directory
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Build run metadata
    run_meta = {
        "commit": get_git_commit(),
        "python_version": get_python_version(),
        "strict_risk_config": strict,
        "risk_rules_path": str(risk_rules_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runner": "run_bus_integration_3D",
        "phase": "3D",
        "dry_run": dry_run,
    }
    
    # 5. Write run_meta.json
    meta_path = out_dir / "run_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2, sort_keys=True)
    
    run_meta["meta_path"] = str(meta_path)
    
    # 6. If not dry_run, would run actual simulation here
    # For now, this runner focuses on the validation + meta generation
    if not dry_run:
        # TODO: Integrate with LoopStepper or other simulation engine
        run_meta["note"] = "Simulation not implemented in this version (use --dry-run)"
    
    return run_meta


def main():
    parser = argparse.ArgumentParser(
        description="Run Bus Integration 3D (strict risk rules validation)"
    )
    parser.add_argument(
        "--risk-rules",
        type=Path,
        default=None,
        help="Path to risk rules YAML (default: configs/risk_rules_prod.yaml or risk_rules.yaml)"
    )
    parser.add_argument(
        "--strict-risk-config",
        type=int,
        choices=[0, 1],
        default=1,
        help="Fail-fast validation of critical keys (default: 1)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "report" / "out_3D1_failfast",
        help="Output directory (default: report/out_3D1_failfast)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate and write meta, skip simulation"
    )
    
    args = parser.parse_args()
    
    # Resolve risk rules path
    risk_rules_path = resolve_risk_rules_path(args.risk_rules)
    strict = bool(args.strict_risk_config)
    
    print(f"[3D Runner] Risk rules: {risk_rules_path}")
    print(f"[3D Runner] Strict mode: {strict}")
    print(f"[3D Runner] Output: {args.out}")
    
    try:
        result = run_3d_integration(
            risk_rules_path=risk_rules_path,
            out_dir=args.out,
            strict=strict,
            dry_run=args.dry_run,
        )
        print(f"[3D Runner] Success. Meta written to: {result.get('meta_path')}")
        return 0
    except ValueError as e:
        print(f"[3D Runner] ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
