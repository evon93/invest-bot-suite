"""
engine/market_data/ccxt_adapter.py

CCXT-based market data adapter with network gating.

AG-3K-2-1: Gated CCXT sandbox feed - no network calls without explicit opt-in.

Note: ccxt is NOT a required dependency. This adapter uses a Protocol for the
client interface, allowing injection of mock clients for testing without network.
If ccxt is installed, it can be used as the real client implementation.
"""

from pathlib import Path
from typing import List, Optional, Protocol, Dict, Any, Callable
from dataclasses import dataclass
import logging
import os

from engine.market_data.market_data_adapter import MarketDataEvent


logger = logging.getLogger(__name__)


# Environment variable for network gating
ENV_ALLOW_NETWORK = "INVESTBOT_ALLOW_NETWORK"


class NetworkDisabledError(RuntimeError):
    """Raised when network access is attempted without explicit opt-in."""
    pass


class OHLCVClient(Protocol):
    """
    Protocol for OHLCV data client (ccxt-like interface).
    
    Implementations must provide fetch_ohlcv() with ccxt-compatible signature.
    This allows injection of mock clients for testing without network.
    """
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[List]:
        """
        Fetch OHLCV data.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT").
            timeframe: Candle timeframe (e.g., "1h", "1m").
            since: Optional start timestamp (epoch ms UTC).
            limit: Optional max number of candles to fetch.
            
        Returns:
            List of [timestamp_ms, open, high, low, close, volume] lists.
        """
        ...


@dataclass
class CCXTConfig:
    """Configuration for CCXT adapter."""
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = 100
    since: Optional[int] = None  # epoch ms UTC
    
    def __post_init__(self):
        # Normalize exchange name
        self.exchange = self.exchange.lower()


class CCXTMarketDataAdapter:
    """
    Market data adapter using CCXT-compatible client.
    
    Features:
        - Network gating: requires explicit --allow-network or env var
        - Client injection for testing without network
        - Respects up_to_ts for no-lookahead guarantee
        - Buffer management for sequential poll()
    
    Gating:
        Network calls are blocked unless:
        - allow_network=True is passed to constructor, OR
        - INVESTBOT_ALLOW_NETWORK=1 env var is set
        
        Without gating enabled, any attempt to poll() raises NetworkDisabledError.
    """
    
    def __init__(
        self,
        client: OHLCVClient,
        config: CCXTConfig,
        allow_network: bool = False,
    ):
        """
        Initialize CCXT adapter.
        
        Args:
            client: OHLCV client implementing OHLCVClient protocol.
            config: CCXT configuration.
            allow_network: Explicit network opt-in (default: False).
            
        Note:
            Network is allowed if allow_network=True OR env var INVESTBOT_ALLOW_NETWORK=1.
        """
        self.client = client
        self.config = config
        
        # Check network gating
        env_allow = os.environ.get(ENV_ALLOW_NETWORK, "").lower() in ("1", "true", "yes")
        self._network_allowed = allow_network or env_allow
        
        # Internal buffer for events
        self._buffer: List[MarketDataEvent] = []
        self._exhausted = False
        self._last_fetch_ts: Optional[int] = None
    
    def _check_network_gating(self) -> None:
        """Check if network is allowed, raise if not."""
        if not self._network_allowed:
            raise NetworkDisabledError(
                "Network access disabled. Use --allow-network flag or set "
                f"{ENV_ALLOW_NETWORK}=1 environment variable to enable."
            )
    
    def _fetch_and_buffer(self, up_to_ts: Optional[int] = None) -> None:
        """
        Fetch new data from client and add to buffer.
        
        Args:
            up_to_ts: Optional upper bound - don't fetch beyond this.
        """
        self._check_network_gating()
        
        # Determine 'since' for next fetch
        since = self._last_fetch_ts
        if since is None:
            since = self.config.since
        
        try:
            raw = self.client.fetch_ohlcv(
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                since=since,
                limit=self.config.limit,
            )
        except Exception as e:
            logger.error(f"CCXT fetch failed: {e}")
            self._exhausted = True
            return
        
        if not raw:
            logger.debug("CCXT returned empty data - marking exhausted")
            self._exhausted = True
            return
        
        # Convert to MarketDataEvent
        for candle in raw:
            # ccxt format: [timestamp_ms, open, high, low, close, volume]
            ts = int(candle[0])
            
            # Skip if we've already seen this timestamp
            if self._last_fetch_ts is not None and ts <= self._last_fetch_ts:
                continue
            
            event = MarketDataEvent(
                ts=ts,
                symbol=self.config.symbol,
                timeframe=self.config.timeframe,
                open=float(candle[1]),
                high=float(candle[2]),
                low=float(candle[3]),
                close=float(candle[4]),
                volume=float(candle[5]),
            )
            self._buffer.append(event)
        
        # Update last fetch timestamp
        if raw:
            self._last_fetch_ts = int(raw[-1][0])
        
        # Check if we got fewer than requested - likely exhausted
        if len(raw) < self.config.limit:
            self._exhausted = True
    
    def poll(
        self,
        max_items: int = 100,
        up_to_ts: Optional[int] = None,
    ) -> List[MarketDataEvent]:
        """
        Fetch next batch of market data events.
        
        Args:
            max_items: Maximum number of events to return.
            up_to_ts: Optional upper bound timestamp (epoch ms UTC).
                      Only events with ts <= up_to_ts are returned.
                      
        Returns:
            List of MarketDataEvent in non-decreasing ts order.
            Empty list when exhausted (EOF).
            
        Raises:
            NetworkDisabledError: If network is not allowed.
        """
        # If buffer empty and not exhausted, fetch more
        if not self._buffer and not self._exhausted:
            self._fetch_and_buffer(up_to_ts)
        
        # Extract events respecting up_to_ts
        result = []
        remaining = []
        
        for event in self._buffer:
            if len(result) >= max_items:
                remaining.append(event)
            elif up_to_ts is not None and event.ts > up_to_ts:
                remaining.append(event)
            else:
                result.append(event)
        
        self._buffer = remaining
        return result
    
    def peek_next_ts(self) -> Optional[int]:
        """Peek at next event's timestamp without consuming."""
        if not self._buffer and not self._exhausted:
            self._fetch_and_buffer()
        
        if self._buffer:
            return self._buffer[0].ts
        return None
    
    def is_exhausted(self) -> bool:
        """Check if adapter has no more data to provide."""
        return self._exhausted and not self._buffer
    
    def remaining(self) -> int:
        """Number of buffered events remaining."""
        return len(self._buffer)


def create_ccxt_client(exchange: str) -> OHLCVClient:
    """
    Factory function to create real CCXT client.
    
    Args:
        exchange: Exchange name (e.g., "binance", "kraken").
        
    Returns:
        OHLCVClient instance.
        
    Raises:
        ImportError: If ccxt is not installed.
        
    Note:
        This function requires ccxt package to be installed.
        For testing, use MockOHLCVClient instead.
    """
    try:
        import ccxt
    except ImportError:
        raise ImportError(
            "ccxt package not installed. Install with: pip install ccxt\n"
            "For testing without network, use MockOHLCVClient instead."
        )
    
    exchange_class = getattr(ccxt, exchange, None)
    if exchange_class is None:
        raise ValueError(f"Unknown exchange: {exchange}")
    
    return exchange_class({"enableRateLimit": True})


class MockOHLCVClient:
    """
    Mock OHLCV client for testing without network.
    
    Generates deterministic fake data based on seed.
    """
    
    def __init__(
        self,
        seed: int = 42,
        n_bars: int = 50,
        start_ts: int = 1705276800000,  # 2024-01-15 00:00:00 UTC
        interval_ms: int = 3600000,  # 1 hour
    ):
        """
        Initialize mock client.
        
        Args:
            seed: Random seed for determinism.
            n_bars: Number of bars to generate.
            start_ts: Start timestamp (epoch ms UTC).
            interval_ms: Interval between bars in milliseconds.
        """
        import random
        self._rng = random.Random(seed)
        self._n_bars = n_bars
        self._start_ts = start_ts
        self._interval_ms = interval_ms
        self._generated = self._generate_data()
    
    def _generate_data(self) -> List[List]:
        """Generate fake OHLCV data."""
        data = []
        price = 42000.0
        
        for i in range(self._n_bars):
            ts = self._start_ts + i * self._interval_ms
            change = self._rng.uniform(-0.02, 0.02)
            open_ = price
            close = price * (1 + change)
            high = max(open_, close) * (1 + self._rng.uniform(0, 0.01))
            low = min(open_, close) * (1 - self._rng.uniform(0, 0.01))
            volume = self._rng.uniform(100, 10000)
            
            data.append([ts, open_, high, low, close, volume])
            price = close
        
        return data
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[List]:
        """
        Return pre-generated data.
        
        Filters by 'since' and respects 'limit'.
        """
        result = self._generated
        
        if since is not None:
            result = [c for c in result if c[0] > since]
        
        if limit is not None:
            result = result[:limit]
        
        return result
