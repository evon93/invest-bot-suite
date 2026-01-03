#!/usr/bin/env python3
"""
tools/run_e2e_2J.py

Canonical E2E Synthetic Runner for 2J Pipeline.
Executes the full risk pipeline in 'synth smoke' mode (determinism checked).

Pipeline Steps:
1. Calibration (run_calibration_2B.py) -> report/runs/2J_e2e_synth
2. Freeze (freeze_topk_2H.py) -> configs/best_params_2H.json
3. Render (render_risk_rules_prod.py) -> configs/risk_rules_prod.yaml
4. Validate (validate_risk_config.py) -> Strict Check (0 Errors, 0 Warnings)
5. Dashboard (build_dashboard.py) -> report/dashboard_2J
6. Robustness Check (validate_robustness_2D_config.py)
"""

import argparse
import platform
import subprocess
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT_DIR / "report" / "runs" / "2J_e2e_synth"
CONFIGS_DIR = ROOT_DIR / "configs"
REPORT_DIR = ROOT_DIR / "report"

def run_cmd(cmd: list, description: str, cwd: Path = ROOT_DIR, strict_output: bool = False):
    """Runs a command and optionally validates strict output requirements."""
    print(f"\n[2J-E2E] >>> {description}...")
    print(f"CMD: {' '.join(str(x) for x in cmd)}")
    
    # Validation steps need output capture for strict checks
    capture = strict_output or False
    
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            capture_output=capture,
            check=not strict_output # output checked manually if strict
        )
    except subprocess.CalledProcessError as e:
        print(f"Error executing {description}: {e}")
        sys.exit(1)

    if strict_output:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        
        if res.returncode != 0:
            print(f"❌ {description} failed with exit code {res.returncode}")
            sys.exit(res.returncode)
            
        # Strict validation logic for validate_risk_config
        if "Errors: 0" not in res.stdout or "Warnings: 0" not in res.stdout:
            print(f"❌ Strict validation FAILED. Expected 0 Errors and 0 Warnings.")
            sys.exit(1)
        else:
            print("✅ Strict validation PASSED (0 Errors, 0 Warnings).")
    else:
        # Popen/run passes output through if not captured
        pass

def main():
    parser = argparse.ArgumentParser(description="Run 2J E2E Synthetic Pipeline")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory for calibration run")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    parser.add_argument("--mode", choices=["quick", "full"], default="quick", 
                        help="Execution mode: quick (smoke) or full (full_demo)")
    parser.add_argument("--seed", default="42", help="Global seed for reproducibility")
    args = parser.parse_args()

    out_dir = args.outdir.resolve()
    
    # Artifacts
    results_agg = out_dir / "results_agg.csv"
    best_params_json = CONFIGS_DIR / "best_params_2H.json"
    topk_audit_json = REPORT_DIR / "topk_freeze_2H.json"
    risk_rules_prod = CONFIGS_DIR / "risk_rules_prod.yaml"
    dashboard_dir = REPORT_DIR / "dashboard_2J"

    # Map runner mode to calibration mode/profile
    # quick -> run_calibration_2B --mode quick
    # full  -> run_calibration_2B --mode full_demo (as per previous logic)
    calib_mode = "quick" if args.mode == "quick" else "full_demo"

    # Define Steps
    steps = []

    # 1. Calibration
    steps.append({
        "desc": f"Step 1: Calibration (2B) [Mode: {calib_mode}]",
        "cmd": [
            "python", "tools/run_calibration_2B.py",
            "--mode", calib_mode,
            "--output-dir", str(out_dir),
            "--seed", args.seed
        ]
    })

    # 2. Freeze
    steps.append({
        "desc": "Step 2: Freeze TopK (2H)",
        "cmd": [
            "python", "tools/freeze_topk_2H.py",
            "--results-agg", str(results_agg),
            "--out-config", str(best_params_json),
            "--out-report", str(topk_audit_json)
        ]
    })

    # 3. Render
    steps.append({
        "desc": "Step 3: Render Prod Config",
        "cmd": [
            "python", "tools/render_risk_rules_prod.py",
            "--base", "risk_rules.yaml",
            "--overlay", str(best_params_json),
            "--out", str(risk_rules_prod)
        ]
    })

    # 4. Validate (Strict)
    steps.append({
        "desc": "Step 4: Validate Prod Config (Strict)",
        "cmd": [
            "python", "tools/validate_risk_config.py",
            "--config", str(risk_rules_prod)
        ],
        "strict": True
    })

    # 5. Dashboard
    steps.append({
        "desc": "Step 5: Build Dashboard (2J)",
        "cmd": [
            "python", "tools/build_dashboard.py",
            "--run-dir", str(out_dir),
            "--out", str(dashboard_dir)
        ]
    })

    # 6. Robustness Config Check
    steps.append({
        "desc": "Step 6: Check Robustness Config (2D)",
        "cmd": [
            "python", "tools/validate_robustness_2D_config.py"
        ]
    })

    # Execution Loop
    for step in steps:
        if args.dry_run:
            print(f"[DRY-RUN] {step['desc']}: {' '.join(step['cmd'])}")
        else:
            run_cmd(step["cmd"], step["desc"], strict_output=step.get("strict", False))

    print("\n✅ E2E Pipeline Completed Successfully.")
    print(f"Artifacts:\n- {out_dir}\n- {best_params_json}\n- {risk_rules_prod}\n- {dashboard_dir}")

if __name__ == "__main__":
    if sys.platform == "win32":
        print("⚠️  Warning: Running on Windows native. Use WSL for canonical execution.", file=sys.stderr)
    main()
