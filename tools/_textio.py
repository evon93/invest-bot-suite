#!/usr/bin/env python3
"""
tools/_textio.py

Text I/O helpers for cp1252-safe printing.
Centralized helper to avoid code duplication across tools.

AG-H7-1-1
"""

import sys


def safe_print(text: str) -> None:
    """Print text safely, handling encoding errors for limited encodings like cp1252."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        print(text)
    except UnicodeEncodeError:
        safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe)


def safe_print_lines(lines: list[str]) -> None:
    """Print multiple lines safely, joined by newlines."""
    safe_print("\n".join(lines))
