"""
tests/test_idempotency_3F2.py

Tests for engine/idempotency.py idempotency store.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.idempotency import InMemoryIdempotencyStore


class TestInMemoryIdempotencyStore:
    """Tests for InMemoryIdempotencyStore."""
    
    def test_first_call_returns_true(self):
        """First call to mark_once returns True."""
        store = InMemoryIdempotencyStore()
        
        result = store.mark_once("key1")
        
        assert result is True
    
    def test_duplicate_returns_false(self):
        """Second call with same key returns False."""
        store = InMemoryIdempotencyStore()
        
        first = store.mark_once("key1")
        second = store.mark_once("key1")
        third = store.mark_once("key1")
        
        assert first is True
        assert second is False
        assert third is False
    
    def test_different_keys_independent(self):
        """Different keys are treated independently."""
        store = InMemoryIdempotencyStore()
        
        result_a = store.mark_once("key_a")
        result_b = store.mark_once("key_b")
        result_c = store.mark_once("key_c")
        
        assert result_a is True
        assert result_b is True
        assert result_c is True
        
        # Second calls should be duplicates
        assert store.mark_once("key_a") is False
        assert store.mark_once("key_b") is False
        assert store.mark_once("key_c") is False
    
    def test_ttl_expires(self):
        """After TTL expires, key can be marked again."""
        fake_time = [0.0]  # Use list for mutability in closure
        
        def fake_now():
            return fake_time[0]
        
        store = InMemoryIdempotencyStore(ttl_s=60.0, now_fn=fake_now)
        
        # First call at t=0
        fake_time[0] = 0.0
        first = store.mark_once("key1")
        assert first is True
        
        # Second call at t=30 (within TTL)
        fake_time[0] = 30.0
        within_ttl = store.mark_once("key1")
        assert within_ttl is False
        
        # Third call at t=61 (after TTL)
        fake_time[0] = 61.0
        after_ttl = store.mark_once("key1")
        assert after_ttl is True
    
    def test_ttl_exactly_at_boundary(self):
        """Key at exactly TTL boundary is expired."""
        fake_time = [0.0]
        
        def fake_now():
            return fake_time[0]
        
        store = InMemoryIdempotencyStore(ttl_s=60.0, now_fn=fake_now)
        
        # First call at t=0
        fake_time[0] = 0.0
        store.mark_once("key1")
        
        # At exactly t=60 (edge case)
        fake_time[0] = 60.0
        at_boundary = store.mark_once("key1")
        # now - seen_at = 60 - 0 = 60, which is NOT < ttl_s (60)
        # So it should be treated as expired
        assert at_boundary is True
    
    def test_size_tracking(self):
        """Size method returns correct count."""
        store = InMemoryIdempotencyStore()
        
        assert store.size() == 0
        
        store.mark_once("key1")
        assert store.size() == 1
        
        store.mark_once("key2")
        assert store.size() == 2
        
        # Duplicate doesn't increase size
        store.mark_once("key1")
        assert store.size() == 2
    
    def test_clear(self):
        """Clear removes all entries."""
        store = InMemoryIdempotencyStore()
        
        store.mark_once("key1")
        store.mark_once("key2")
        store.mark_once("key3")
        assert store.size() == 3
        
        store.clear()
        assert store.size() == 0
        
        # Can mark again after clear
        assert store.mark_once("key1") is True
    
    def test_many_unique_keys(self):
        """Handle many unique keys."""
        store = InMemoryIdempotencyStore()
        
        for i in range(100):
            result = store.mark_once(f"key_{i}")
            assert result is True
        
        assert store.size() == 100
        
        # All duplicates
        for i in range(100):
            result = store.mark_once(f"key_{i}")
            assert result is False
