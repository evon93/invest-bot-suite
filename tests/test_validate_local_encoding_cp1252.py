#!/usr/bin/env python3
"""
tests/test_validate_local_encoding_cp1252.py

Test that _safe_print handles encoding errors gracefully.
AG-H6-2-2-1
"""

import io
import sys

import pytest


def test_safe_print_handles_cp1252_checkmark():
    """Test that _safe_print doesn't crash when stdout is cp1252 and text contains ✓."""
    from tools.validate_local import _safe_print

    # Simulate cp1252 stdout
    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
    old_stdout = sys.stdout
    try:
        sys.stdout = wrapper
        # This should NOT raise UnicodeEncodeError
        _safe_print("✓")
        _safe_print("OK ✓ FAIL ✗")
        _safe_print("Normal ASCII text")
        wrapper.flush()
    finally:
        sys.stdout = old_stdout

    # No assertion needed - we just verify no exception was raised


def test_safe_print_works_with_utf8():
    """Test that _safe_print works normally with utf-8 stdout."""
    from tools.validate_local import _safe_print

    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="utf-8", errors="strict")
    old_stdout = sys.stdout
    try:
        sys.stdout = wrapper
        _safe_print("✓ ✗ Unicode works!")
        wrapper.flush()
    finally:
        sys.stdout = old_stdout

    # Verify content was written correctly
    content = buffer.getvalue().decode("utf-8")
    assert "✓" in content
    assert "✗" in content
