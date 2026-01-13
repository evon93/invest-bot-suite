"""
tests/test_ccxt_adapter.py

Unit tests for CCXTMarketDataAdapter.

AG-3K-2-1: Tests for CCXT adapter with network gating.
All tests use MockOHLCVClient - NO network calls.
"""

import pytest
import os
from pathlib import Path

from engine.market_data.ccxt_adapter import (
    CCXTMarketDataAdapter,
    CCXTConfig,
    MockOHLCVClient,
    NetworkDisabledError,
    ENV_ALLOW_NETWORK,
)
from engine.market_data.market_data_adapter import MarketDataEvent


class TestMockOHLCVClient:
    """Tests for MockOHLCVClient determinism."""
    
    def test_deterministic_data_generation(self):
        """Same seed produces same data."""
        client1 = MockOHLCVClient(seed=42)
        client2 = MockOHLCVClient(seed=42)
        
        data1 = client1.fetch_ohlcv("BTC/USDT")
        data2 = client2.fetch_ohlcv("BTC/USDT")
        
        assert data1 == data2
    
    def test_different_seeds_produce_different_data(self):
        """Different seeds produce different data."""
        client1 = MockOHLCVClient(seed=42)
        client2 = MockOHLCVClient(seed=123)
        
        data1 = client1.fetch_ohlcv("BTC/USDT")
        data2 = client2.fetch_ohlcv("BTC/USDT")
        
        assert data1 != data2
    
    def test_fetch_respects_since_filter(self):
        """since parameter filters out earlier data."""
        client = MockOHLCVClient(seed=42, n_bars=10)
        
        all_data = client.fetch_ohlcv("BTC/USDT")
        third_ts = all_data[2][0]  # ts of 3rd bar
        
        filtered = client.fetch_ohlcv("BTC/USDT", since=third_ts)
        
        assert len(filtered) < len(all_data)
        assert all(candle[0] > third_ts for candle in filtered)
    
    def test_fetch_respects_limit(self):
        """limit parameter caps results."""
        client = MockOHLCVClient(seed=42, n_bars=50)
        
        data = client.fetch_ohlcv("BTC/USDT", limit=5)
        
        assert len(data) == 5


class TestCCXTMarketDataAdapter:
    """Tests for CCXTMarketDataAdapter with mocked client."""
    
    def test_poll_returns_market_data_events(self):
        """poll() returns list of MarketDataEvent."""
        client = MockOHLCVClient(seed=42)
        config = CCXTConfig(symbol="BTC/USDT", timeframe="1h")
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        events = adapter.poll(max_items=5)
        
        assert len(events) == 5
        assert all(isinstance(e, MarketDataEvent) for e in events)
    
    def test_poll_events_have_correct_symbol(self):
        """Events have symbol from config."""
        client = MockOHLCVClient(seed=42)
        config = CCXTConfig(symbol="ETH/USDT", timeframe="4h")
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        events = adapter.poll(max_items=3)
        
        assert all(e.symbol == "ETH/USDT" for e in events)
        assert all(e.timeframe == "4h" for e in events)
    
    def test_poll_monotonic_timestamps(self):
        """Events are in non-decreasing ts order."""
        client = MockOHLCVClient(seed=42)
        config = CCXTConfig()
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        events = adapter.poll(max_items=20)
        
        for i in range(1, len(events)):
            assert events[i].ts >= events[i-1].ts
    
    def test_poll_up_to_ts_blocks_future(self):
        """up_to_ts prevents lookahead."""
        client = MockOHLCVClient(seed=42)
        config = CCXTConfig()
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        # Get first event's ts
        events = adapter.poll(max_items=1)
        first_ts = events[0].ts
        
        # Poll with boundary = first_ts + 1 hour
        boundary = first_ts + 3600000
        adapter2 = CCXTMarketDataAdapter(
            MockOHLCVClient(seed=42), 
            config, 
            allow_network=True
        )
        limited_events = adapter2.poll(max_items=100, up_to_ts=boundary)
        
        assert all(e.ts <= boundary for e in limited_events)
    
    def test_poll_respects_max_items(self):
        """poll() returns at most max_items."""
        client = MockOHLCVClient(seed=42, n_bars=100)
        config = CCXTConfig(limit=100)
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        events = adapter.poll(max_items=7)
        
        assert len(events) == 7
    
    def test_exhaustion_returns_empty_list(self):
        """After consuming all data, poll returns []."""
        client = MockOHLCVClient(seed=42, n_bars=5)
        config = CCXTConfig(limit=10)
        adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
        
        # Consume all
        adapter.poll(max_items=100)
        
        # Should be exhausted
        assert adapter.poll(max_items=10) == []
        assert adapter.is_exhausted()


class TestNetworkGating:
    """Tests for network gating behavior."""
    
    def test_network_disabled_raises_error(self):
        """poll() raises NetworkDisabledError when network not allowed."""
        # Ensure env var is not set
        old_val = os.environ.pop(ENV_ALLOW_NETWORK, None)
        try:
            client = MockOHLCVClient(seed=42)
            config = CCXTConfig()
            adapter = CCXTMarketDataAdapter(client, config, allow_network=False)
            
            with pytest.raises(NetworkDisabledError, match="Network access disabled"):
                adapter.poll()
        finally:
            if old_val is not None:
                os.environ[ENV_ALLOW_NETWORK] = old_val
    
    def test_env_var_enables_network(self):
        """ENV_ALLOW_NETWORK=1 enables network."""
        old_val = os.environ.get(ENV_ALLOW_NETWORK)
        try:
            os.environ[ENV_ALLOW_NETWORK] = "1"
            
            client = MockOHLCVClient(seed=42)
            config = CCXTConfig()
            adapter = CCXTMarketDataAdapter(client, config, allow_network=False)
            
            # Should NOT raise - env var overrides allow_network=False
            events = adapter.poll(max_items=5)
            assert len(events) == 5
        finally:
            if old_val is None:
                os.environ.pop(ENV_ALLOW_NETWORK, None)
            else:
                os.environ[ENV_ALLOW_NETWORK] = old_val
    
    def test_allow_network_flag_enables(self):
        """allow_network=True enables network."""
        old_val = os.environ.pop(ENV_ALLOW_NETWORK, None)
        try:
            client = MockOHLCVClient(seed=42)
            config = CCXTConfig()
            adapter = CCXTMarketDataAdapter(client, config, allow_network=True)
            
            # Should NOT raise
            events = adapter.poll(max_items=5)
            assert len(events) == 5
        finally:
            if old_val is not None:
                os.environ[ENV_ALLOW_NETWORK] = old_val
    
    def test_error_message_includes_instructions(self):
        """NetworkDisabledError message includes how to enable."""
        old_val = os.environ.pop(ENV_ALLOW_NETWORK, None)
        try:
            client = MockOHLCVClient(seed=42)
            config = CCXTConfig()
            adapter = CCXTMarketDataAdapter(client, config, allow_network=False)
            
            with pytest.raises(NetworkDisabledError) as exc_info:
                adapter.poll()
            
            msg = str(exc_info.value)
            assert "--allow-network" in msg
            assert ENV_ALLOW_NETWORK in msg
        finally:
            if old_val is not None:
                os.environ[ENV_ALLOW_NETWORK] = old_val


class TestRunnerCCXTMode:
    """Integration tests for runner with CCXT mode."""
    
    def test_ccxt_without_allow_network_fails(self, tmp_path):
        """Runner with --data ccxt but no --allow-network exits with error."""
        import subprocess
        
        result = subprocess.run(
            [
                "python", "tools/run_live_3E.py",
                "--data", "ccxt",
                "--outdir", str(tmp_path / "out"),
                "--max-steps", "5",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            env={**os.environ, ENV_ALLOW_NETWORK: ""},  # Ensure disabled
        )
        
        assert result.returncode != 0
        assert "requires --allow-network" in result.stdout or "allow-network" in result.stderr
    
    def test_ccxt_with_allow_network_runs(self, tmp_path):
        """Runner with --data ccxt --allow-network succeeds (uses mock fallback)."""
        import subprocess
        
        outdir = tmp_path / "out_ccxt"
        
        result = subprocess.run(
            [
                "python", "tools/run_live_3E.py",
                "--data", "ccxt",
                "--allow-network",
                "--outdir", str(outdir),
                "--max-steps", "5",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
        )
        
        # Should succeed (using mock fallback since ccxt not installed)
        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert (outdir / "events.ndjson").exists()
