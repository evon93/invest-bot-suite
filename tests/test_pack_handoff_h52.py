"""
tests/test_pack_handoff_h52.py

Unit tests for tools/pack_handoff.py deterministic ZIP packaging.

AG-H5-2-1
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import pack_handoff


def sha256_bytes(data: bytes) -> str:
    """Calculate SHA256 of bytes."""
    return hashlib.sha256(data).hexdigest()


class TestPackHandoff:
    """Unit tests for pack_handoff.py."""

    def test_sha256_file_correct(self, tmp_path):
        """sha256_file returns correct hash."""
        content = b"hello world\n"
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(content)
        
        expected = sha256_bytes(content)
        actual = pack_handoff.sha256_file(test_file)
        
        assert actual == expected

    def test_create_deterministic_zip_sorted_entries(self, tmp_path):
        """ZIP entries are sorted lexicographically."""
        # Create files in non-alphabetic order
        (tmp_path / "c_file.txt").write_text("c content")
        (tmp_path / "a_file.txt").write_text("a content")
        (tmp_path / "b_file.txt").write_text("b content")
        
        files = [
            (tmp_path / "c_file.txt", "c_file.txt"),
            (tmp_path / "a_file.txt", "a_file.txt"),
            (tmp_path / "b_file.txt", "b_file.txt"),
        ]
        
        zip_path = tmp_path / "out.zip"
        pack_handoff.create_deterministic_zip(files, zip_path)
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
        
        assert names == ["a_file.txt", "b_file.txt", "c_file.txt"]

    def test_create_deterministic_zip_fixed_timestamp(self, tmp_path):
        """ZIP entries have fixed timestamp for reproducibility."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        files = [(test_file, "test.txt")]
        zip_path = tmp_path / "out.zip"
        
        pack_handoff.create_deterministic_zip(files, zip_path)
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            info = zf.getinfo("test.txt")
        
        assert info.date_time == pack_handoff.FIXED_ZIP_DATETIME

    def test_is_excluded_matches_patterns(self):
        """is_excluded correctly identifies excluded patterns."""
        excludes = ["*.pyc", "__pycache__", "*.env"]
        
        assert pack_handoff.is_excluded("module.pyc", excludes) is True
        assert pack_handoff.is_excluded("src/__pycache__/foo.py", excludes) is True
        assert pack_handoff.is_excluded("config.env", excludes) is True
        assert pack_handoff.is_excluded("report/data.txt", excludes) is False
        assert pack_handoff.is_excluded("src/main.py", excludes) is False

    def test_manifest_has_correct_structure(self, tmp_path, monkeypatch):
        """Generated manifest has all required fields."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content 1")
        (tmp_path / "file2.txt").write_text("content 2")
        
        # Patch paths
        monkeypatch.setattr(pack_handoff, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(pack_handoff, "REPORT_DIR", tmp_path / "report")
        (tmp_path / "report").mkdir()
        
        # Run with custom files
        monkeypatch.setattr(
            sys, "argv",
            [
                "pack_handoff.py",
                "--out", str(tmp_path / "out.zip"),
                "--manifest", str(tmp_path / "manifest.json"),
                "--files", "file1.txt", "file2.txt",
            ]
        )
        
        pack_handoff.main()
        
        # Verify manifest
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        required_fields = {
            "iso_time", "branch", "head", "python", "platform",
            "zip_path", "file_count", "files"
        }
        assert required_fields.issubset(set(manifest.keys()))
        
        assert manifest["file_count"] == 2
        assert len(manifest["files"]) == 2
        
        # Check file entry structure
        for file_entry in manifest["files"]:
            assert "rel_path" in file_entry
            assert "sha256" in file_entry
            assert "size_bytes" in file_entry
            assert len(file_entry["sha256"]) == 64  # SHA256 hex length

    def test_zip_contains_correct_content(self, tmp_path, monkeypatch):
        """ZIP file contains correct file content."""
        content1 = "file 1 content here"
        content2 = "file 2 different content"
        
        (tmp_path / "a.txt").write_text(content1)
        (tmp_path / "b.txt").write_text(content2)
        
        monkeypatch.setattr(pack_handoff, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(pack_handoff, "REPORT_DIR", tmp_path / "report")
        (tmp_path / "report").mkdir()
        
        zip_path = tmp_path / "out.zip"
        manifest_path = tmp_path / "manifest.json"
        
        monkeypatch.setattr(
            sys, "argv",
            [
                "pack_handoff.py",
                "--out", str(zip_path),
                "--manifest", str(manifest_path),
                "--files", "a.txt", "b.txt",
            ]
        )
        
        pack_handoff.main()
        
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert zf.read("a.txt").decode() == content1
            assert zf.read("b.txt").decode() == content2

    def test_missing_file_logs_warning(self, tmp_path, monkeypatch, capsys):
        """Missing files are logged as warnings, not errors."""
        (tmp_path / "exists.txt").write_text("I exist")
        
        monkeypatch.setattr(pack_handoff, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(pack_handoff, "REPORT_DIR", tmp_path / "report")
        (tmp_path / "report").mkdir()
        
        monkeypatch.setattr(
            sys, "argv",
            [
                "pack_handoff.py",
                "--out", str(tmp_path / "out.zip"),
                "--manifest", str(tmp_path / "manifest.json"),
                "--files", "exists.txt", "missing.txt",
            ]
        )
        
        result = pack_handoff.main()
        
        assert result == 0  # Should not fail
        
        # Check manifest only has existing file
        with open(tmp_path / "manifest.json") as f:
            manifest = json.load(f)
        
        assert manifest["file_count"] == 1
        assert manifest["files"][0]["rel_path"] == "exists.txt"

    def test_dry_run_creates_no_files(self, tmp_path, monkeypatch):
        """--dry-run does not create ZIP or manifest."""
        (tmp_path / "test.txt").write_text("test")
        
        monkeypatch.setattr(pack_handoff, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(pack_handoff, "REPORT_DIR", tmp_path / "report")
        
        zip_path = tmp_path / "out.zip"
        manifest_path = tmp_path / "manifest.json"
        
        monkeypatch.setattr(
            sys, "argv",
            [
                "pack_handoff.py",
                "--dry-run",
                "--out", str(zip_path),
                "--manifest", str(manifest_path),
                "--files", "test.txt",
            ]
        )
        
        result = pack_handoff.main()
        
        assert result == 0
        assert not zip_path.exists()
        assert not manifest_path.exists()
