#!/usr/bin/env python3
"""
tools/validate_local.py

Local validation harness for running gates and generating evidence artifacts.
Stdlib-only, no external dependencies.

AG-H5-1-1
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "report"


# Preset configurations
PRESETS = {
    "ci": {
        "cov_fail_under": 80,
        "gates": [
            {"name": "pytest_full", "cmd": ["python", "-m", "pytest", "-q"]},
            {
                "name": "coverage_gate",
                "cmd": [
                    "python", "-m", "pytest", "-q",
                    "--cov=engine", "--cov=tools",
                    "--cov-fail-under={cov_fail_under}",
                    "--cov-report=xml:report/coverage.xml",
                ],
            },
            {
                "name": "offline_integration",
                "cmd": ["python", "-m", "pytest", "-q", "tests/test_integration_offline_H3.py"],
                "env_extra": {"INVESTBOT_TEST_INTEGRATION_OFFLINE": "1"},
            },
        ],
    },
    "quick": {
        "cov_fail_under": 80,
        "gates": [
            {"name": "pytest_full", "cmd": ["python", "-m", "pytest", "-q"]},
        ],
    },
}


def get_git_info() -> dict:
    """Get current git branch and HEAD."""
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=10
        ).stdout.strip()
    except Exception:
        branch = "unknown"
    
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=REPO_ROOT, timeout=10
        ).stdout.strip()
    except Exception:
        head = "unknown"
    
    return {"branch": branch, "head": head}


def run_gate(gate_config: dict, cov_fail_under: int, log_dir: Path) -> dict:
    """Run a single gate and return result dict."""
    name = gate_config["name"]
    cmd = gate_config["cmd"].copy()
    
    # Substitute cov_fail_under in command
    cmd = [c.format(cov_fail_under=cov_fail_under) for c in cmd]
    
    # Prepare environment
    env = os.environ.copy()
    if "env_extra" in gate_config:
        env.update(gate_config["env_extra"])
    
    log_path = log_dir / f"{name}.log"
    
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            timeout=600,  # 10 min max per gate
        )
        rc = result.returncode
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        rc = -1
        output = "TIMEOUT after 600s"
    except Exception as e:
        rc = -2
        output = f"Exception: {e}"
    
    elapsed = time.perf_counter() - start
    
    # Write log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Command: {' '.join(cmd)}\n")
        f.write(f"Exit code: {rc}\n")
        f.write(f"Elapsed: {elapsed:.2f}s\n")
        f.write("-" * 60 + "\n")
        f.write(output)
    
    return {
        "name": name,
        "cmd": " ".join(cmd),
        "rc": rc,
        "elapsed_s": round(elapsed, 2),
        "status": "PASS" if rc == 0 else "FAIL",
        "log_path": str(log_path.relative_to(REPO_ROOT)),
    }


def main() -> int:
    """Main entry point. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Local validation harness for invest-bot-suite"
    )
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="ci",
        help="Preset configuration (default: ci)",
    )
    parser.add_argument(
        "--cov-fail-under",
        type=int,
        default=None,
        help="Override coverage threshold (default: from preset)",
    )
    parser.add_argument(
        "--out-prefix",
        default="validate_local_H51",
        help="Output file prefix (default: validate_local_H51)",
    )
    
    try:
        args = parser.parse_args()
    except SystemExit:
        return 2
    
    preset_config = PRESETS[args.preset]
    cov_fail_under = args.cov_fail_under or preset_config["cov_fail_under"]
    
    # Ensure report dir exists
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create temp log directory for gate outputs
    log_dir = REPORT_DIR / f"{args.out_prefix}_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Collect metadata
    git_info = get_git_info()
    iso_time = datetime.now(timezone.utc).isoformat()
    
    run_meta = {
        "iso_time": iso_time,
        "branch": git_info["branch"],
        "head": git_info["head"],
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "preset": args.preset,
        "cov_fail_under": cov_fail_under,
        "gates": [],
        "overall_status": "PASS",
        "elapsed_total_s": 0.0,
    }
    
    # Human-readable log
    human_log_lines = [
        f"validate_local.py — {iso_time}",
        f"Preset: {args.preset} | Coverage threshold: {cov_fail_under}%",
        f"Branch: {git_info['branch']} | HEAD: {git_info['head'][:12]}",
        "=" * 60,
        "",
    ]
    
    total_start = time.perf_counter()
    all_passed = True
    
    for gate_config in preset_config["gates"]:
        gate_result = run_gate(gate_config, cov_fail_under, log_dir)
        run_meta["gates"].append(gate_result)
        
        status_icon = "✓" if gate_result["status"] == "PASS" else "✗"
        human_log_lines.append(
            f"[{status_icon}] {gate_result['name']}: {gate_result['status']} "
            f"({gate_result['elapsed_s']:.1f}s)"
        )
        
        if gate_result["status"] != "PASS":
            all_passed = False
    
    total_elapsed = time.perf_counter() - total_start
    run_meta["elapsed_total_s"] = round(total_elapsed, 2)
    run_meta["overall_status"] = "PASS" if all_passed else "FAIL"
    
    human_log_lines.extend([
        "",
        "=" * 60,
        f"OVERALL: {run_meta['overall_status']} ({total_elapsed:.1f}s)",
    ])
    
    # Write outputs
    txt_path = REPORT_DIR / f"{args.out_prefix}.txt"
    json_path = REPORT_DIR / f"{args.out_prefix}_run_meta.json"
    
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(human_log_lines) + "\n")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(run_meta, f, indent=2, sort_keys=True)
    
    # Print summary to stdout
    print("\n".join(human_log_lines))
    print(f"\nArtifacts written:")
    print(f"  - {txt_path.relative_to(REPO_ROOT)}")
    print(f"  - {json_path.relative_to(REPO_ROOT)}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
