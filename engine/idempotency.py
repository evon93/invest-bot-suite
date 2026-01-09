"""
engine/idempotency.py

Idempotency store for preventing duplicate execution of operations.
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Protocol, Set


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


@dataclass
class FileIdempotencyStore:
    """
    File-backed idempotency store using append-only JSONL.
    
    Keys persist across restarts for crash recovery.
    Each key is written as a JSON line: {"key": "..."}
    
    On init, loads all existing keys from file.
    On mark_once, appends new keys and flushes to disk.
    """
    file_path: Path
    _seen: Set[str] = field(default_factory=set, init=False)
    _file_handle: any = field(default=None, init=False)
    
    def __post_init__(self):
        self.file_path = Path(self.file_path)
        self._load_existing()
        # Open file for appending
        self._file_handle = open(self.file_path, "a", encoding="utf-8")
    
    def _load_existing(self) -> None:
        """Load existing keys from file."""
        if not self.file_path.exists():
            return
        
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        self._seen.add(data["key"])
                    except (json.JSONDecodeError, KeyError):
                        # Skip malformed lines
                        pass
    
    def mark_once(self, key: str) -> bool:
        """
        Mark a key as seen. Returns True if first time, False if duplicate.
        
        Appends new keys to file and flushes immediately for durability.
        """
        if key in self._seen:
            return False
        
        self._seen.add(key)
        
        # Append to file with immediate flush
        self._file_handle.write(json.dumps({"key": key}) + "\n")
        self._file_handle.flush()
        
        return True
    
    def close(self) -> None:
        """Close file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
    
    def size(self) -> int:
        """Return number of keys."""
        return len(self._seen)
    
    def __del__(self):
        self.close()


@dataclass
class SQLiteIdempotencyStore:
    """
    SQLite-backed idempotency store with WAL mode for concurrency.
    
    Provides atomic mark_once via INSERT OR IGNORE.
    Thread-safe via internal lock.
    
    Features:
    - WAL mode for better concurrent read/write performance
    - INSERT OR IGNORE for atomic "first-writer-wins" semantics
    - Thread-safe for multi-threaded access
    - Persists across restarts for crash recovery
    
    Attributes:
        db_path: Path to SQLite database file
        timeout_s: Database lock timeout in seconds
        synchronous: PRAGMA synchronous mode (NORMAL or FULL)
    """
    db_path: Path
    timeout_s: float = 30.0
    synchronous: str = "NORMAL"
    _conn: any = field(default=None, init=False, repr=False)
    _lock: any = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        import sqlite3
        import threading
        
        self.db_path = Path(self.db_path)
        self._lock = threading.Lock()
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect with WAL mode
        self._conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.timeout_s,
            check_same_thread=False,  # We manage thread safety via lock
            isolation_level=None,  # Autocommit mode
        )
        
        # Configure WAL and synchronous mode
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(f"PRAGMA synchronous={self.synchronous}")
        
        # Create table if not exists
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT PRIMARY KEY,
                created_at REAL NOT NULL
            )
        """)
    
    def mark_once(self, key: str) -> bool:
        """
        Mark a key as seen. Returns True if first time, False if duplicate.
        
        Uses INSERT OR IGNORE for atomic first-writer-wins semantics.
        Thread-safe via internal lock.
        
        Args:
            key: Unique operation key
            
        Returns:
            True if this is the first time seeing this key
            False if this key was already seen
        """
        import time
        
        with self._lock:
            cursor = self._conn.execute(
                "INSERT OR IGNORE INTO idempotency_keys (key, created_at) VALUES (?, ?)",
                (key, time.time())
            )
            # rowcount = 1 if inserted, 0 if already existed
            return cursor.rowcount == 1
    
    def contains(self, key: str) -> bool:
        """Check if a key exists (for testing/debugging)."""
        with self._lock:
            cursor = self._conn.execute(
                "SELECT 1 FROM idempotency_keys WHERE key = ?",
                (key,)
            )
            return cursor.fetchone() is not None
    
    def size(self) -> int:
        """Return number of keys in store."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM idempotency_keys")
            return cursor.fetchone()[0]
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __del__(self):
        self.close()
