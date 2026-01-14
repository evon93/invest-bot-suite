"""
tests/test_ccxt_market_data_mock_parity_3L2.py

Offline parity tests for CCXT adapter normalization.

AG-3L-2-1: These tests verify that:
- MockOHLCVClient produces same schema as real CCXT
- Normalization logic works without network
- No ccxt import required (uses sample data)
"""

import pytest
from typing import List


class TestMockClientParity:
    """Parity tests between MockOHLCVClient and real CCXT format."""
    
    # Sample OHLCV data in CCXT format: [[timestamp_ms, open, high, low, close, volume], ...]
    SAMPLE_CCXT_OHLCV = [
        [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],  # 2024-01-15 00:00:00 UTC
        [1705280400000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],  # 2024-01-15 01:00:00 UTC
        [1705284000000, 42600.0, 42900.0, 42400.0, 42700.0, 800.0],   # 2024-01-15 02:00:00 UTC
    ]
    
    def test_mock_client_produces_ccxt_format(self):
        """MockOHLCVClient.fetch_ohlcv() returns CCXT-compatible list structure."""
        from engine.market_data.ccxt_adapter import MockOHLCVClient
        
        client = MockOHLCVClient(seed=42, n_bars=5)
        result = client.fetch_ohlcv("BTC/USDT", timeframe="1h")
        
        # Check structure matches CCXT format
        assert isinstance(result, list), "Should return list"
        assert len(result) == 5, "Should have 5 bars"
        
        # Each candle should have 6 elements
        for i, candle in enumerate(result):
            assert isinstance(candle, list), f"Candle {i} should be list"
            assert len(candle) == 6, f"Candle {i} should have 6 elements [ts, o, h, l, c, v]"
            
            ts, o, h, l, c, v = candle
            
            # Type checks
            assert isinstance(ts, (int, float)), f"Candle {i} timestamp should be numeric"
            assert isinstance(o, float), f"Candle {i} open should be float"
            assert isinstance(h, float), f"Candle {i} high should be float"
            assert isinstance(l, float), f"Candle {i} low should be float"
            assert isinstance(c, float), f"Candle {i} close should be float"
            assert isinstance(v, float), f"Candle {i} volume should be float"
    
    def test_mock_client_timestamps_are_epoch_ms(self):
        """Timestamps are in epoch milliseconds (not seconds)."""
        from engine.market_data.ccxt_adapter import MockOHLCVClient
        
        client = MockOHLCVClient(
            seed=42, 
            n_bars=3,
            start_ts=1705276800000,  # Known epoch ms
            interval_ms=3600000,  # 1 hour
        )
        result = client.fetch_ohlcv("BTC/USDT")
        
        # Check timestamps
        expected_ts = [
            1705276800000,
            1705280400000,
            1705284000000,
        ]
        
        for i, candle in enumerate(result):
            assert candle[0] == expected_ts[i], f"Candle {i} timestamp mismatch"
    
    def test_mock_client_ohlc_relationships_valid(self):
        """Mock data has valid OHLC relationships (high >= open, close; low <= open, close)."""
        from engine.market_data.ccxt_adapter import MockOHLCVClient
        
        client = MockOHLCVClient(seed=42, n_bars=20)
        result = client.fetch_ohlcv("BTC/USDT")
        
        for i, candle in enumerate(result):
            _, o, h, l, c, v = candle
            
            assert h >= o, f"Candle {i}: high {h} should be >= open {o}"
            assert h >= c, f"Candle {i}: high {h} should be >= close {c}"
            assert l <= o, f"Candle {i}: low {l} should be <= open {o}"
            assert l <= c, f"Candle {i}: low {l} should be <= close {c}"
            assert v >= 0, f"Candle {i}: volume should be non-negative"
    
    def test_mock_client_respects_limit_parameter(self):
        """fetch_ohlcv(limit=N) returns at most N candles."""
        from engine.market_data.ccxt_adapter import MockOHLCVClient
        
        client = MockOHLCVClient(seed=42, n_bars=50)
        
        result = client.fetch_ohlcv("BTC/USDT", limit=5)
        assert len(result) == 5
        
        result = client.fetch_ohlcv("BTC/USDT", limit=1)
        assert len(result) == 1
    
    def test_mock_client_respects_since_parameter(self):
        """fetch_ohlcv(since=X) returns only candles with ts > X."""
        from engine.market_data.ccxt_adapter import MockOHLCVClient
        
        client = MockOHLCVClient(
            seed=42, 
            n_bars=5,
            start_ts=1705276800000,
            interval_ms=3600000,
        )
        
        # Skip first two bars
        since_ts = 1705280400000  # Second bar timestamp
        result = client.fetch_ohlcv("BTC/USDT", since=since_ts)
        
        # Should only return bars after since_ts
        for candle in result:
            assert candle[0] > since_ts, f"Candle ts {candle[0]} should be > {since_ts}"


class TestAdapterNormalization:
    """Test that CCXTMarketDataAdapter normalizes correctly."""
    
    def test_adapter_converts_to_market_data_event(self):
        """Adapter converts CCXT format to MarketDataEvent."""
        from engine.market_data.ccxt_adapter import (
            CCXTMarketDataAdapter, CCXTConfig, MockOHLCVClient
        )
        from engine.market_data.market_data_adapter import MarketDataEvent
        
        client = MockOHLCVClient(seed=42, n_bars=5)
        config = CCXTConfig(
            exchange="mock",
            symbol="BTC/USDT",
            timeframe="1h",
            limit=5,
        )
        
        adapter = CCXTMarketDataAdapter(
            client=client,
            config=config,
            allow_network=True,  # MockClient doesn't need network but adapter checks
        )
        
        events = adapter.poll(max_items=3)
        
        assert len(events) == 3
        
        for event in events:
            assert isinstance(event, MarketDataEvent)
            assert event.symbol == "BTC/USDT"
            assert event.timeframe == "1h"
            assert isinstance(event.ts, int)
            assert isinstance(event.open, float)
            assert isinstance(event.high, float)
            assert isinstance(event.low, float)
            assert isinstance(event.close, float)
            assert isinstance(event.volume, float)
    
    def test_adapter_timestamps_are_integers(self):
        """Adapter converts timestamps to int (not float)."""
        from engine.market_data.ccxt_adapter import (
            CCXTMarketDataAdapter, CCXTConfig, MockOHLCVClient
        )
        
        client = MockOHLCVClient(seed=42, n_bars=5)
        config = CCXTConfig(symbol="ETH/USDT", limit=5)
        
        adapter = CCXTMarketDataAdapter(
            client=client,
            config=config,
            allow_network=True,
        )
        
        events = adapter.poll(max_items=5)
        
        for event in events:
            assert isinstance(event.ts, int), f"ts should be int, got {type(event.ts)}"
    
    def test_adapter_events_are_ordered(self):
        """Events from adapter are in non-decreasing ts order."""
        from engine.market_data.ccxt_adapter import (
            CCXTMarketDataAdapter, CCXTConfig, MockOHLCVClient
        )
        
        client = MockOHLCVClient(seed=42, n_bars=10)
        config = CCXTConfig(symbol="BTC/USDT", limit=10)
        
        adapter = CCXTMarketDataAdapter(
            client=client,
            config=config,
            allow_network=True,
        )
        
        events = adapter.poll(max_items=10)
        
        for i in range(1, len(events)):
            assert events[i].ts >= events[i-1].ts, f"Events not ordered at {i}"


class TestSampleDataParity:
    """Test adapter with known sample data."""
    
    def test_sample_ccxt_ohlcv_normalizes_correctly(self):
        """Sample CCXT data normalizes to expected MarketDataEvent values."""
        from engine.market_data.ccxt_adapter import CCXTMarketDataAdapter, CCXTConfig
        from engine.market_data.market_data_adapter import MarketDataEvent
        
        # Create a simple client that returns our sample data
        class SampleClient:
            def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=None):
                data = [
                    [1705276800000, 42000.0, 42500.0, 41800.0, 42300.0, 1000.0],
                    [1705280400000, 42300.0, 42800.0, 42200.0, 42600.0, 1200.0],
                ]
                if limit:
                    data = data[:limit]
                return data
        
        config = CCXTConfig(symbol="BTC/USDT", timeframe="1h", limit=2)
        adapter = CCXTMarketDataAdapter(
            client=SampleClient(),
            config=config,
            allow_network=True,
        )
        
        events = adapter.poll(max_items=2)
        
        # Verify first event
        assert events[0].ts == 1705276800000
        assert events[0].open == 42000.0
        assert events[0].high == 42500.0
        assert events[0].low == 41800.0
        assert events[0].close == 42300.0
        assert events[0].volume == 1000.0
        
        # Verify second event
        assert events[1].ts == 1705280400000
        assert events[1].open == 42300.0
