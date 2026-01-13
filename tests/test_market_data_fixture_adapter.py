"""
tests/test_market_data_fixture_adapter.py

Unit tests for FixtureMarketDataAdapter.

AG-3K-1-1: Tests for poll(), ordering, epoch ms conversion, and no-lookahead.
"""

import pytest
from pathlib import Path
import subprocess
import json

from engine.market_data.fixture_adapter import FixtureMarketDataAdapter
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
