import pandas as pd
from typing import List, Dict, Any, Optional
from contracts.event_messages import OrderIntent
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_order_intents(
    ohlcv_df: pd.DataFrame,
    params: Dict[str, Any],
    ticker: str,
    asof_ts: pd.Timestamp
) -> List[OrderIntent]:
    """
    Generates OrderIntent events based on SMA crossover strategy.

    Args:
        ohlcv_df: DataFrame containing OHLCV data. optimized for 'close' column.
        params: Dictionary containing strategy parameters ('fast_period', 'slow_period').
        ticker: Symbol/Ticker for the orders.
        asof_ts: The timestamp to evaluate the signal at (simulation time).

    Returns:
        List[OrderIntent]: List of generated order intents (empty if no signal).
    """
    
    # 1. Validation & Setup
    if ohlcv_df.empty:
        return []

    fast_period = params.get('fast_period', 10)
    slow_period = params.get('slow_period', 30)
    
    # Ensure dataframe is sorted by timestamp (loader guarantees but good practice for strategy engine)
    # Assume 'timestamp' is a column or index. If column, set as index for rolling.
    df = ohlcv_df.copy()
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    df = df.sort_index()
    
    # Check if asof_ts is in the data (or we have data up to it)
    # in simulations we might pass the entire history and slice, or just the history up to asof_ts.
    # Here we assume df contains history up to at least asof_ts.
    # We slice strictly up to asof_ts
    df = df.loc[:asof_ts]
    
    if len(df) < slow_period:
        # Not enough data for warmup
        return []

    # 2. Calculate Indicators
    # Optimization: We only strictly need the last 2 points if we calculated incrementally,
    # but for v0.7 vectorization is fine.
    
    df['fast_sma'] = df['close'].rolling(window=fast_period).mean()
    df['slow_sma'] = df['close'].rolling(window=slow_period).mean()
    
    # 3. Crossover Logic
    # We need the current row (at asof_ts) and the previous row.
    # Note: asof_ts might not exactly match a candle timestamp if we are between candles,
    # but usually in backtest tick == candle close.
    # We perform "asof" lookups by position.
    
    if len(df) < 2:
        return []

    curr_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # Ensure we are actually evaluating the requested timestamp (allow small tolerance or strict?)
    # If the last available candle is too old, maybe we shouldn't trade.
    # For now, we assume the caller feeds us relevant data.
    
    # Check for valid SMAs
    if pd.isna(curr_row['fast_sma']) or pd.isna(curr_row['slow_sma']) or \
       pd.isna(prev_row['fast_sma']) or pd.isna(prev_row['slow_sma']):
        return []

    intents = []
    
    # Golden Cross: Fast crosses above Slow
    # Prev: Fast <= Slow
    # Curr: Fast > Slow
    if prev_row['fast_sma'] <= prev_row['slow_sma'] and curr_row['fast_sma'] > curr_row['slow_sma']:
        intent = OrderIntent(
            symbol=ticker,
            side="BUY",
            qty=1.0, # Placeholder, sizing logic usually in another layer or risk manager
            order_type="MARKET",
            ts=asof_ts.isoformat()
        )
        intents.append(intent)

    # Death Cross: Fast crosses below Slow
    # Prev: Fast >= Slow
    # Curr: Fast < Slow
    elif prev_row['fast_sma'] >= prev_row['slow_sma'] and curr_row['fast_sma'] < curr_row['slow_sma']:
        intent = OrderIntent(
            symbol=ticker,
            side="SELL",
            qty=1.0, # Placeholder
            order_type="MARKET",
            ts=asof_ts.isoformat()
        )
        intents.append(intent)
        
    return intents
