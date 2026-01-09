"""
tests/test_idempotency_store_sqlite.py

Tests for SQLiteIdempotencyStore with WAL mode.
"""

import os
import sys
import tempfile
import threading
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.idempotency import SQLiteIdempotencyStore


class TestSQLiteIdempotencyStoreBasic:
    """Basic functionality tests."""
    
    def test_first_insert_returns_true(self, tmp_path):
        """First time seeing a key should return True."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        result = store.mark_once("key_001")
        
        assert result is True
        assert store.size() == 1
        store.close()
    
    def test_second_insert_returns_false(self, tmp_path):
        """Duplicate key should return False."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        result1 = store.mark_once("key_001")
        result2 = store.mark_once("key_001")
        
        assert result1 is True
        assert result2 is False
        assert store.size() == 1
        store.close()
    
    def test_multiple_different_keys(self, tmp_path):
        """Multiple different keys all return True."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        results = []
        for i in range(5):
            results.append(store.mark_once(f"key_{i:03d}"))
        
        assert all(results), "All unique keys should return True"
        assert store.size() == 5
        store.close()
    
    def test_contains_method(self, tmp_path):
        """Contains method checks key existence."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        assert store.contains("key_001") is False
        store.mark_once("key_001")
        assert store.contains("key_001") is True
        store.close()


class TestSQLiteIdempotencyStorePersistence:
    """Tests for persistence across restarts."""
    
    def test_persistence_across_instances(self, tmp_path):
        """Keys persist after closing and reopening store."""
        db_path = tmp_path / "idempotency.db"
        
        # First instance: insert keys
        store1 = SQLiteIdempotencyStore(db_path=db_path)
        store1.mark_once("key_001")
        store1.mark_once("key_002")
        store1.close()
        
        # Second instance: keys should exist
        store2 = SQLiteIdempotencyStore(db_path=db_path)
        
        assert store2.mark_once("key_001") is False, "key_001 should exist from previous instance"
        assert store2.mark_once("key_002") is False, "key_002 should exist from previous instance"
        assert store2.mark_once("key_003") is True, "key_003 is new"
        assert store2.size() == 3
        store2.close()
    
    def test_crash_recovery_simulation(self, tmp_path):
        """Simulates crash recovery: keys survive."""
        db_path = tmp_path / "idempotency.db"
        
        # First run: insert keys, simulate crash (no close)
        store1 = SQLiteIdempotencyStore(db_path=db_path)
        store1.mark_once("order_event_123")
        store1.mark_once("order_event_456")
        # Don't close - simulate crash
        
        # Recovery: new instance should see previous keys
        store2 = SQLiteIdempotencyStore(db_path=db_path)
        
        assert store2.mark_once("order_event_123") is False, "Should be persisted"
        assert store2.mark_once("order_event_456") is False, "Should be persisted"
        assert store2.size() == 2
        store2.close()


class TestSQLiteIdempotencyStoreConcurrency:
    """Thread safety tests."""
    
    def test_concurrent_same_key_exactly_one_true(self, tmp_path):
        """
        With N threads inserting the same key, exactly one should return True.
        """
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        n_threads = 10
        results = []
        errors = []
        
        def worker():
            try:
                result = store.mark_once("shared_key")
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        store.close()
        
        assert len(errors) == 0, f"No errors expected, got: {errors}"
        assert len(results) == n_threads
        assert results.count(True) == 1, "Exactly one thread should win"
        assert results.count(False) == n_threads - 1
    
    def test_concurrent_different_keys_all_true(self, tmp_path):
        """
        With N threads inserting different keys, all should return True.
        """
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        n_threads = 10
        results = []
        
        def worker(thread_id):
            result = store.mark_once(f"thread_{thread_id}_key")
            results.append(result)
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        store.close()
        
        assert len(results) == n_threads
        assert all(results), "All unique keys should return True"


class TestSQLiteIdempotencyStoreWAL:
    """Tests verifying WAL mode is active."""
    
    def test_wal_mode_enabled(self, tmp_path):
        """Verify WAL journal mode is set."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        cursor = store._conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        
        assert mode.upper() == "WAL", f"Expected WAL mode, got {mode}"
        store.close()
    
    def test_synchronous_normal_default(self, tmp_path):
        """Verify synchronous mode defaults to NORMAL."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        cursor = store._conn.execute("PRAGMA synchronous")
        # NORMAL = 1, FULL = 2
        sync_value = cursor.fetchone()[0]
        
        assert sync_value == 1, f"Expected NORMAL (1), got {sync_value}"
        store.close()


class TestSQLiteIdempotencyStoreEdgeCases:
    """Edge case tests."""
    
    def test_empty_key(self, tmp_path):
        """Empty string key should work."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        assert store.mark_once("") is True
        assert store.mark_once("") is False
        store.close()
    
    def test_unicode_key(self, tmp_path):
        """Unicode keys should work."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        key = "orden_日本語_émoji_🚀"
        assert store.mark_once(key) is True
        assert store.mark_once(key) is False
        store.close()
    
    def test_very_long_key(self, tmp_path):
        """Very long keys should work (SQLite TEXT has no practical limit)."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        long_key = "x" * 10000
        assert store.mark_once(long_key) is True
        assert store.mark_once(long_key) is False
        store.close()
    
    def test_size_after_operations(self, tmp_path):
        """Size accurately reflects number of unique keys."""
        db_path = tmp_path / "idempotency.db"
        store = SQLiteIdempotencyStore(db_path=db_path)
        
        assert store.size() == 0
        
        store.mark_once("a")
        assert store.size() == 1
        
        store.mark_once("a")  # Duplicate
        assert store.size() == 1
        
        store.mark_once("b")
        assert store.size() == 2
        
        store.close()
