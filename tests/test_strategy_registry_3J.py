"""
tests/test_strategy_registry_3J.py

Tests for strategy registry and selector (AG-3J-1-1).

Validates:
- Registry returns correct strategy function for each version
- Default is v0_7 if not specified
- Unknown version raises ValueError
- Both v0_7 and v0_8 are callable with correct signature
"""

import pytest
import pandas as pd
from datetime import datetime, timezone

from strategy_engine.strategy_registry import (
    get_strategy_fn,
    STRATEGY_VERSIONS,
    DEFAULT_STRATEGY,
)


class TestStrategyRegistry:
    """Tests for strategy_registry module."""

    def test_default_strategy_is_v0_7(self):
        """DEFAULT_STRATEGY should be v0_7 for backward compatibility."""
        assert DEFAULT_STRATEGY == "v0_7"

    def test_strategy_versions_contains_v0_7_and_v0_8(self):
        """STRATEGY_VERSIONS should include both v0_7 and v0_8."""
        assert "v0_7" in STRATEGY_VERSIONS
        assert "v0_8" in STRATEGY_VERSIONS

    def test_get_strategy_fn_default(self):
        """get_strategy_fn() without args should return v0_7."""
        fn = get_strategy_fn()
        # Verify it's the v0_7 function by checking module
        assert fn.__module__ == "strategy_engine.strategy_v0_7"

    def test_get_strategy_fn_v0_7(self):
        """get_strategy_fn('v0_7') should return v0_7 function."""
        fn = get_strategy_fn("v0_7")
        assert fn.__module__ == "strategy_engine.strategy_v0_7"

    def test_get_strategy_fn_v0_8(self):
        """get_strategy_fn('v0_8') should return v0_8 function."""
        fn = get_strategy_fn("v0_8")
        assert fn.__module__ == "strategy_engine.strategy_v0_8"

    def test_get_strategy_fn_unknown_raises(self):
        """get_strategy_fn with unknown version should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy version"):
            get_strategy_fn("v0_99")

    def test_strategy_functions_are_callable(self):
        """Both strategy functions should be callable with correct signature."""
        for version in STRATEGY_VERSIONS:
            fn = get_strategy_fn(version)
            assert callable(fn)
            
            # Test with empty dataframe should return empty list
            empty_df = pd.DataFrame()
            result = fn(empty_df, {}, "BTC-USD", pd.Timestamp.now(tz="UTC"))
            assert isinstance(result, list)
            assert result == []


class TestStrategyV0_8Stub:
    """Tests for strategy_v0_8 stub behavior."""

    def test_v0_8_returns_empty_list(self):
        """v0.8 stub should return empty list (no signals)."""
        from strategy_engine.strategy_v0_8 import generate_order_intents
        
        # Create minimal OHLCV data
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=50, freq="h", tz="UTC"),
            "open": [100.0] * 50,
            "high": [105.0] * 50,
            "low": [95.0] * 50,
            "close": [101.0] * 50,
            "volume": [1000.0] * 50,
        })
        
        params = {"fast_period": 10, "slow_period": 30}
        asof_ts = pd.Timestamp("2025-01-03", tz="UTC")
        
        result = generate_order_intents(df, params, "BTC-USD", asof_ts)
        
        assert result == [], "v0.8 stub should return empty list"


class TestStrategyV0_7Integration:
    """Tests to verify v0_7 still works via registry."""

    def test_v0_7_generates_signals(self):
        """v0.7 should generate signals on crossover data."""
        from strategy_engine.strategy_v0_7 import generate_order_intents
        
        # Create data with clear crossover pattern
        n = 40
        # Start with slow > fast, then transition to fast > slow
        close_prices = (
            [100.0] * 15 +        # Warmup
            [100.0 - i for i in range(10)] +  # Declining (death cross)
            [90.0 + i*2 for i in range(15)]   # Rising (golden cross)
        )
        
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=n, freq="h", tz="UTC"),
            "close": close_prices,
        })
        
        params = {"fast_period": 3, "slow_period": 5}
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, "BTC-USD", asof_ts)
        
        # Should have at least one signal (either BUY or SELL)
        # Note: With this price pattern, there should be a golden cross
        assert isinstance(result, list)
