#!/usr/bin/env python3
"""
tools/pack_handoff.py

Deterministic ZIP packaging tool for handoff evidence files.
Generates sha256 manifest for reproducibility verification.

Stdlib-only, no external dependencies.

AG-H5-2-1
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "report"

# Fixed timestamp for deterministic ZIP (1980-01-01 00:00:00)
FIXED_ZIP_DATETIME = (1980, 1, 1, 0, 0, 0)

# Default exclusion patterns
DEFAULT_EXCLUDES = [
    "*.env",
    "**/secrets*",
    "credentials*",
    ".ssh",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".mypy_cache",
]

# Default files to include in handoff pack
DEFAULT_EVIDENCE_FILES = [
    "report/AG-H5-0-1_return.md",
    "report/head_mismatch_H50.md",
    "report/pytest_H50_snapshot.txt",
    "report/pytest_cov_H50_snapshot.txt",
    "report/AG-H5-1-1_return.md",
    "report/validate_local_H51.txt",
    "report/validate_local_H51_run_meta.json",
    "report/pytest_H51_postchange.txt",
    "registro_de_estado_invest_bot.md",
]


def sha256_file(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha512_file(path: Path) -> str:
    """Calculate SHA512 hash of a file."""
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# Import helper (package mode or script mode)
try:
    from tools._textio import safe_print
except ImportError:
    from _textio import safe_print


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


def is_excluded(rel_path: str, excludes: list) -> bool:
    """Check if path matches any exclusion pattern."""
    path_parts = rel_path.replace("\\", "/").split("/")
    
    for pattern in excludes:
        # Check full path
        if fnmatch(rel_path.replace("\\", "/"), pattern):
            return True
        # Check each component
        for part in path_parts:
            if fnmatch(part, pattern.replace("**/", "")):
                return True
    return False


def create_deterministic_zip(
    files: list[tuple[Path, str]],
    zip_path: Path,
) -> None:
    """Create a deterministic ZIP with fixed timestamps and sorted entries."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Sort by internal path for determinism
    sorted_files = sorted(files, key=lambda x: x[1])
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src_path, internal_path in sorted_files:
            # Read file content
            with open(src_path, "rb") as f:
                content = f.read()
            
            # Create ZipInfo with fixed timestamp
            info = zipfile.ZipInfo(filename=internal_path)
            info.date_time = FIXED_ZIP_DATETIME
            info.compress_type = zipfile.ZIP_DEFLATED
            
            zf.writestr(info, content)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pack handoff evidence files into a deterministic ZIP with manifest"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output ZIP path (default: report/archive/<date>_handoff/handoff_pack.zip)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Manifest JSON path (default: alongside ZIP)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y%m%d"),
        help="Date prefix for archive (default: today YYYYMMDD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without creating archive",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Override default evidence files (relative to repo root)",
    )
    parser.add_argument(
        "--sha512",
        action="store_true",
        help="Include SHA512 hashes in manifest (in addition to SHA256)",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    evidence_files = args.files if args.files else DEFAULT_EVIDENCE_FILES
    
    if args.out:
        zip_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    else:
        zip_path = REPORT_DIR / "archive" / f"{args.date}_handoff" / "handoff_pack.zip"
    
    if args.manifest:
        manifest_path = args.manifest if args.manifest.is_absolute() else REPO_ROOT / args.manifest
    else:
        manifest_path = zip_path.with_name("handoff_pack_manifest.json")
    
    log_path = REPORT_DIR / "pack_handoff_H52.txt"
    
    # Collect metadata
    git_info = get_git_info()
    iso_time = datetime.now(timezone.utc).isoformat()
    
    # Process files
    included = []
    warnings = []
    
    for rel_path_str in evidence_files:
        rel_path = rel_path_str.replace("\\", "/")
        abs_path = REPO_ROOT / rel_path
        
        if is_excluded(rel_path, DEFAULT_EXCLUDES):
            warnings.append(f"EXCLUDED: {rel_path}")
            continue
        
        if not abs_path.exists():
            warnings.append(f"MISSING: {rel_path}")
            continue
        
        if not abs_path.is_file():
            warnings.append(f"NOT_FILE: {rel_path}")
            continue
        
        # Calculate hash and size
        file_hash = sha256_file(abs_path)
        file_size = abs_path.stat().st_size
        
        entry = {
            "abs_path": abs_path,
            "rel_path": rel_path,
            "sha256": file_hash,
            "size_bytes": file_size,
        }
        
        # Add SHA512 if requested
        if args.sha512:
            entry["sha512"] = sha512_file(abs_path)
        
        included.append(entry)
    
    # Build manifest
    manifest = {
        "iso_time": iso_time,
        "branch": git_info["branch"],
        "head": git_info["head"],
        "python": sys.version.split()[0],
        "platform": platform.system(),
        "zip_path": str(zip_path.relative_to(REPO_ROOT)) if zip_path.is_relative_to(REPO_ROOT) else str(zip_path),
        "file_count": len(included),
        "sha512_enabled": args.sha512,
        "files": [
            {
                "rel_path": f["rel_path"],
                "sha256": f["sha256"],
                "size_bytes": f["size_bytes"],
                **({
                    "sha512": f["sha512"]
                } if "sha512" in f else {}),
            }
            for f in sorted(included, key=lambda x: x["rel_path"])
        ],
    }
    
    # Build human log
    log_lines = [
        f"pack_handoff.py — {iso_time}",
        f"Branch: {git_info['branch']} | HEAD: {git_info['head'][:12]}",
        "=" * 60,
        "",
        f"Files to include: {len(included)}",
    ]
    
    for f in sorted(included, key=lambda x: x["rel_path"]):
        log_lines.append(f"  ✓ {f['rel_path']} ({f['size_bytes']} bytes)")
    
    if warnings:
        log_lines.extend(["", "Warnings:"])
        for w in warnings:
            log_lines.append(f"  ⚠ {w}")
    
    log_lines.extend([
        "",
        "=" * 60,
    ])
    
    if args.dry_run:
        log_lines.append("DRY RUN — no files written")
        safe_print("\n".join(log_lines))
        return 0
    
    # Create ZIP
    files_for_zip = [(f["abs_path"], f["rel_path"]) for f in included]
    create_deterministic_zip(files_for_zip, zip_path)
    
    # Write manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    
    # Write log
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log_lines.extend([
        f"ZIP created: {zip_path.relative_to(REPO_ROOT)}",
        f"Manifest: {manifest_path.relative_to(REPO_ROOT)}",
        f"Total files: {len(included)}",
    ])
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines) + "\n")
    
    # Print summary
    safe_print("\n".join(log_lines))
    print(f"\nArtifacts written:")
    print(f"  - {zip_path.relative_to(REPO_ROOT)}")
    print(f"  - {manifest_path.relative_to(REPO_ROOT)}")
    print(f"  - {log_path.relative_to(REPO_ROOT)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
