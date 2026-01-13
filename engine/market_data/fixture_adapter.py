"""
engine/market_data/fixture_adapter.py

Offline deterministic market data adapter for CI/testing.

AG-3K-1-1: FixtureMarketDataAdapter loads CSV fixtures using existing ohlcv_loader.
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd

from data_adapters.ohlcv_loader import load_ohlcv
from engine.market_data.market_data_adapter import MarketDataEvent


class FixtureMarketDataAdapter:
    """
    Offline market data adapter that reads from CSV/Parquet fixtures.
    
    Uses data_adapters.ohlcv_loader for loading and normalization (UTC, validation).
    Emits events sequentially via poll() - no lookahead.
    
    Attributes:
        symbol: Trading pair symbol.
        timeframe: Candle timeframe.
    """
    
    def __init__(
        self,
        fixture_path: Path,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
    ):
        """
        Initialize adapter with fixture file.
        
        Args:
            fixture_path: Path to CSV or Parquet file with OHLCV data.
            symbol: Trading pair symbol (default: BTC/USDT).
            timeframe: Candle timeframe (default: 1h).
            
        Raises:
            FileNotFoundError: If fixture_path doesn't exist.
            ValueError: If fixture has invalid data (via ohlcv_loader).
        """
        self.fixture_path = Path(fixture_path)
        self.symbol = symbol
        self.timeframe = timeframe
        
        # Load and validate via ohlcv_loader (handles normalization, UTC, duplicates, etc.)
        self._df = load_ohlcv(self.fixture_path)
        
        # Convert timestamps to epoch ms
        self._events = self._build_events()
        self._idx = 0
    
    def _build_events(self) -> List[MarketDataEvent]:
        """Build list of MarketDataEvent from loaded DataFrame."""
        events = []
        for row in self._df.itertuples():
            # row.timestamp is datetime64 with UTC tz
            ts_ms = int(row.timestamp.timestamp() * 1000)
            events.append(MarketDataEvent(
                ts=ts_ms,
                symbol=self.symbol,
                timeframe=self.timeframe,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
            ))
        return events
    
    def poll(self, max_items: int = 100) -> List[MarketDataEvent]:
        """
        Fetch next batch of events.
        
        Args:
            max_items: Maximum number of events to return.
            
        Returns:
            List of MarketDataEvent, up to max_items, in ts order.
            Empty list when exhausted.
        """
        if self._idx >= len(self._events):
            return []
        
        end_idx = min(self._idx + max_items, len(self._events))
        batch = self._events[self._idx:end_idx]
        self._idx = end_idx
        return batch
    
    def reset(self) -> None:
        """Reset adapter to beginning for re-iteration."""
        self._idx = 0
    
    def remaining(self) -> int:
        """Return number of events remaining."""
        return len(self._events) - self._idx
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the underlying OHLCV DataFrame.
        
        Useful for compatibility with existing code that expects DataFrame input.
        """
        return self._df.copy()
    
    def __len__(self) -> int:
        """Total number of events in fixture."""
        return len(self._events)
