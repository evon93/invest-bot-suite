"""
engine/market_data/fixture_adapter.py

Offline deterministic market data adapter for CI/testing.

AG-3K-1-1: FixtureMarketDataAdapter loads CSV fixtures using existing ohlcv_loader.
AG-3K-1-2: Hardening - schema validation, no-lookahead via up_to_ts, gaps awareness.
"""

from pathlib import Path
from typing import List, Optional
import logging
import pandas as pd

from data_adapters.ohlcv_loader import load_ohlcv, REQUIRED_COLUMNS
from engine.market_data.market_data_adapter import MarketDataEvent


logger = logging.getLogger(__name__)


# Expected schema for fixture files
FIXTURE_SCHEMA = {
    "required_columns": REQUIRED_COLUMNS,  # ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    "numeric_columns": ["open", "high", "low", "close", "volume"],
}


class FixtureSchemaError(ValueError):
    """Raised when fixture file doesn't match expected schema."""
    pass


class FixtureMarketDataAdapter:
    """
    Offline market data adapter that reads from CSV/Parquet fixtures.
    
    Uses data_adapters.ohlcv_loader for loading and normalization (UTC, validation).
    Emits events sequentially via poll() - enforces no-lookahead.
    
    Schema Validation:
        - ohlcv_loader validates: columns, NaNs, duplicates, monotonicity
        - This adapter validates: positive prices, valid OHLC relationships
    
    Gaps Handling:
        - Gaps in timestamps are preserved (not interpolated).
        - ohlcv_loader logs warnings for detected gaps.
        - Events are emitted in original order regardless of gaps.
    
    NaN Handling (strict mode):
        - ohlcv_loader raises ValueError on NaN in required columns.
        - This adapter does not allow NaN values.
    
    Attributes:
        symbol: Trading pair symbol.
        timeframe: Candle timeframe.
        has_gaps: True if temporal gaps were detected in fixture.
    """
    
    def __init__(
        self,
        fixture_path: Path,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        strict: bool = True,
    ):
        """
        Initialize adapter with fixture file.
        
        Args:
            fixture_path: Path to CSV or Parquet file with OHLCV data.
            symbol: Trading pair symbol (default: BTC/USDT).
            timeframe: Candle timeframe (default: 1h).
            strict: If True, validate OHLC relationships (default: True).
            
        Raises:
            FileNotFoundError: If fixture_path doesn't exist.
            ValueError: If fixture has invalid data (via ohlcv_loader).
            FixtureSchemaError: If fixture fails schema validation.
        """
        self.fixture_path = Path(fixture_path)
        self.symbol = symbol
        self.timeframe = timeframe
        self.strict = strict
        
        # Load and validate via ohlcv_loader (handles normalization, UTC, duplicates, NaNs)
        self._df = load_ohlcv(self.fixture_path)
        
        # Additional schema validation
        self._validate_schema()
        
        # Detect gaps for informational purposes
        self.has_gaps = self._detect_gaps()
        
        # Convert timestamps to epoch ms
        self._events = self._build_events()
        self._idx = 0
    
    def _validate_schema(self) -> None:
        """
        Validate fixture schema beyond ohlcv_loader checks.
        
        Raises:
            FixtureSchemaError: If validation fails.
        """
        df = self._df
        
        # Check for required columns (redundant but explicit)
        missing = [c for c in FIXTURE_SCHEMA["required_columns"] if c not in df.columns]
        if missing:
            raise FixtureSchemaError(f"Missing required columns: {missing}")
        
        if not self.strict:
            return
        
        # Validate positive prices
        for col in ["open", "high", "low", "close"]:
            if (df[col] <= 0).any():
                raise FixtureSchemaError(f"Column '{col}' contains non-positive values")
        
        # Validate volume non-negative
        if (df["volume"] < 0).any():
            raise FixtureSchemaError("Column 'volume' contains negative values")
        
        # Validate OHLC relationships: high >= max(open, close), low <= min(open, close)
        high_valid = (df["high"] >= df["open"]) & (df["high"] >= df["close"])
        low_valid = (df["low"] <= df["open"]) & (df["low"] <= df["close"])
        
        if not high_valid.all():
            invalid_idx = df.index[~high_valid].tolist()
            raise FixtureSchemaError(
                f"Invalid OHLC: high < open or close at indices: {invalid_idx[:5]}"
            )
        
        if not low_valid.all():
            invalid_idx = df.index[~low_valid].tolist()
            raise FixtureSchemaError(
                f"Invalid OHLC: low > open or close at indices: {invalid_idx[:5]}"
            )
    
    def _detect_gaps(self) -> bool:
        """Detect if fixture has temporal gaps. Returns True if gaps exist."""
        if len(self._df) < 2:
            return False
        
        deltas = self._df["timestamp"].diff().dropna()
        if len(deltas) == 0:
            return False
            
        median_delta = deltas.median()
        # Gap = delta > 1.5x median
        gap_count = (deltas > 1.5 * median_delta).sum()
        
        if gap_count > 0:
            logger.info(f"Fixture has {gap_count} temporal gaps (median delta: {median_delta})")
            return True
        return False
    
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
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            ))
        return events
    
    def poll(
        self, 
        max_items: int = 100, 
        up_to_ts: Optional[int] = None
    ) -> List[MarketDataEvent]:
        """
        Fetch next batch of events.
        
        Args:
            max_items: Maximum number of events to return.
            up_to_ts: Optional upper bound timestamp (epoch ms UTC).
                      If provided, only events with ts <= up_to_ts are returned.
                      Events beyond up_to_ts remain buffered for future polls.
                      
        Returns:
            List of MarketDataEvent, up to max_items, in ts order.
            Empty list [] when exhausted (EOF).
            
        No-Lookahead Guarantee:
            When up_to_ts is provided, events with ts > up_to_ts are NOT returned
            and remain available for future polls with higher up_to_ts.
        """
        if self._idx >= len(self._events):
            return []  # EOF - consistent empty list
        
        batch = []
        consumed = 0
        
        while self._idx + consumed < len(self._events) and len(batch) < max_items:
            event = self._events[self._idx + consumed]
            
            # No-lookahead check
            if up_to_ts is not None and event.ts > up_to_ts:
                break  # Stop here, don't advance past up_to_ts
            
            batch.append(event)
            consumed += 1
        
        self._idx += consumed
        return batch
    
    def peek_next_ts(self) -> Optional[int]:
        """
        Peek at the timestamp of the next event without consuming it.
        
        Returns:
            Timestamp of next event (epoch ms), or None if exhausted.
        """
        if self._idx >= len(self._events):
            return None
        return self._events[self._idx].ts
    
    def reset(self) -> None:
        """Reset adapter to beginning for re-iteration."""
        self._idx = 0
    
    def remaining(self) -> int:
        """Return number of events remaining."""
        return len(self._events) - self._idx
    
    def is_exhausted(self) -> bool:
        """Return True if all events have been consumed (EOF)."""
        return self._idx >= len(self._events)
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the underlying OHLCV DataFrame.
        
        Useful for compatibility with existing code that expects DataFrame input.
        """
        return self._df.copy()
    
    def __len__(self) -> int:
        """Total number of events in fixture."""
        return len(self._events)
