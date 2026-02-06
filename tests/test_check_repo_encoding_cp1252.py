#!/usr/bin/env python3
"""
tests/test_check_repo_encoding_cp1252.py

Test that safe_print() handles cp1252 encoding gracefully.
Mirrors the approach in test_validate_local_encoding_cp1252.py.

AG-H6-5-2-1, updated AG-H7-1-1
"""

import io
import sys


def test_safe_print_handles_cp1252_encoding():
    """Test that safe_print handles unicode characters on cp1252 stdout without raising."""
    # Import the safe_print function from _textio
    from tools._textio import safe_print
    
    # Create a fake stdout with cp1252 encoding and strict error handling
    class FakeStdout(io.StringIO):
        encoding = "cp1252"
        errors = "strict"
        
        def write(self, s):
            # Simulate cp1252 encoding failure for unicode chars
            try:
                s.encode("cp1252")
            except UnicodeEncodeError:
                raise UnicodeEncodeError("charmap", s, 0, len(s), "character maps to <undefined>")
            return super().write(s)
    
    original_stdout = sys.stdout
    try:
        sys.stdout = FakeStdout()
        
        # This should NOT raise even with unicode characters
        # safe_print should catch and replace problematic chars
        safe_print("Test: ✅ passed")
        safe_print("Test: ❌ failed")
        safe_print("Simple ASCII: PASS")
        
    finally:
        sys.stdout = original_stdout
    
    # If we get here without exception, the test passes


def test_safe_print_works_on_utf8():
    """Test that safe_print works normally on UTF-8 stdout."""
    from tools._textio import safe_print
    
    class FakeStdout(io.StringIO):
        encoding = "utf-8"
        errors = "strict"
    
    original_stdout = sys.stdout
    try:
        sys.stdout = FakeStdout()
        
        # Should work fine with UTF-8
        safe_print("Test: ✅ passed")
        safe_print("Test: ❌ failed")
        
        output = sys.stdout.getvalue()
        assert "✅" in output
        assert "❌" in output
        
    finally:
        sys.stdout = original_stdout
