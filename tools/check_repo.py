#!/usr/bin/env python3
"""
check_repo.py - Script único de verificación del repositorio

Ejecuta:
1. pytest -q
2. python tools/validate_risk_config.py --config risk_rules.yaml
3. python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42

Devuelve exit code != 0 si algo falla.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _safe_print(text: str) -> None:
    """Print text safely, handling encoding errors for limited encodings like cp1252."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe)


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
        _safe_print(f"  {name}: {status}")
        if not success:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("ALL CHECKS PASSED")
        return 0
    else:
        print("SOME CHECKS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
