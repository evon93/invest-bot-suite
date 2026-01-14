"""
tests/test_ccxt_market_data_real_gated_3L2.py

Gated tests for real CCXT network access.

AG-3L-2-1: These tests ONLY run when:
- ccxt package is installed
- INVESTBOT_ALLOW_NETWORK=1
- INVESTBOT_CCXT_EXCHANGE is set
- INVESTBOT_CCXT_SYMBOL is set

In CI/offline environments, these tests are automatically SKIPPED.
"""

import os
import pytest
from typing import Optional


# Environment variable names (DO NOT log values - security)
ENV_ALLOW_NETWORK = "INVESTBOT_ALLOW_NETWORK"
ENV_CCXT_EXCHANGE = "INVESTBOT_CCXT_EXCHANGE"
ENV_CCXT_SYMBOL = "INVESTBOT_CCXT_SYMBOL"
ENV_CCXT_API_KEY = "INVESTBOT_CCXT_API_KEY"
ENV_CCXT_API_SECRET = "INVESTBOT_CCXT_API_SECRET"


def _env_present(name: str) -> bool:
    """Check if env var is present (don't log value)."""
    return bool(os.environ.get(name, "").strip())


def _get_env(name: str) -> Optional[str]:
    """Get env var value (caller responsible for not logging sensitive ones)."""
    val = os.environ.get(name, "").strip()
    return val if val else None


# Module-level skip conditions
ccxt = pytest.importorskip("ccxt", reason="ccxt not installed - skip real network tests")


@pytest.fixture(scope="module")
def network_allowed():
    """Check if network is allowed."""
    allowed = os.environ.get(ENV_ALLOW_NETWORK, "").lower() in ("1", "true", "yes")
    if not allowed:
        pytest.skip(f"{ENV_ALLOW_NETWORK} not set to '1' - skipping real network test")
    return True


@pytest.fixture(scope="module")
def ccxt_config(network_allowed):
    """Get CCXT configuration from environment."""
    exchange = _get_env(ENV_CCXT_EXCHANGE)
    symbol = _get_env(ENV_CCXT_SYMBOL)
    
    # Log presence, not values
    print(f"  {ENV_CCXT_EXCHANGE}: {'present' if exchange else 'MISSING'}")
    print(f"  {ENV_CCXT_SYMBOL}: {'present' if symbol else 'MISSING'}")
    print(f"  {ENV_CCXT_API_KEY}: {'present' if _env_present(ENV_CCXT_API_KEY) else 'not set (optional)'}")
    print(f"  {ENV_CCXT_API_SECRET}: {'present' if _env_present(ENV_CCXT_API_SECRET) else 'not set (optional)'}")
    
    if not exchange:
        pytest.skip(f"{ENV_CCXT_EXCHANGE} not set - skipping real network test")
    if not symbol:
        pytest.skip(f"{ENV_CCXT_SYMBOL} not set - skipping real network test")
    
    return {
        "exchange": exchange,
        "symbol": symbol,
        "api_key": _get_env(ENV_CCXT_API_KEY),
        "api_secret": _get_env(ENV_CCXT_API_SECRET),
    }


class TestCCXTRealNetworkGated:
    """Gated tests that require real network access."""
    
    def test_ccxt_can_fetch_ohlcv(self, ccxt_config):
        """
        Fetch OHLCV from real exchange.
        
        This test:
        - Uses short timeout
        - Fetches only 2 candles max
        - Does NOT log sensitive data
        """
        exchange_name = ccxt_config["exchange"]
        symbol = ccxt_config["symbol"]
        
        # Get exchange class
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            pytest.skip(f"Unknown exchange: {exchange_name}")
        
        # Create exchange with rate limiting
        config = {"enableRateLimit": True, "timeout": 10000}  # 10s timeout
        
        if ccxt_config.get("api_key"):
            config["apiKey"] = ccxt_config["api_key"]
        if ccxt_config.get("api_secret"):
            config["secret"] = ccxt_config["api_secret"]
        
        exchange = exchange_class(config)
        
        try:
            # Fetch only 2 candles with short limit
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=2)
            
            # Basic validation
            assert isinstance(ohlcv, list), "OHLCV should be a list"
            assert len(ohlcv) >= 1, "Should have at least 1 candle"
            
            # Validate candle structure
            candle = ohlcv[0]
            assert len(candle) == 6, "Candle should have 6 elements [ts, o, h, l, c, v]"
            assert isinstance(candle[0], (int, float)), "Timestamp should be numeric"
            assert candle[0] > 0, "Timestamp should be positive"
            
            print(f"  Successfully fetched {len(ohlcv)} candle(s) from {exchange_name}")
            
        except ccxt.NetworkError as e:
            pytest.fail(f"Network error (check connectivity): {type(e).__name__}")
        except ccxt.ExchangeError as e:
            pytest.fail(f"Exchange error (check symbol/permissions): {type(e).__name__}")
        except ccxt.BaseError as e:
            pytest.fail(f"CCXT error: {type(e).__name__}")
        finally:
            # Close exchange connection
            if hasattr(exchange, 'close'):
                try:
                    exchange.close()
                except Exception:
                    pass
    
    def test_ccxt_adapter_integration(self, ccxt_config):
        """
        Test CCXTMarketDataAdapter with real exchange.
        
        Uses the adapter with real client to verify full integration.
        """
        from engine.market_data.ccxt_adapter import (
            CCXTMarketDataAdapter, CCXTConfig, create_ccxt_client
        )
        
        exchange_name = ccxt_config["exchange"]
        symbol = ccxt_config["symbol"]
        
        try:
            client = create_ccxt_client(exchange_name)
        except ImportError:
            pytest.skip("ccxt not available for create_ccxt_client")
        
        config = CCXTConfig(
            exchange=exchange_name,
            symbol=symbol,
            timeframe="1h",
            limit=2,
        )
        
        adapter = CCXTMarketDataAdapter(
            client=client,
            config=config,
            allow_network=True,
        )
        
        # Poll once
        events = adapter.poll(max_items=2)
        
        assert len(events) >= 1, "Should have at least 1 event"
        
        event = events[0]
        assert event.symbol == symbol
        assert event.ts > 0
        assert event.open > 0
        assert event.close > 0
        
        print(f"  Adapter fetched {len(events)} event(s)")
