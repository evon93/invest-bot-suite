#!/usr/bin/env python3
"""
tools/report_artifact_policy.py

Validate report/ artifacts against storage policy (AG-H1-1-1).

Features:
- Scan for files exceeding size thresholds
- Validate allowlist exceptions
- Generate SHA256 digest for large files
- Exit code != 0 if policy violations found (CI gate)

Usage:
    python tools/report_artifact_policy.py --check          # Validate (default)
    python tools/report_artifact_policy.py --digest FILE    # Generate digest
"""

import argparse
import hashlib
import sys
from pathlib import Path
from typing import List, Tuple

# Size thresholds (bytes)
WARNING_THRESHOLD = 1 * 1024 * 1024   # 1 MB
BLOCK_THRESHOLD = 5 * 1024 * 1024     # 5 MB

# Patterns that are ALLOWED to be large (tracked in git)
ALLOWLIST_PATTERNS = [
    "*_return.md",
    "*_last_commit.txt",
    "*_notes.md",
    "bridge_*_report.md",
    "ORCH_HANDOFF_*.md",
]

# Patterns that should go to CI artifacts (ignored in git)
CI_ARTIFACT_PATTERNS = [
    "*_diff.patch",
    "*_run.txt",
    "*_run_*.txt",
    "pytest_*.txt",
    "runs/**",
    "out_*/**",
]


def matches_any(name: str, patterns: List[str]) -> bool:
    """Check if name matches any glob pattern."""
    import fnmatch
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def get_sha256(path: Path, first_bytes: int = 0) -> str:
    """Calculate SHA256 hash of file (or first N bytes)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        if first_bytes > 0:
            h.update(f.read(first_bytes))
        else:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    return h.hexdigest()


def generate_digest(path: Path) -> dict:
    """Generate metadata digest for a file."""
    stat = path.stat()
    sha = get_sha256(path)
    
    # Get first/last lines for text files
    first_lines = []
    last_lines = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            first_lines = [l.rstrip() for l in lines[:5]]
            last_lines = [l.rstrip() for l in lines[-5:]]
    except Exception:
        pass
    
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "sha256": sha,
        "first_lines": first_lines,
        "last_lines": last_lines,
    }


def check_policy(report_dir: Path) -> Tuple[List[dict], List[dict]]:
    """
    Check files against policy.
    
    Returns:
        (warnings, errors) - lists of violation dicts
    """
    warnings = []
    errors = []
    
    for path in report_dir.rglob("*"):
        if not path.is_file():
            continue
        
        rel_path = path.relative_to(report_dir)
        name = path.name
        size = path.stat().st_size
        
        # Skip allowlisted
        if matches_any(name, ALLOWLIST_PATTERNS):
            continue
        
        # Check thresholds
        if size >= BLOCK_THRESHOLD:
            errors.append({
                "path": str(rel_path),
                "size_mb": size / (1024 * 1024),
                "reason": "exceeds_block_threshold",
            })
        elif size >= WARNING_THRESHOLD:
            warnings.append({
                "path": str(rel_path),
                "size_mb": size / (1024 * 1024),
                "reason": "exceeds_warning_threshold",
            })
    
    return warnings, errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate report/ artifacts against storage policy"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        default=True,
        help="Check policy (default)",
    )
    parser.add_argument(
        "--digest",
        type=Path,
        metavar="FILE",
        help="Generate digest for specific file",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Path to report/ (auto-detect if not specified)",
    )
    
    args = parser.parse_args()
    
    # Determine report directory
    if args.report_dir:
        report_dir = args.report_dir
    else:
        script_dir = Path(__file__).parent
        report_dir = script_dir.parent / "report"
    
    # Digest mode
    if args.digest:
        if not args.digest.exists():
            print(f"ERROR: File not found: {args.digest}", file=sys.stderr)
            return 1
        
        import json
        digest = generate_digest(args.digest)
        print(json.dumps(digest, indent=2))
        return 0
    
    # Check mode
    if not report_dir.is_dir():
        print(f"ERROR: report/ not found: {report_dir}", file=sys.stderr)
        return 1
    
    warnings, errors = check_policy(report_dir)
    
    print(f"=== Report Artifact Policy Check ===")
    print(f"Directory: {report_dir}")
    print(f"Thresholds: warn={WARNING_THRESHOLD // (1024*1024)}MB, block={BLOCK_THRESHOLD // (1024*1024)}MB")
    print()
    
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w['path']}: {w['size_mb']:.2f} MB")
    
    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e['path']}: {e['size_mb']:.2f} MB - EXCEEDS BLOCK THRESHOLD")
    
    if not warnings and not errors:
        print("OK: No policy violations found")
        return 0
    
    if errors:
        print(f"\nFAILED: {len(errors)} file(s) exceed block threshold")
        return 1
    
    print(f"\nPASSED with warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
