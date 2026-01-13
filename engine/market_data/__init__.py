"""
engine/market_data/__init__.py

Market data feed components for pluggable data sources.
"""

from engine.market_data.market_data_adapter import MarketDataEvent, MarketDataAdapter
from engine.market_data.fixture_adapter import FixtureMarketDataAdapter, FixtureSchemaError
from engine.market_data.ccxt_adapter import (
    CCXTMarketDataAdapter,
    CCXTConfig,
    OHLCVClient,
    MockOHLCVClient,
    NetworkDisabledError,
)

__all__ = [
    "MarketDataEvent",
    "MarketDataAdapter",
    "FixtureMarketDataAdapter",
    "FixtureSchemaError",
    "CCXTMarketDataAdapter",
    "CCXTConfig",
    "OHLCVClient",
    "MockOHLCVClient",
    "NetworkDisabledError",
]

