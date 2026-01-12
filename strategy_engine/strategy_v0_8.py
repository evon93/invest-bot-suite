"""
strategy_engine/strategy_v0_8.py

Strategy v0.8 stub for AG-3J-1-1.

This is a placeholder that implements the same interface as v0.7.
The actual alpha logic will be implemented in ticket 3J.2.

Interface contract:
    generate_order_intents(ohlcv_df, params, ticker, asof_ts) -> List[OrderIntent]
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
    Generates OrderIntent events - v0.8 stub.
    
    This version is a placeholder that returns empty list by default.
    Real implementation will be added in AG-3J-2-x.
    
    Args:
        ohlcv_df: DataFrame containing OHLCV data.
        params: Dictionary containing strategy parameters.
        ticker: Symbol/Ticker for the orders.
        asof_ts: The timestamp to evaluate the signal at (simulation time).

    Returns:
        List[OrderIntent]: Empty list (stub behavior).
    """
    # Validation
    if ohlcv_df.empty:
        return []
    
    # Log that v0.8 is being used
    logger.debug("Strategy v0.8 (stub) called for ticker=%s at %s", ticker, asof_ts)
    
    # Stub: Return empty list - no signals generated
    # This maintains determinism and doesn't affect existing behavior
    return []
