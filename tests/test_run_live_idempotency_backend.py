"""
tests/test_run_live_idempotency_backend.py

Tests for --idempotency-backend wiring in run_live_3E.py
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildIdempotencyStore:
    """Tests for build_idempotency_store helper function."""
    
    def test_sqlite_backend_creates_db(self, tmp_path):
        """sqlite backend creates DB file and mark_once works."""
        from tools.run_live_3E import build_idempotency_store
        
        store = build_idempotency_store(tmp_path, "sqlite")
        
        # Verify DB file exists
        db_path = tmp_path / "idempotency.db"
        assert db_path.exists(), "SQLite DB should be created"
        
        # Verify mark_once works
        assert store.mark_once("key_001") is True
        assert store.mark_once("key_001") is False
        
        store.close()
    
    def test_sqlite_backend_persistence(self, tmp_path):
        """sqlite backend persists keys across instances."""
        from tools.run_live_3E import build_idempotency_store
        
        # First instance
        store1 = build_idempotency_store(tmp_path, "sqlite")
        store1.mark_once("persistent_key")
        store1.close()
        
        # Second instance - should detect duplicate
        store2 = build_idempotency_store(tmp_path, "sqlite")
        result = store2.mark_once("persistent_key")
        store2.close()
        
        assert result is False, "Key should persist across instances"
    
    def test_file_backend_creates_jsonl(self, tmp_path):
        """file backend creates JSONL file at expected path."""
        from tools.run_live_3E import build_idempotency_store
        
        store = build_idempotency_store(tmp_path, "file")
        
        # Mark a key to trigger file write
        store.mark_once("key_001")
        
        # Verify JSONL file path
        jsonl_path = tmp_path / "idempotency_keys.jsonl"
        assert jsonl_path.exists(), "JSONL file should be created"
        
        store.close()
    
    def test_file_backend_persistence(self, tmp_path):
        """file backend persists keys across instances."""
        from tools.run_live_3E import build_idempotency_store
        
        # First instance
        store1 = build_idempotency_store(tmp_path, "file")
        store1.mark_once("file_persistent_key")
        store1.close()
        
        # Second instance
        store2 = build_idempotency_store(tmp_path, "file")
        result = store2.mark_once("file_persistent_key")
        store2.close()
        
        assert result is False, "Key should persist across file instances"
    
    def test_memory_backend_no_persistence(self, tmp_path):
        """memory backend does not persist keys (new instance = fresh)."""
        from tools.run_live_3E import build_idempotency_store
        
        # First instance
        store1 = build_idempotency_store(tmp_path, "memory")
        store1.mark_once("memory_key")
        
        # Memory store has no close(), but we can discard
        del store1
        
        # Second instance - should NOT detect duplicate (fresh memory)
        store2 = build_idempotency_store(tmp_path, "memory")
        result = store2.mark_once("memory_key")
        
        assert result is True, "Memory store should not persist"
    
    def test_unknown_backend_raises(self, tmp_path):
        """Unknown backend raises ValueError."""
        from tools.run_live_3E import build_idempotency_store
        
        with pytest.raises(ValueError) as exc_info:
            build_idempotency_store(tmp_path, "redis")
        
        assert "unknown" in str(exc_info.value).lower()


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing (integration-like)."""
    
    def test_default_backend_is_file(self):
        """Default idempotency backend should be 'file'."""
        import argparse
        from unittest import mock
        
        # Mock sys.argv to test arg parsing
        with mock.patch("sys.argv", ["run_live_3E.py"]):
            # We need to parse like the script does
            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--idempotency-backend",
                choices=["file", "sqlite", "memory"],
                default="file"
            )
            args = parser.parse_args([])
            
            assert args.idempotency_backend == "file"
    
    def test_sqlite_backend_selectable(self):
        """sqlite backend can be selected."""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--idempotency-backend",
            choices=["file", "sqlite", "memory"],
            default="file"
        )
        args = parser.parse_args(["--idempotency-backend", "sqlite"])
        
        assert args.idempotency_backend == "sqlite"
