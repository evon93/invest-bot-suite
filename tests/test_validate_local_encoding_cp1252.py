#!/usr/bin/env python3
"""
tests/test_validate_local_encoding_cp1252.py

Test that safe_print handles encoding errors gracefully.
AG-H6-2-2-1, updated AG-H7-1-1
"""

import io
import sys

import pytest


def test_safe_print_handles_cp1252_checkmark():
    """Test that safe_print doesn't crash when stdout is cp1252 and text contains ✓."""
    from tools._textio import safe_print

    # Simulate cp1252 stdout
    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="cp1252", errors="strict")
    old_stdout = sys.stdout
    try:
        sys.stdout = wrapper
        # This should NOT raise UnicodeEncodeError
        safe_print("✓")
        safe_print("OK ✓ FAIL ✗")
        safe_print("Normal ASCII text")
        wrapper.flush()
    finally:
        sys.stdout = old_stdout

    # No assertion needed - we just verify no exception was raised


def test_safe_print_works_with_utf8():
    """Test that safe_print works normally with utf-8 stdout."""
    from tools._textio import safe_print

    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="utf-8", errors="strict")
    old_stdout = sys.stdout
    try:
        sys.stdout = wrapper
        safe_print("✓ ✗ Unicode works!")
        wrapper.flush()
    finally:
        sys.stdout = old_stdout

    # Verify content was written correctly
    content = buffer.getvalue().decode("utf-8")
    assert "✓" in content
    assert "✗" in content
