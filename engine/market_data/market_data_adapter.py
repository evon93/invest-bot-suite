"""
engine/market_data/market_data_adapter.py

Protocol and dataclass for pluggable market data feeds.

AG-3K-1-1: Introduces MarketDataAdapter Protocol and MarketDataEvent.
"""

from dataclasses import dataclass
from typing import Protocol, List


@dataclass(frozen=True)
class MarketDataEvent:
    """
    Single market data bar/tick.
    
    Attributes:
        ts: Timestamp as epoch milliseconds (int) in UTC.
        symbol: Trading pair (e.g., "BTC/USDT").
        timeframe: Candle timeframe (e.g., "1h", "1m").
        open: Open price.
        high: High price.
        low: Low price.
        close: Close price.
        volume: Trade volume.
    """
    ts: int  # epoch milliseconds UTC
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataAdapter(Protocol):
    """
    Protocol for market data feed adapters.
    
    Implementations must provide sequential, non-lookahead access to market data.
    
    Contract:
        - poll() returns events in non-decreasing order by ts.
        - poll() respects max_items limit.
        - After exhaustion, poll() returns empty list.
    """
    
    def poll(self, max_items: int = 100) -> List[MarketDataEvent]:
        """
        Fetch next batch of market data events.
        
        Args:
            max_items: Maximum number of events to return.
            
        Returns:
            List of MarketDataEvent in non-decreasing ts order.
            Returns empty list when exhausted.
        """
        ...
