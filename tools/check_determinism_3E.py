"""
tools/check_determinism_3E.py

Determinism gate for run_live_3E.py.
Executes the runner twice and compares outputs.
"""

import argparse
import sys
import subprocess
import shutil
import hashlib
import json
from pathlib import Path

def calculate_file_hash(path: Path) -> str:
    """Calculate SHA256 of a file."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()

def compare_json(path_a: Path, path_b: Path, ignored_keys=None) -> bool:
    """Compare two JSON files ignoring specific keys."""
    if ignored_keys is None:
        ignored_keys = []
        
    with open(path_a, "r", encoding="utf-8") as f:
        data_a = json.load(f)
    with open(path_b, "r", encoding="utf-8") as f:
        data_b = json.load(f)
        
    for k in ignored_keys:
        data_a.pop(k, None)
        data_b.pop(k, None)
        
    if data_a != data_b:
        print(f"Mismatch in {path_a.name}:")
        print(f"A: {data_a}")
        print(f"B: {data_b}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Determinism Checker 3E")
    
    parser.add_argument("--outdir-a", required=True, help="Dir for run A")
    parser.add_argument("--outdir-b", required=True, help="Dir for run B")
    parser.add_argument("--seed", default="42", help="Seed")
    parser.add_argument("--clock", default="simulated", help="Clock mode")
    parser.add_argument("--exchange", default="paper", help="Exchange mode")
    
    args = parser.parse_args()
    
    runner_script = Path(__file__).parent / "run_live_3E.py"
    if not runner_script.exists():
        print(f"Runner not found at {runner_script}")
        sys.exit(1)

    dir_a = Path(args.outdir_a)
    dir_b = Path(args.outdir_b)
    
    # Run A
    print(f"Running A -> {dir_a}")
    cmd_a = [sys.executable, str(runner_script), "--outdir", str(dir_a), "--seed", args.seed, "--clock", args.clock, "--exchange", args.exchange]
    subprocess.check_call(cmd_a)
    
    # Run B
    print(f"Running B -> {dir_b}")
    cmd_b = [sys.executable, str(runner_script), "--outdir", str(dir_b), "--seed", args.seed, "--clock", args.clock, "--exchange", args.exchange]
    subprocess.check_call(cmd_b)
    
    # Compare Artifacts
    artifacts = ["results.csv", "events.ndjson", "run_meta.json"]
    success = True
    
    for art in artifacts:
        path_a = dir_a / art
        path_b = dir_b / art
        
        if not path_a.exists() or not path_b.exists():
            print(f"Missing artifact {art}")
            success = False
            continue
            
        if art == "run_meta.json":
            # Semantic compare ignoring timestamps
            if not compare_json(path_a, path_b, ignored_keys=["timestamp_start"]):
                success = False
        else:
            # Hash compare
            hash_a = calculate_file_hash(path_a)
            hash_b = calculate_file_hash(path_b)
            if hash_a != hash_b:
                print(f"Hash mismatch for {art}: {hash_a} != {hash_b}")
                success = False
    
    if success:
        print("Determinism Verified: MATCH")
        sys.exit(0)
    else:
        print("Determinism Verified: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()
