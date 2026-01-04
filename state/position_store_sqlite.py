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
        meta_json = json.dumps(meta) if meta else None
        
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
        Apply a fill to update position.
        
        BUY: Increases position, recalculates avg_price
        SELL: Decreases position (closes if qty matches)
        
        Args:
            symbol: Asset symbol
            side: "BUY" or "SELL"
            qty: Fill quantity (always positive)
            price: Fill price
            
        Returns:
            Updated position dict
        """
        if qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")
        if side.upper() not in ("BUY", "SELL"):
            raise ValueError(f"side must be BUY or SELL, got {side}")
        
        side = side.upper()
        current = self.get_position(symbol)
        
        if current is None:
            # No existing position
            if side == "BUY":
                new_qty = qty
                new_avg = price
            else:
                # SELL with no position: short position
                new_qty = -qty
                new_avg = price
        else:
            current_qty = current["qty"]
            current_avg = current["avg_price"] or 0.0
            
            if side == "BUY":
                # Add to position
                total_value = (current_qty * current_avg) + (qty * price)
                new_qty = current_qty + qty
                new_avg = total_value / new_qty if new_qty != 0 else 0.0
            else:
                # Reduce position
                new_qty = current_qty - qty
                # Keep avg_price on sell (realized P&L would be external)
                new_avg = current_avg if new_qty != 0 else None
        
        # Handle position closure
        if abs(new_qty) < 1e-10:
            self.delete_position(symbol)
            return {"symbol": symbol, "qty": 0.0, "avg_price": None, "closed": True}
        
        self.upsert_position(symbol, new_qty, new_avg)
        return self.get_position(symbol)

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
