"""
strategy_engine/strategy_registry.py

Strategy registry for selecting strategy versions at runtime (AG-3J-1-1).

Usage:
    from strategy_engine.strategy_registry import get_strategy_fn, STRATEGY_VERSIONS
    
    strategy_fn = get_strategy_fn("v0_7")  # Returns generate_order_intents function
    intents = strategy_fn(ohlcv_df, params, ticker, asof_ts)
"""

from typing import Callable, Dict, List, Any
import pandas as pd
from contracts.event_messages import OrderIntent

# Type alias for strategy function signature
StrategyFn = Callable[
    [pd.DataFrame, Dict[str, Any], str, pd.Timestamp],
    List[OrderIntent]
]

# Available strategy versions
STRATEGY_VERSIONS = ["v0_7", "v0_8"]
DEFAULT_STRATEGY = "v0_7"


def get_strategy_fn(version: str = DEFAULT_STRATEGY) -> StrategyFn:
    """
    Get strategy function by version string.
    
    Args:
        version: Strategy version (e.g., "v0_7", "v0_8")
        
    Returns:
        Strategy function with signature:
            (ohlcv_df, params, ticker, asof_ts) -> List[OrderIntent]
            
    Raises:
        ValueError: If version is not supported
    """
    if version == "v0_7":
        from strategy_engine.strategy_v0_7 import generate_order_intents
        return generate_order_intents
    elif version == "v0_8":
        from strategy_engine.strategy_v0_8 import generate_order_intents
        return generate_order_intents
    else:
        supported = ", ".join(STRATEGY_VERSIONS)
        raise ValueError(f"Unknown strategy version '{version}'. Supported: {supported}")
