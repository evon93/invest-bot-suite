"""
tests/test_position_store_sqlite.py

Tests for state/position_store_sqlite.py
"""

import pytest
from state.position_store_sqlite import PositionStoreSQLite


class TestEnsureSchema:
    """Tests for ensure_schema()."""

    def test_creates_tables_on_fresh_db(self, tmp_path):
        """Schema should be created on fresh database."""
        db_path = tmp_path / "state.db"
        store = PositionStoreSQLite(db_path)
        store.ensure_schema()
        
        # Should not raise, tables exist
        positions = store.list_positions()
        assert positions == []
        store.close()

    def test_idempotent(self, tmp_path):
        """Calling ensure_schema() multiple times should be safe."""
        db_path = tmp_path / "state.db"
        store = PositionStoreSQLite(db_path)
        
        # Call multiple times
        store.ensure_schema()
        store.ensure_schema()
        store.ensure_schema()
        
        # Should still work
        assert store.list_positions() == []
        store.close()

    def test_context_manager(self, tmp_path):
        """Context manager should ensure schema and close."""
        db_path = tmp_path / "state.db"
        
        with PositionStoreSQLite(db_path) as store:
            store.upsert_position("BTC/USDT", 1.0)
            assert store.get_position("BTC/USDT") is not None


class TestPositionCRUD:
    """Tests for position CRUD operations."""

    def test_upsert_and_get(self, tmp_path):
        """upsert_position and get_position should work."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.upsert_position("BTC/USDT", 1.5, avg_price=50000.0)
            
            pos = store.get_position("BTC/USDT")
            assert pos is not None
            assert pos["symbol"] == "BTC/USDT"
            assert pos["qty"] == 1.5
            assert pos["avg_price"] == 50000.0

    def test_get_nonexistent(self, tmp_path):
        """get_position should return None for nonexistent symbol."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            assert store.get_position("NONEXISTENT") is None

    def test_upsert_updates_existing(self, tmp_path):
        """upsert_position should update existing position."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.upsert_position("BTC/USDT", 1.0, avg_price=50000.0)
            store.upsert_position("BTC/USDT", 2.0, avg_price=55000.0)
            
            pos = store.get_position("BTC/USDT")
            assert pos["qty"] == 2.0
            assert pos["avg_price"] == 55000.0

    def test_list_positions(self, tmp_path):
        """list_positions should return all positions."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.upsert_position("BTC/USDT", 1.0)
            store.upsert_position("ETH/USDT", 2.0)
            store.upsert_position("SOL/USDT", 3.0)
            
            positions = store.list_positions()
            assert len(positions) == 3
            symbols = [p["symbol"] for p in positions]
            assert "BTC/USDT" in symbols
            assert "ETH/USDT" in symbols
            assert "SOL/USDT" in symbols

    def test_list_positions_empty(self, tmp_path):
        """list_positions should return empty list on fresh db."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            assert store.list_positions() == []

    def test_meta_json(self, tmp_path):
        """Meta should be stored as JSON and parsed back."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            meta = {"strategy": "SMA", "entry_time": "2026-01-01T00:00:00Z"}
            store.upsert_position("BTC/USDT", 1.0, meta=meta)
            
            pos = store.get_position("BTC/USDT")
            assert pos["meta"] == meta

    def test_delete_position(self, tmp_path):
        """delete_position should remove position."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.upsert_position("BTC/USDT", 1.0)
            assert store.get_position("BTC/USDT") is not None
            
            deleted = store.delete_position("BTC/USDT")
            assert deleted is True
            assert store.get_position("BTC/USDT") is None

    def test_delete_nonexistent(self, tmp_path):
        """delete_position should return False for nonexistent."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            deleted = store.delete_position("NONEXISTENT")
            assert deleted is False


class TestApplyFill:
    """Tests for apply_fill()."""

    def test_buy_opens_position(self, tmp_path):
        """BUY on no position should open position."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            result = store.apply_fill("BTC/USDT", "BUY", 1.0, 50000.0)
            
            assert result["qty"] == 1.0
            assert result["avg_price"] == 50000.0

    def test_buy_increases_position(self, tmp_path):
        """BUY on existing position should increase and recalc avg."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.apply_fill("BTC/USDT", "BUY", 1.0, 50000.0)
            result = store.apply_fill("BTC/USDT", "BUY", 1.0, 60000.0)
            
            # avg = (1*50000 + 1*60000) / 2 = 55000
            assert result["qty"] == 2.0
            assert result["avg_price"] == pytest.approx(55000.0)

    def test_sell_reduces_position(self, tmp_path):
        """SELL should reduce position quantity."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.apply_fill("BTC/USDT", "BUY", 2.0, 50000.0)
            result = store.apply_fill("BTC/USDT", "SELL", 1.0, 55000.0)
            
            assert result["qty"] == 1.0
            # avg_price preserved on sell
            assert result["avg_price"] == 50000.0

    def test_sell_closes_position(self, tmp_path):
        """SELL exact qty should close position."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.apply_fill("BTC/USDT", "BUY", 1.0, 50000.0)
            result = store.apply_fill("BTC/USDT", "SELL", 1.0, 55000.0)
            
            assert result["qty"] == 0.0
            assert result.get("closed") is True
            assert store.get_position("BTC/USDT") is None

    def test_sell_no_position_creates_short(self, tmp_path):
        """SELL with no position creates short (negative qty)."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            result = store.apply_fill("BTC/USDT", "SELL", 1.0, 50000.0)
            
            assert result["qty"] == -1.0

    def test_invalid_qty_raises(self, tmp_path):
        """Zero or negative qty should raise."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            with pytest.raises(ValueError):
                store.apply_fill("BTC/USDT", "BUY", 0, 50000.0)
            with pytest.raises(ValueError):
                store.apply_fill("BTC/USDT", "BUY", -1.0, 50000.0)

    def test_invalid_side_raises(self, tmp_path):
        """Invalid side should raise."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            with pytest.raises(ValueError):
                store.apply_fill("BTC/USDT", "HOLD", 1.0, 50000.0)


class TestKeyValueStore:
    """Tests for KV operations."""

    def test_set_and_get(self, tmp_path):
        """set_kv and get_kv should work."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.set_kv("last_sync", "2026-01-01T00:00:00Z")
            
            value = store.get_kv("last_sync")
            assert value == "2026-01-01T00:00:00Z"

    def test_get_nonexistent(self, tmp_path):
        """get_kv should return None for nonexistent key."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            assert store.get_kv("nonexistent") is None

    def test_set_updates_existing(self, tmp_path):
        """set_kv should update existing key."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.set_kv("key1", "value1")
            store.set_kv("key1", "value2")
            
            assert store.get_kv("key1") == "value2"

    def test_delete_kv(self, tmp_path):
        """delete_kv should remove key."""
        db_path = tmp_path / "state.db"
        with PositionStoreSQLite(db_path) as store:
            store.set_kv("key1", "value1")
            deleted = store.delete_kv("key1")
            
            assert deleted is True
            assert store.get_kv("key1") is None
