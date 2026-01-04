"""
state/position_store_sqlite.py

SQLite-based position store for state persistence.

Uses only sqlite3 (stdlib), no external dependencies.
Schema is created idempotently on first access.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class PositionStoreSQLite:
    """
    SQLite-backed position store.
    
    Usage:
        store = PositionStoreSQLite("state.db")
        store.ensure_schema()
        store.upsert_position("BTC/USDT", 1.5, avg_price=50000.0)
        pos = store.get_position("BTC/USDT")
    """

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS positions (
        symbol TEXT PRIMARY KEY,
        qty REAL NOT NULL,
        avg_price REAL,
        updated_at TEXT NOT NULL,
        meta_json TEXT
    );
    
    CREATE TABLE IF NOT EXISTS kv (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """

    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize the position store.
        
        Args:
            db_path: Path to SQLite database file (created if not exists)
        """
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def ensure_schema(self) -> None:
        """
        Create schema if not exists (idempotent).
        
        Safe to call multiple times.
        """
        conn = self._get_connection()
        conn.executescript(self.SCHEMA_SQL)
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "PositionStoreSQLite":
        self.ensure_schema()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # -------------------------------------------------------------------------
    # Position CRUD
    # -------------------------------------------------------------------------

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position by symbol.
        
        Returns:
            Position dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT symbol, qty, avg_price, updated_at, meta_json FROM positions WHERE symbol = ?",
            (symbol,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def upsert_position(
        self,
        symbol: str,
        qty: float,
        avg_price: Optional[float] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Insert or update position.
        
        Args:
            symbol: Asset symbol
            qty: Position quantity
            avg_price: Average entry price (optional)
            meta: Additional metadata (optional)
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        meta_json = json.dumps(meta, sort_keys=True, separators=(',', ':')) if meta else None
        
        conn.execute(
            """
            INSERT INTO positions (symbol, qty, avg_price, updated_at, meta_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
                qty = excluded.qty,
                avg_price = excluded.avg_price,
                updated_at = excluded.updated_at,
                meta_json = excluded.meta_json
            """,
            (symbol, qty, avg_price, now, meta_json)
        )
        conn.commit()

    def list_positions(self) -> List[Dict[str, Any]]:
        """
        List all positions.
        
        Returns:
            List of position dicts
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT symbol, qty, avg_price, updated_at, meta_json FROM positions ORDER BY symbol"
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def delete_position(self, symbol: str) -> bool:
        """
        Delete position by symbol.
        
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
        conn.commit()
        return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Fill Application
    # -------------------------------------------------------------------------

    def apply_fill(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
    ) -> Dict[str, Any]:
        """
        Apply a fill to update position (transactional).
        
        Semantics:
        - BUY adds positive qty, SELL adds negative qty to position
        - Increasing position: recalculate weighted avg_price
        - Decreasing/reducing position: keep existing avg_price
        - Cross (sign flip): avg_price = fill price
        - Full close (qty near zero): delete position
        
        Args:
            symbol: Asset symbol (non-empty string)
            side: "BUY" or "SELL" (case-insensitive)
            qty: Fill quantity (must be > 0)
            price: Fill price (must be > 0)
            
        Returns:
            Updated position dict (or closed=True if closed)
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Validate inputs
        if not symbol or not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"symbol must be a non-empty string, got {symbol!r}")
        symbol = symbol.strip()
        
        if not isinstance(side, str):
            raise ValueError(f"side must be a string, got {type(side)}")
        side = side.upper().strip()
        if side not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {side!r}")
        
        if qty is None or qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")
        
        if price is None or price <= 0:
            raise ValueError(f"price must be positive, got {price}")
        
        # Transactional: use single connection with explicit transaction
        conn = self._get_connection()
        
        with conn:  # Implicit transaction
            # Read current position within transaction
            cursor = conn.execute(
                "SELECT symbol, qty, avg_price FROM positions WHERE symbol = ?",
                (symbol,)
            )
            row = cursor.fetchone()
            
            if row is None:
                current_qty = 0.0
                current_avg = 0.0
            else:
                current_qty = float(row["qty"])
                current_avg = float(row["avg_price"]) if row["avg_price"] is not None else 0.0
            
            # Calculate new qty and avg_price
            new_qty, new_avg = self._compute_new_position(
                current_qty, current_avg, side, qty, price
            )
            
            # Handle position closure
            if abs(new_qty) < 1e-10:
                conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
                return {"symbol": symbol, "qty": 0.0, "avg_price": None, "closed": True}
            
            # Upsert within transaction
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO positions (symbol, qty, avg_price, updated_at, meta_json)
                VALUES (?, ?, ?, ?, NULL)
                ON CONFLICT(symbol) DO UPDATE SET
                    qty = excluded.qty,
                    avg_price = excluded.avg_price,
                    updated_at = excluded.updated_at
                """,
                (symbol, new_qty, new_avg, now)
            )
        
        # Read back the updated position
        return self.get_position(symbol)

    def _compute_new_position(
        self,
        current_qty: float,
        current_avg: float,
        side: str,
        fill_qty: float,
        fill_price: float,
    ) -> tuple:
        """
        Compute new position qty and avg_price after a fill.
        
        Rules (DS-3C-4-1):
        1. Increasing position (same sign): weighted average
        2. Reducing position (opposite sign, no cross): keep avg_price
        3. Crossing zero: avg_price = fill_price
        4. Opening from flat: avg_price = fill_price
        
        Args:
            current_qty: Current position quantity (can be negative for short)
            current_avg: Current average price
            side: "BUY" or "SELL"
            fill_qty: Fill quantity (always positive)
            fill_price: Fill price
            
        Returns:
            Tuple of (new_qty, new_avg_price)
        """
        # Determine the signed fill delta
        if side == "BUY":
            delta = fill_qty  # Positive
        else:
            delta = -fill_qty  # Negative
        
        # Case 1: No existing position (flat)
        if abs(current_qty) < 1e-10:
            return (delta, fill_price)
        
        new_qty = current_qty + delta
        
        # Case 2: Full close (new position is flat)
        if abs(new_qty) < 1e-10:
            return (0.0, None)
        
        # Determine if this is increasing, reducing, or crossing
        same_sign_as_current = (delta > 0 and current_qty > 0) or (delta < 0 and current_qty < 0)
        crossed_zero = (current_qty > 0 and new_qty < 0) or (current_qty < 0 and new_qty > 0)
        
        if crossed_zero:
            # Case 3: Crossed zero - avg_price = fill price
            return (new_qty, fill_price)
        
        if same_sign_as_current:
            # Case 4: Increasing position - weighted average
            total_value = (abs(current_qty) * current_avg) + (fill_qty * fill_price)
            new_avg = total_value / abs(new_qty)
            return (new_qty, new_avg)
        else:
            # Case 5: Reducing position (partial cover) - keep avg_price
            return (new_qty, current_avg)

    # -------------------------------------------------------------------------
    # Key-Value Store
    # -------------------------------------------------------------------------

    def set_kv(self, key: str, value: str) -> None:
        """Set key-value pair."""
        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO kv (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value)
        )
        conn.commit()

    def get_kv(self, key: str) -> Optional[str]:
        """Get value by key."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT value FROM kv WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else None

    def delete_kv(self, key: str) -> bool:
        """Delete key-value pair."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM kv WHERE key = ?", (key,))
        conn.commit()
        return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dict with parsed meta_json."""
        d = dict(row)
        if d.get("meta_json"):
            try:
                d["meta"] = json.loads(d["meta_json"])
            except json.JSONDecodeError:
                d["meta"] = None
        else:
            d["meta"] = None
        del d["meta_json"]
        return d
