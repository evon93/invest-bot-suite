"""
engine/idempotency.py

Idempotency store for preventing duplicate execution of operations.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Protocol


class IdempotencyStore(Protocol):
    """Protocol for idempotency stores."""
    
    def mark_once(self, key: str) -> bool:
        """
        Mark a key as seen. Returns True if first time, False if duplicate.
        
        Args:
            key: Unique operation key
            
        Returns:
            True if this is the first time seeing this key (proceed with operation)
            False if this key was already seen (skip/duplicate)
        """
        ...


@dataclass
class InMemoryIdempotencyStore:
    """
    In-memory idempotency store with TTL expiration.
    
    Thread-safe for single-threaded use (no actual locking needed).
    For multi-threaded use, add locking.
    
    Attributes:
        ttl_s: Time-to-live in seconds for entries
        now_fn: Function returning current time (for testing)
    """
    ttl_s: float = 3600.0
    now_fn: Callable[[], float] = field(default_factory=lambda: time.time)
    _seen: Dict[str, float] = field(default_factory=dict)
    
    def mark_once(self, key: str) -> bool:
        """
        Mark a key as seen. Returns True if first time or expired, False if duplicate.
        
        Automatically cleans up expired entries on access.
        """
        now = self.now_fn()
        
        # Check if key exists and not expired
        if key in self._seen:
            seen_at = self._seen[key]
            if now - seen_at < self.ttl_s:
                # Still valid → duplicate
                return False
            # Expired → treat as new
        
        # Mark as seen
        self._seen[key] = now
        
        # Lazy cleanup: remove expired entries (only every N calls or when size is large)
        self._maybe_cleanup(now)
        
        return True
    
    def _maybe_cleanup(self, now: float) -> None:
        """Remove expired entries to prevent memory leak."""
        # Only cleanup when store gets large
        if len(self._seen) < 1000:
            return
        
        expired_keys = [
            k for k, v in self._seen.items()
            if now - v >= self.ttl_s
        ]
        for k in expired_keys:
            del self._seen[k]
    
    def clear(self) -> None:
        """Clear all entries."""
        self._seen.clear()
    
    def size(self) -> int:
        """Return number of entries."""
        return len(self._seen)
