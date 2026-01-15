#!/usr/bin/env python3
"""
cleanup_report.py — Cleanup ephemeral files in report/

Usage:
    python tools/cleanup_report.py --dry-run          # List candidates (default)
    python tools/cleanup_report.py --apply            # Delete ephemeral files
    python tools/cleanup_report.py --apply --days 14  # Only files older than 14 days

Ticket: AG-H0-1-1
"""

import argparse
import fnmatch
import os
import sys
import time
from pathlib import Path

# Ephemeral patterns (Tier 2) - eligible for cleanup
EPHEMERAL_PATTERNS = [
    # Files
    "git_status_*.txt",
    "head_*.txt",
    "origin_main_*.txt",
    "pytest_*_snapshot.txt",
    "python_*.txt",
    "smoke_*.txt",
    "ls_out_*.txt",
    "working_tree_diff_*.txt",
    "ahead_*.txt",
    "ffonly_*.txt",
    "log_graph_*.txt",
    "session_*.txt",
    "session_*.md",
    "os_release_*.txt",
    "remote_*.txt",
    "untracked_count_*.txt",
    "help_*.txt",
    "contains_*.txt",
    "in_main_*.txt",
    "delta_*.md",
    "git_show_*.txt",
    "python_venv_*.txt",
    "python_exe_*.txt",
]

# Ephemeral directories (Tier 2)
EPHEMERAL_DIR_PATTERNS = [
    "det_*",
    "det_close_*",
]


def is_ephemeral_file(name: str) -> bool:
    """Check if filename matches ephemeral patterns."""
    for pattern in EPHEMERAL_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def is_ephemeral_dir(name: str) -> bool:
    """Check if directory name matches ephemeral patterns."""
    for pattern in EPHEMERAL_DIR_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def get_mtime_days(path: Path) -> float:
    """Return age of file in days."""
    try:
        mtime = path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / 86400.0
    except OSError:
        return 0.0


def get_dir_size(path: Path) -> int:
    """Return total size of directory in bytes."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except OSError:
        pass
    return total


def find_candidates(report_dir: Path, min_age_days: int) -> tuple[list[Path], list[Path]]:
    """
    Find ephemeral files and directories eligible for cleanup.
    
    Returns:
        (files, dirs) - lists of Path objects
    """
    files = []
    dirs = []

    for entry in report_dir.iterdir():
        if entry.is_file() and is_ephemeral_file(entry.name):
            if get_mtime_days(entry) >= min_age_days:
                files.append(entry)
        elif entry.is_dir() and is_ephemeral_dir(entry.name):
            # For directories, check the newest file inside
            newest_age = min_age_days
            for child in entry.rglob("*"):
                if child.is_file():
                    age = get_mtime_days(child)
                    if age < newest_age:
                        newest_age = age
            if newest_age >= min_age_days:
                dirs.append(entry)

    return sorted(files, key=lambda p: p.name), sorted(dirs, key=lambda p: p.name)


def format_size(bytes_: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f} KB"
    else:
        return f"{bytes_ / (1024 * 1024):.2f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cleanup ephemeral files in report/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/cleanup_report.py --dry-run          # Preview (default)
  python tools/cleanup_report.py --apply            # Delete files
  python tools/cleanup_report.py --apply --days 14  # Files older than 14 days
        """,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files (default is dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview files to delete (default behavior)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        metavar="N",
        help="Only delete files older than N days (default: 0 = all)",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Path to report/ directory (auto-detected if not specified)",
    )

    args = parser.parse_args()

    # Determine report directory
    if args.report_dir:
        report_dir = args.report_dir
    else:
        # Auto-detect: assume script is in tools/
        script_dir = Path(__file__).parent
        report_dir = script_dir.parent / "report"

    if not report_dir.is_dir():
        print(f"ERROR: report directory not found: {report_dir}", file=sys.stderr)
        return 1

    # Find candidates
    files, dirs = find_candidates(report_dir, args.days)

    if not files and not dirs:
        print(f"No ephemeral files found (min age: {args.days} days)")
        return 0

    # Calculate sizes
    total_file_size = sum(f.stat().st_size for f in files)
    total_dir_size = sum(get_dir_size(d) for d in dirs)
    total_size = total_file_size + total_dir_size

    # Display candidates
    mode = "DRY-RUN" if not args.apply else "APPLY"
    print(f"=== cleanup_report [{mode}] ===")
    print(f"Report dir: {report_dir}")
    print(f"Min age: {args.days} days")
    print()

    if files:
        print(f"Files ({len(files)}):")
        for f in files:
            size = format_size(f.stat().st_size)
            age = get_mtime_days(f)
            print(f"  {f.name:<50} {size:>10}  ({age:.1f}d)")

    if dirs:
        print(f"\nDirectories ({len(dirs)}):")
        for d in dirs:
            size = format_size(get_dir_size(d))
            print(f"  {d.name:<50} {size:>10}")

    print()
    print(f"Total: {len(files)} files, {len(dirs)} dirs = {format_size(total_size)}")

    # Apply if requested
    if args.apply:
        print()
        deleted_files = 0
        deleted_dirs = 0
        errors = 0

        for f in files:
            try:
                f.unlink()
                deleted_files += 1
            except OSError as e:
                print(f"  ERROR: {f.name}: {e}", file=sys.stderr)
                errors += 1

        for d in dirs:
            try:
                import shutil
                shutil.rmtree(d)
                deleted_dirs += 1
            except OSError as e:
                print(f"  ERROR: {d.name}: {e}", file=sys.stderr)
                errors += 1

        print(f"Deleted: {deleted_files} files, {deleted_dirs} dirs")
        if errors:
            print(f"Errors: {errors}")
            return 1
    else:
        print("(Use --apply to delete)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
