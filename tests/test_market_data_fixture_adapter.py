"""
tests/test_market_data_fixture_adapter.py

Unit tests for FixtureMarketDataAdapter.

AG-3K-1-1: Tests for poll(), ordering, epoch ms conversion, and no-lookahead.
AG-3K-1-2: Hardening tests for schema validation, gaps, NaNs, up_to_ts, EOF.
"""

import pytest
from pathlib import Path
import subprocess
import json
import pandas as pd

from engine.market_data.fixture_adapter import FixtureMarketDataAdapter, FixtureSchemaError
from engine.market_data.market_data_adapter import MarketDataEvent


# Path to test fixture
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ohlcv_fixture_3K1.csv"


class TestFixtureMarketDataAdapter:
    """Tests for FixtureMarketDataAdapter."""
    
    def test_load_fixture_creates_events(self):
        """Adapter loads fixture and creates events."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        assert len(adapter) == 10  # 10 bars in fixture
        assert adapter.remaining() == 10
    
    def test_poll_respects_max_items(self):
        """poll(5) returns at most 5 items."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        batch = adapter.poll(max_items=5)
        assert len(batch) == 5
        assert adapter.remaining() == 5
    
    def test_poll_order_monotonic(self):
        """All events returned by poll have non-decreasing ts."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        events = adapter.poll(max_items=100)
        
        for i in range(1, len(events)):
            assert events[i].ts >= events[i-1].ts, f"ts not monotonic at index {i}"
    
    def test_epoch_ms_conversion(self):
        """Timestamps are converted to epoch ms correctly."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        events = adapter.poll(max_items=1)
        
        assert len(events) == 1
        event = events[0]
        
        # First bar: 2024-01-15 00:00:00+00:00
        # epoch ms: 1705276800000
        expected_ts_ms = 1705276800000
        assert event.ts == expected_ts_ms, f"Expected {expected_ts_ms}, got {event.ts}"
    
    def test_no_lookahead(self):
        """After N polls, no events with ts > last emitted are returned."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Poll 3 events
        batch1 = adapter.poll(max_items=3)
        last_ts_1 = batch1[-1].ts
        
        # Poll more
        batch2 = adapter.poll(max_items=3)
        
        # All new events must have ts >= last_ts_1 (since monotonic)
        for e in batch2:
            assert e.ts >= last_ts_1, f"Lookahead detected: {e.ts} < {last_ts_1}"
    
    def test_exhausted_returns_empty(self):
        """After consuming all events, poll returns empty list."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Consume all
        while adapter.remaining() > 0:
            adapter.poll(max_items=100)
        
        # Should return empty
        assert adapter.poll(max_items=100) == []
        assert adapter.remaining() == 0
    
    def test_reset_restarts_iteration(self):
        """reset() allows re-iteration from beginning."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Consume some
        adapter.poll(max_items=5)
        assert adapter.remaining() == 5
        
        # Reset
        adapter.reset()
        assert adapter.remaining() == 10
        
        # Poll again from start
        batch = adapter.poll(max_items=2)
        assert len(batch) == 2
    
    def test_to_dataframe_returns_copy(self):
        """to_dataframe() returns valid DataFrame copy."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        df = adapter.to_dataframe()
        
        assert len(df) == 10
        assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        
        # Modifying returned df doesn't affect adapter
        df["close"] = 0
        events = adapter.poll(max_items=1)
        assert events[0].close != 0
    
    def test_event_has_correct_attributes(self):
        """MarketDataEvent has all expected attributes."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH, symbol="ETH/USDT", timeframe="4h")
        events = adapter.poll(max_items=1)
        
        event = events[0]
        assert isinstance(event, MarketDataEvent)
        assert event.symbol == "ETH/USDT"
        assert event.timeframe == "4h"
        assert isinstance(event.ts, int)
        assert isinstance(event.open, float)
        assert isinstance(event.high, float)
        assert isinstance(event.low, float)
        assert isinstance(event.close, float)
        assert isinstance(event.volume, float)


class TestRunnerFixtureMode:
    """Integration test for runner with fixture mode."""
    
    def test_smoke_runner_fixture_mode(self, tmp_path):
        """Runner executes successfully with --data fixture."""
        outdir = tmp_path / "out_fixture"
        
        result = subprocess.run(
            [
                "python", "tools/run_live_3E.py",
                "--data", "fixture",
                "--fixture-path", str(FIXTURE_PATH),
                "--outdir", str(outdir),
                "--max-steps", "5",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        
        # Check execution success
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        # Check artifacts exist
        assert (outdir / "events.ndjson").exists(), "events.ndjson not created"
        assert (outdir / "run_meta.json").exists(), "run_meta.json not created"
        
        # Check metadata contains fixture info
        with open(outdir / "run_meta.json") as f:
            meta = json.load(f)
        assert meta["data_source"] == "fixture"
        assert meta["fixture_path"] == str(FIXTURE_PATH)


class TestHardeningFeatures:
    """AG-3K-1-2: Hardening tests for schema, gaps, NaNs, up_to_ts, EOF."""
    
    # --- up_to_ts (No-Lookahead) Tests ---
    
    def test_poll_up_to_ts_respects_boundary(self):
        """poll(up_to_ts=X) returns only events with ts <= X."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Get first event's ts
        first_ts = adapter.peek_next_ts()
        assert first_ts is not None
        
        # Poll with up_to_ts = first_ts (should get only 1 event)
        batch = adapter.poll(max_items=100, up_to_ts=first_ts)
        assert len(batch) == 1
        assert batch[0].ts == first_ts
        
        # Remaining events still available
        assert adapter.remaining() == 9
    
    def test_poll_up_to_ts_blocks_future_events(self):
        """poll(up_to_ts=X) never returns events with ts > X."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # First bar ts: 1705276800000 (2024-01-15 00:00:00 UTC)
        # Second bar ts: 1705280400000 (2024-01-15 01:00:00 UTC)
        boundary_ts = 1705276800000  # Only first bar
        
        batch = adapter.poll(max_items=100, up_to_ts=boundary_ts)
        
        for event in batch:
            assert event.ts <= boundary_ts, f"Lookahead: {event.ts} > {boundary_ts}"
    
    def test_poll_up_to_ts_buffers_future_events(self):
        """Events beyond up_to_ts remain available for future polls."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Poll with strict boundary (only first 2 bars)
        boundary_ts = 1705280400000  # 2024-01-15 01:00:00 UTC
        batch1 = adapter.poll(max_items=100, up_to_ts=boundary_ts)
        
        assert len(batch1) == 2  # First two bars only
        assert adapter.remaining() == 8  # Rest still buffered
        
        # Now poll with higher boundary
        batch2 = adapter.poll(max_items=100, up_to_ts=boundary_ts + 7200000)  # +2 hours
        assert len(batch2) == 2  # Two more bars
    
    # --- EOF Behavior Tests ---
    
    def test_eof_returns_empty_list_not_exception(self):
        """EOF returns [] consistently, not exception."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        # Exhaust
        adapter.poll(max_items=100)
        
        # Multiple EOF calls should all return []
        assert adapter.poll() == []
        assert adapter.poll() == []
        assert adapter.poll(max_items=1000) == []
    
    def test_is_exhausted_flag(self):
        """is_exhausted() correctly reports EOF state."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        assert not adapter.is_exhausted()
        
        adapter.poll(max_items=100)
        
        assert adapter.is_exhausted()
        
        # Reset clears exhaustion
        adapter.reset()
        assert not adapter.is_exhausted()
    
    def test_peek_next_ts_returns_none_at_eof(self):
        """peek_next_ts() returns None when exhausted."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        
        assert adapter.peek_next_ts() is not None
        
        adapter.poll(max_items=100)
        
        assert adapter.peek_next_ts() is None
    
    # --- Schema Validation Tests ---
    
    def test_schema_rejects_negative_prices(self, tmp_path):
        """Negative prices trigger FixtureSchemaError."""
        csv = tmp_path / "bad.csv"
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00+00:00,-100.0,110.0,90.0,105.0,1000\n"
        )
        
        with pytest.raises(FixtureSchemaError, match="non-positive"):
            FixtureMarketDataAdapter(csv)
    
    def test_schema_rejects_invalid_ohlc_high_low(self, tmp_path):
        """Invalid OHLC (high < low) triggers error."""
        csv = tmp_path / "bad_ohlc.csv"
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00+00:00,100.0,95.0,105.0,100.0,1000\n"  # high < low
        )
        
        with pytest.raises(FixtureSchemaError, match="Invalid OHLC"):
            FixtureMarketDataAdapter(csv)
    
    def test_schema_strict_false_allows_minor_issues(self, tmp_path):
        """strict=False skips OHLC relationship checks."""
        csv = tmp_path / "relaxed.csv"
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00+00:00,100.0,95.0,105.0,100.0,1000\n"  # high < low but strict=False
        )
        
        # This would fail with strict=True, but passes with strict=False
        # Note: ohlcv_loader still validates NaN/duplicates/monotonicity
        # Only OHLC relationship check is skipped
        adapter = FixtureMarketDataAdapter(csv, strict=False)
        assert len(adapter) == 1
    
    # --- Gaps Detection Tests ---
    
    def test_gaps_detected_in_fixture(self, tmp_path):
        """Temporal gaps are detected and flagged."""
        csv = tmp_path / "gaps.csv"
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00+00:00,100.0,110.0,95.0,105.0,1000\n"
            "2024-01-15 01:00:00+00:00,105.0,115.0,100.0,110.0,1100\n"
            "2024-01-15 05:00:00+00:00,110.0,120.0,105.0,115.0,1200\n"  # 4-hour gap
        )
        
        adapter = FixtureMarketDataAdapter(csv)
        assert adapter.has_gaps is True
    
    def test_no_gaps_in_regular_fixture(self):
        """Regular fixture without gaps is flagged correctly."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        # The 3K1 fixture has hourly bars, no gaps
        assert adapter.has_gaps is False
    
    # --- NaN Handling Tests (via ohlcv_loader) ---
    
    def test_nan_in_ohlcv_raises_error(self, tmp_path):
        """NaN values in OHLCV columns trigger error (strict mode)."""
        csv = tmp_path / "nans.csv"
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00+00:00,100.0,110.0,95.0,,1000\n"  # NaN close
        )
        
        # ohlcv_loader raises ValueError for NaN in required columns
        with pytest.raises(ValueError, match="NaN"):
            FixtureMarketDataAdapter(csv)
    
    # --- UTC Enforcement Tests ---
    
    def test_utc_conversion_from_offset_timezone(self, tmp_path):
        """Timestamps with offset are converted to UTC epoch ms."""
        csv = tmp_path / "offset.csv"
        # 2024-01-15 00:00:00-05:00 = 2024-01-15 05:00:00 UTC
        csv.write_text(
            "timestamp,open,high,low,close,volume\n"
            "2024-01-15 00:00:00-05:00,100.0,110.0,95.0,105.0,1000\n"
        )
        
        adapter = FixtureMarketDataAdapter(csv)
        events = adapter.poll(max_items=1)
        
        # Expected: 2024-01-15 05:00:00 UTC = 1705294800000
        expected_ts = 1705294800000
        assert events[0].ts == expected_ts
    
    def test_utc_epoch_ms_is_integer(self):
        """All timestamps are integers (not floats)."""
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        for event in adapter.poll(max_items=100):
            assert isinstance(event.ts, int), f"ts is {type(event.ts)}, expected int"

