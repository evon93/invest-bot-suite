#!/usr/bin/env python3
"""
check_repo.py - Script único de verificación del repositorio

Ejecuta:
1. pytest -q
2. python tools/validate_risk_config.py --config risk_rules.yaml
3. python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42

Devuelve exit code != 0 si algo falla.
"""

import fnmatch
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import helper (package mode or script mode)
try:
    from tools._textio import safe_print
except ImportError:
    from _textio import safe_print

# AG-H0-2-1: Patterns for volatile report files (should be ignored, not tracked)
VOLATILE_PATTERNS = [
    "report/out_*/**",
    "report/calibration_2B/results.csv",
    "report/calibration_2B/run_*.txt",
    "report/calibration_2B/run_meta.json",
    "report/calibration_2B/topk.json",
    "report/calibration_results_2B.csv",
    "report/pytest_*.txt",
    "report/git_status_*.txt",
    "report/head_*.txt",
    "report/smoke_*.txt",
    "report/runs/**",
]


def run_cmd(cmd: list[str], name: str) -> tuple[bool, str]:
    """Ejecuta comando y retorna (success, output)."""
    print(f"\n{'='*60}")
    print(f"[CHECK] {name}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        
        # Para pytest, verificar que hay "passed" en output
        if "pytest" in cmd[1] if len(cmd) > 1 else False:
            success = "passed" in output and "failed" not in output.lower()
        
        # Para validate_risk_config, verificar Errors: 0
        if "validate_risk_config" in str(cmd):
            success = "Errors: 0" in output
        
        # Para calibration, verificar que no hay errores fatales
        if "run_calibration" in str(cmd):
            success = "ok" in output.lower() and "error" not in result.stderr.lower()
        
        print(output[:2000] if len(output) > 2000 else output)
        return success, output
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {name}")
        return False, "TIMEOUT"
    except Exception as e:
        print(f"[ERROR] {name}: {e}")
        return False, str(e)


def check_volatile_report_files() -> list[str]:
    """Check for modified volatile files in report/ that are tracked. Returns warnings."""
    warnings = []
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "report/"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        if result.returncode != 0:
            return []
        
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            # Format: " M path" or "M  path" etc.
            status = line[:2]
            filepath = line[3:].strip()
            
            # Check if modified file matches volatile pattern
            for pattern in VOLATILE_PATTERNS:
                if fnmatch.fnmatch(filepath, pattern):
                    warnings.append(f"{filepath} (matches {pattern})")
                    break
    except Exception:
        pass  # Non-critical check
    return warnings


def main():
    print("=" * 60)
    print("REPOSITORY VERIFICATION SCRIPT")
    print("=" * 60)
    
    checks = [
        ([sys.executable, "-m", "pytest", "-q"], "pytest"),
        ([sys.executable, "tools/validate_risk_config.py", "--config", "risk_rules.yaml"], "validate_risk_config"),
        ([sys.executable, "tools/run_calibration_2B.py", "--mode", "quick", "--max-combinations", "3", "--seed", "42"], "calibration_2B"),
    ]
    
    results = []
    for cmd, name in checks:
        success, _ = run_cmd(cmd, name)
        results.append((name, success))
    
    # Resumen
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        safe_print(f"  {name}: {status}")
        if not success:
            all_passed = False
    
    # AG-H0-2-1: Check for volatile tracked files (WARN only)
    volatile_warnings = check_volatile_report_files()
    if volatile_warnings:
        print("\n" + "=" * 60)
        print("[WARN] VOLATILE TRACKED FILES MODIFIED")
        print("=" * 60)
        print("The following volatile files are tracked and modified:")
        for w in volatile_warnings[:10]:  # Limit output
            safe_print(f"  - {w}")
        if len(volatile_warnings) > 10:
            print(f"  ... and {len(volatile_warnings) - 10} more")
        print("Consider: git rm --cached <file> or update .gitignore")
    
    print("\n" + "=" * 60)
    if all_passed:
        if volatile_warnings:
            print("ALL CHECKS PASSED (with volatile file warnings)")
        else:
            print("ALL CHECKS PASSED")
        return 0
    else:
        print("SOME CHECKS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
