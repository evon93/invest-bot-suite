"""
engine/market_data/market_data_adapter.py

Protocol and dataclass for pluggable market data feeds.

AG-3K-1-1: Introduces MarketDataAdapter Protocol and MarketDataEvent.
AG-3K-1-2: Hardening - clarified poll() contract, EOF behavior, no-lookahead.
"""

from dataclasses import dataclass
from typing import Protocol, List, Optional


@dataclass(frozen=True)
class MarketDataEvent:
    """
    Single market data bar/tick.
    
    Attributes:
        ts: Timestamp as epoch milliseconds (int) in UTC.
             Must be non-decreasing across sequential poll() calls.
        symbol: Trading pair (e.g., "BTC/USDT").
        timeframe: Candle timeframe (e.g., "1h", "1m").
        open: Open price (must be > 0, non-NaN).
        high: High price (must be >= open, low, close).
        low: Low price (must be <= open, high, close).
        close: Close price (must be > 0, non-NaN).
        volume: Trade volume (must be >= 0, non-NaN).
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
        1. poll() returns events in strictly non-decreasing order by ts.
        2. poll() respects max_items limit (returns <= max_items).
        3. If up_to_ts is provided, only events with ts <= up_to_ts are returned.
           This enables verifiable no-lookahead behavior.
        4. After exhaustion (all events consumed), poll() returns empty list [].
           This is the EOF behavior - consistent and no exceptions.
        5. Calling poll() after exhaustion continues to return [].
        6. reset() (if available) restarts iteration from beginning.
    
    No-Lookahead Guarantee:
        When up_to_ts is provided, the adapter MUST NOT return any event
        with ts > up_to_ts. This allows callers to enforce "current time"
        boundaries and prevents future data leakage in backtests.
    
    EOF Behavior:
        - Returns [] when no more events are available.
        - Does NOT raise exceptions on exhaustion.
        - Subsequent calls continue to return [].
    
    Thread Safety:
        Implementations are NOT required to be thread-safe.
        Callers should synchronize access if needed.
    """
    
    def poll(
        self, 
        max_items: int = 100, 
        up_to_ts: Optional[int] = None
    ) -> List[MarketDataEvent]:
        """
        Fetch next batch of market data events.
        
        Args:
            max_items: Maximum number of events to return (default: 100).
            up_to_ts: Optional upper bound timestamp (epoch ms UTC).
                      If provided, only events with ts <= up_to_ts are returned.
                      Events beyond up_to_ts remain buffered for future polls.
                      
        Returns:
            List of MarketDataEvent in non-decreasing ts order.
            Returns empty list [] when exhausted (EOF).
            
        Contract:
            - len(result) <= max_items
            - All events satisfy: event.ts <= up_to_ts (if up_to_ts provided)
            - Events are ordered: result[i].ts <= result[i+1].ts
        """
        ...
