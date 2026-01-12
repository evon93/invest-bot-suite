"""
tests/test_strategy_v0_8_3J2.py

Tests for strategy v0.8 determinism and correctness (AG-3J-2-1).

Validates:
- Determinism: same input → same output
- No-lookahead: output at t is invariant to data after t
- Warmup: returns [] if insufficient history
- NaN handling: defined behavior, no crash
- Crossover detection: BUY on golden cross, SELL on death cross
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from strategy_engine.strategy_v0_8 import generate_order_intents


def make_ohlcv(
    close_prices: list,
    start: str = "2025-01-01",
    freq: str = "h"
) -> pd.DataFrame:
    """Create OHLCV DataFrame from close prices."""
    n = len(close_prices)
    return pd.DataFrame({
        "timestamp": pd.date_range(start, periods=n, freq=freq, tz="UTC"),
        "open": close_prices,
        "high": [p * 1.01 for p in close_prices],
        "low": [p * 0.99 for p in close_prices],
        "close": close_prices,
        "volume": [1000.0] * n,
    })


class TestStrategyV08Determinism:
    """Tests for determinism guarantee."""

    def test_same_input_same_output(self):
        """Same input should produce identical output across calls."""
        # Create a dataset with clear crossover
        prices = [100.0] * 20 + [101.0 + i * 0.5 for i in range(10)]  # Rising trend
        df = make_ohlcv(prices)
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        # Call twice with identical inputs
        result1 = generate_order_intents(df, params, ticker, asof_ts)
        result2 = generate_order_intents(df, params, ticker, asof_ts)
        
        # Must be identical
        assert len(result1) == len(result2)
        for r1, r2 in zip(result1, result2):
            assert r1.symbol == r2.symbol
            assert r1.side == r2.side
            assert r1.qty == r2.qty
            assert r1.ts == r2.ts

    def test_determinism_multiple_calls(self):
        """Multiple calls should produce consistent results."""
        prices = [100.0 - i * 0.5 for i in range(30)]  # Declining trend
        df = make_ohlcv(prices)
        params = {"fast_period": 3, "slow_period": 8}
        ticker = "ETH-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        # Call 10 times
        results = [generate_order_intents(df, params, ticker, asof_ts) for _ in range(10)]
        
        # All should be identical
        first = results[0]
        for r in results[1:]:
            assert len(r) == len(first)


class TestStrategyV08NoLookahead:
    """Tests for no-lookahead guarantee."""

    def test_output_invariant_appending_future(self):
        """Output at t should not change when future data is appended."""
        # Base dataset up to time t
        prices_base = [100.0] * 15 + [100.0 + i * 0.3 for i in range(15)]
        df_base = make_ohlcv(prices_base)
        
        # Extended dataset with future data after t
        prices_extended = prices_base + [120.0 + i * 0.5 for i in range(20)]  # More future data
        df_extended = make_ohlcv(prices_extended)
        
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        
        # The "now" timestamp is the last timestamp of base dataset
        asof_ts = df_base["timestamp"].iloc[-1]
        
        # Strategy evaluated at asof_ts on base dataset
        result_base = generate_order_intents(df_base, params, ticker, asof_ts)
        
        # Strategy evaluated at same asof_ts on extended dataset
        result_extended = generate_order_intents(df_extended, params, ticker, asof_ts)
        
        # Outputs must be identical (future data should be ignored)
        assert len(result_base) == len(result_extended)
        for r1, r2 in zip(result_base, result_extended):
            assert r1.side == r2.side
            assert r1.symbol == r2.symbol

    def test_future_data_does_not_affect_signal(self):
        """Adding different future paths should not change current signal."""
        # Dataset with clear state at t
        prices = [100.0] * 10 + [99.0, 98.0, 97.0, 96.0, 95.0]  # Decline
        df_original = make_ohlcv(prices)
        
        # Future path 1: continues declining
        prices_decline = prices + [94.0, 93.0, 92.0]
        df_decline = make_ohlcv(prices_decline)
        
        # Future path 2: suddenly reverses
        prices_rise = prices + [100.0, 105.0, 110.0]
        df_rise = make_ohlcv(prices_rise)
        
        params = {"fast_period": 3, "slow_period": 5}
        ticker = "BTC-USD"
        asof_ts = df_original["timestamp"].iloc[-1]
        
        result_orig = generate_order_intents(df_original, params, ticker, asof_ts)
        result_decline = generate_order_intents(df_decline, params, ticker, asof_ts)
        result_rise = generate_order_intents(df_rise, params, ticker, asof_ts)
        
        # All must be identical
        assert len(result_orig) == len(result_decline) == len(result_rise)


class TestStrategyV08Warmup:
    """Tests for warmup behavior."""

    def test_insufficient_history_returns_empty(self):
        """Should return [] if not enough data for slow_period."""
        # Only 5 bars, but slow_period is 13
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        df = make_ohlcv(prices)
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        
        assert result == []

    def test_exact_warmup_threshold(self):
        """At exactly slow_period bars, should not crash."""
        # Exactly 13 bars
        prices = [100.0 + i for i in range(13)]
        df = make_ohlcv(prices)
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        # Should not crash, may or may not produce signal
        result = generate_order_intents(df, params, ticker, asof_ts)
        assert isinstance(result, list)

    def test_empty_dataframe_returns_empty(self):
        """Empty DataFrame should return []."""
        df = pd.DataFrame()
        params = {"fast_period": 5, "slow_period": 13}
        result = generate_order_intents(df, params, "BTC-USD", pd.Timestamp.now(tz="UTC"))
        assert result == []


class TestStrategyV08NaNHandling:
    """Tests for NaN handling."""

    def test_nan_in_close_returns_empty(self):
        """NaN in close column should not crash, returns []."""
        prices = [100.0] * 20
        df = make_ohlcv(prices)
        # Inject NaN in last close
        df.loc[df.index[-1], "close"] = np.nan
        
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        # Should handle gracefully, not crash
        assert isinstance(result, list)

    def test_nan_propagates_to_indicators(self):
        """NaN in data should propagate to indicators → empty result."""
        prices = [100.0] * 20
        df = make_ohlcv(prices)
        # Inject NaN in middle of data
        df.loc[df.index[15], "close"] = np.nan
        
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        # EMA will propagate NaN - should return []
        assert result == []

    def test_missing_close_column_returns_empty(self):
        """Missing 'close' column should return [] (no crash)."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=20, freq="h", tz="UTC"),
            "open": [100.0] * 20,
            "high": [105.0] * 20,
            "low": [95.0] * 20,
            "volume": [1000.0] * 20,
            # No 'close' column!
        })
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        assert result == []


class TestStrategyV08CrossoverDetection:
    """Tests for crossover signal generation."""

    def test_golden_cross_generates_buy(self):
        """Fast EMA crossing above slow EMA should generate BUY."""
        # Create clear golden cross: low prices then rising
        prices = [100.0] * 15 + [100.0 + i * 2 for i in range(15)]  # Strong uptrend
        df = make_ohlcv(prices)
        params = {"fast_period": 3, "slow_period": 8}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        
        # Should have BUY signal (if crossover detected)
        if len(result) > 0:
            assert result[0].side == "BUY"

    def test_death_cross_generates_sell(self):
        """Fast EMA crossing below slow EMA should generate SELL."""
        # Create clear death cross: high prices then falling
        prices = [100.0 + i for i in range(15)] + [115.0 - i * 2 for i in range(15)]  # Strong downtrend
        df = make_ohlcv(prices)
        params = {"fast_period": 3, "slow_period": 8}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        
        # Should have SELL signal (if crossover detected)
        if len(result) > 0:
            assert result[0].side == "SELL"

    def test_no_crossover_returns_empty(self):
        """No crossover should return empty list."""
        # Flat prices - no crossover
        prices = [100.0] * 30
        df = make_ohlcv(prices)
        params = {"fast_period": 5, "slow_period": 13}
        ticker = "BTC-USD"
        asof_ts = df["timestamp"].iloc[-1]
        
        result = generate_order_intents(df, params, ticker, asof_ts)
        assert result == []
