"""
strategy_engine/strategy_v0_8.py

Strategy v0.8 - EMA Crossover (AG-3J-2-1)

Implements EMA-based crossover strategy:
- Deterministic: no RNG, no wallclock
- No-lookahead: uses only data up to asof_ts
- Warmup: returns [] if insufficient history
- NaN-safe: explicit handling of rolling NaNs

Interface contract (same as v0.7):
    generate_order_intents(ohlcv_df, params, ticker, asof_ts) -> List[OrderIntent]

Key differences from v0.7:
- Uses EMA instead of SMA (more responsive to recent data)
- Slightly different default periods (fast=5, slow=13)
"""

import pandas as pd
from typing import List, Dict, Any
from contracts.event_messages import OrderIntent
import logging

logger = logging.getLogger(__name__)


def generate_order_intents(
    ohlcv_df: pd.DataFrame,
    params: Dict[str, Any],
    ticker: str,
    asof_ts: pd.Timestamp
) -> List[OrderIntent]:
    """
    Generates OrderIntent events based on EMA crossover strategy.
    
    Determinism guarantees (AG-3J-2-1):
    - Same input → same output (no RNG, no wallclock)
    - No lookahead: output at t is invariant to data after t
    - Warmup: returns [] if len(data) < slow_period
    - NaN-safe: returns [] if indicators have NaN
    
    Args:
        ohlcv_df: DataFrame containing OHLCV data.
        params: Dictionary containing strategy parameters.
            - fast_period (int): Fast EMA period (default: 5)
            - slow_period (int): Slow EMA period (default: 13)
        ticker: Symbol/Ticker for the orders.
        asof_ts: The timestamp to evaluate the signal at (simulation time).

    Returns:
        List[OrderIntent]: List of generated order intents (empty if no signal).
    """
    # 1. Validation - empty data
    if ohlcv_df.empty:
        return []
    
    # Extract params with defaults
    fast_period = params.get('fast_period', 5)
    slow_period = params.get('slow_period', 13)
    
    # Ensure slow_period >= fast_period
    if slow_period < fast_period:
        slow_period, fast_period = fast_period, slow_period
    
    # 2. Prepare data - copy and set index
    df = ohlcv_df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    df = df.sort_index()
    
    # 3. Slice strictly up to asof_ts (NO LOOKAHEAD)
    df = df.loc[:asof_ts]
    
    # 4. Warmup check - need at least slow_period rows for EMA to stabilize
    if len(df) < slow_period:
        return []
    
    # 5. Validate 'close' column exists
    if 'close' not in df.columns:
        logger.warning("Strategy v0.8: 'close' column missing")
        return []
    
    # 6. Calculate EMAs
    # Using pandas EWM (Exponentially Weighted Moving) with span parameter
    # This is deterministic given the same input data
    df['fast_ema'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['slow_ema'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    # 7. Need at least 2 rows for crossover detection
    if len(df) < 2:
        return []
    
    curr_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # 8. NaN handling - return empty if any indicator is NaN
    if (pd.isna(curr_row['fast_ema']) or pd.isna(curr_row['slow_ema']) or
        pd.isna(prev_row['fast_ema']) or pd.isna(prev_row['slow_ema'])):
        return []
    
    intents = []
    
    # 9. Crossover Logic
    # Golden Cross: Fast EMA crosses above Slow EMA
    if prev_row['fast_ema'] <= prev_row['slow_ema'] and curr_row['fast_ema'] > curr_row['slow_ema']:
        intent = OrderIntent(
            symbol=ticker,
            side="BUY",
            qty=1.0,  # Placeholder, sizing handled by risk manager
            order_type="MARKET",
            ts=asof_ts.isoformat()
        )
        intents.append(intent)
    
    # Death Cross: Fast EMA crosses below Slow EMA
    elif prev_row['fast_ema'] >= prev_row['slow_ema'] and curr_row['fast_ema'] < curr_row['slow_ema']:
        intent = OrderIntent(
            symbol=ticker,
            side="SELL",
            qty=1.0,
            order_type="MARKET",
            ts=asof_ts.isoformat()
        )
        intents.append(intent)
    
    return intents
