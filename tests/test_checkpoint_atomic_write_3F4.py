"""
tests/test_checkpoint_atomic_write_3F4.py

Tests for atomic checkpoint writing.
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.checkpoint import Checkpoint


class TestCheckpointAtomicWrite:
    """Tests for atomic checkpoint persistence."""
    
    def test_save_and_load(self):
        """Checkpoint can be saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "checkpoint.json"
            
            cp = Checkpoint.create_new("test-run-001")
            cp = cp.update(0)  # Processed idx 0
            cp = cp.update(1)  # Processed idx 1
            
            cp.save_atomic(path)
            
            loaded = Checkpoint.load(path)
            
            assert loaded.run_id == "test-run-001"
            assert loaded.last_processed_idx == 1
            assert loaded.processed_count == 2
    
    def test_checkpoint_always_parseable(self):
        """Multiple writes always produce valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "checkpoint.json"
            
            cp = Checkpoint.create_new("multi-write-run")
            
            for i in range(100):
                cp = cp.update(i)
                cp.save_atomic(path)
                
                # Verify always parseable
                with open(path, "r") as f:
                    data = json.load(f)
                    assert data["last_processed_idx"] == i
                    assert data["processed_count"] == i + 1
    
    def test_tmp_file_not_left_behind(self):
        """Temp file is cleaned up after atomic write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "checkpoint.json"
            tmp_path = path.with_suffix(".json.tmp")
            
            cp = Checkpoint.create_new("cleanup-run")
            cp.save_atomic(path)
            
            assert path.exists()
            assert not tmp_path.exists()
    
    def test_create_new_initial_values(self):
        """New checkpoint has correct initial values."""
        cp = Checkpoint.create_new("new-run")
        
        assert cp.run_id == "new-run"
        assert cp.last_processed_idx == -1  # Nothing processed
        assert cp.processed_count == 0
        assert cp.updated_at is not None
    
    def test_update_immutable(self):
        """Update returns new instance, doesn't modify original."""
        cp1 = Checkpoint.create_new("immutable-run")
        cp2 = cp1.update(0)
        
        assert cp1.last_processed_idx == -1
        assert cp1.processed_count == 0
        
        assert cp2.last_processed_idx == 0
        assert cp2.processed_count == 1
    
    def test_load_nonexistent_raises(self):
        """Loading nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Checkpoint.load(Path("/nonexistent/path/checkpoint.json"))


class TestFileIdempotencyStore:
    """Tests for FileIdempotencyStore."""
    
    def test_persist_and_reload(self):
        """Keys persist across store instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "idempotency_keys.jsonl"
            
            from engine.idempotency import FileIdempotencyStore
            
            # First store instance
            store1 = FileIdempotencyStore(path)
            assert store1.mark_once("key-001") is True
            assert store1.mark_once("key-002") is True
            assert store1.mark_once("key-001") is False  # Duplicate
            store1.close()
            
            # Second store instance (simulating restart)
            store2 = FileIdempotencyStore(path)
            assert store2.mark_once("key-001") is False  # Already seen
            assert store2.mark_once("key-002") is False  # Already seen
            assert store2.mark_once("key-003") is True   # New
            store2.close()
            
            # Verify file contents
            with open(path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3
    
    def test_empty_file_on_first_use(self):
        """Store creates file on first mark_once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "new_keys.jsonl"
            
            from engine.idempotency import FileIdempotencyStore
            
            assert not path.exists()
            
            store = FileIdempotencyStore(path)
            store.mark_once("first-key")
            store.close()
            
            assert path.exists()
    
    def test_size_tracking(self):
        """Size returns correct count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "size_test.jsonl"
            
            from engine.idempotency import FileIdempotencyStore
            
            store = FileIdempotencyStore(path)
            assert store.size() == 0
            
            store.mark_once("a")
            assert store.size() == 1
            
            store.mark_once("b")
            assert store.size() == 2
            
            store.mark_once("a")  # Duplicate
            assert store.size() == 2
            
            store.close()
