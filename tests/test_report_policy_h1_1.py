"""
tests/test_report_policy_h1_1.py

Tests for report_artifact_policy.py (AG-H1-1-1).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from report_artifact_policy import (
    matches_any,
    check_policy,
    generate_digest,
    ALLOWLIST_PATTERNS,
    WARNING_THRESHOLD,
    BLOCK_THRESHOLD,
)


class TestMatchesAny:
    """Test pattern matching."""
    
    def test_allowlist_return_md(self):
        assert matches_any("AG-H1-1-1_return.md", ALLOWLIST_PATTERNS)
    
    def test_allowlist_last_commit(self):
        assert matches_any("AG-3O-2-1_last_commit.txt", ALLOWLIST_PATTERNS)
    
    def test_non_allowlist_diff(self):
        assert not matches_any("AG-H1-1-1_diff.patch", ALLOWLIST_PATTERNS)


class TestCheckPolicy:
    """Test policy checking."""
    
    def test_empty_dir_no_violations(self, tmp_path):
        report_dir = tmp_path / "report"
        report_dir.mkdir()
        
        warnings, errors = check_policy(report_dir)
        
        assert warnings == []
        assert errors == []
    
    def test_small_file_no_violation(self, tmp_path):
        report_dir = tmp_path / "report"
        report_dir.mkdir()
        (report_dir / "small.txt").write_text("hello")
        
        warnings, errors = check_policy(report_dir)
        
        assert warnings == []
        assert errors == []
    
    def test_large_file_warning(self, tmp_path):
        report_dir = tmp_path / "report"
        report_dir.mkdir()
        
        # Create file > 1MB
        large_file = report_dir / "large.txt"
        large_file.write_bytes(b"x" * (WARNING_THRESHOLD + 1000))
        
        warnings, errors = check_policy(report_dir)
        
        assert len(warnings) == 1
        assert "large.txt" in warnings[0]["path"]
        assert errors == []
    
    def test_allowlist_exempt_from_check(self, tmp_path):
        report_dir = tmp_path / "report"
        report_dir.mkdir()
        
        # Create large return.md (allowlisted)
        return_file = report_dir / "AG-test_return.md"
        return_file.write_bytes(b"x" * (WARNING_THRESHOLD + 1000))
        
        warnings, errors = check_policy(report_dir)
        
        # Should be exempt
        assert warnings == []
        assert errors == []


class TestGenerateDigest:
    """Test digest generation."""
    
    def test_digest_has_required_fields(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")
        
        digest = generate_digest(test_file)
        
        assert "path" in digest
        assert "size_bytes" in digest
        assert "sha256" in digest
        assert len(digest["sha256"]) == 64  # SHA256 hex length
