from typing import Dict, Union
import pandas as pd

def needs_rebalance(  # type: ignore[type-arg]
    current: Dict[str, float] | "pd.Series" | "pd.DataFrame"
) -> bool:
    """
    Returns True if any asset drifts more than
    RISK_RULES["rebalance"]["drift_threshold"] from TARGET_ALLOC.

    Accepts dict, pd.Series or 1-row pd.DataFrame.
    """
    RISK_RULES = {"rebalance": {"drift_threshold": 0.03}}
    TARGET_ALLOC = {"ETF": 0.60, "CRYPTO_BTC": 0.08, "CRYPTO_ETH": 0.04, "BONDS": 0.28}

    if isinstance(current, dict):
        current_weights = pd.Series(current)
    elif isinstance(current, pd.Series):
        current_weights = current
    else:  # pd.DataFrame
        if current.shape[0] != 1:
            raise ValueError("DataFrame must have exactly 1 row")
        current_weights = current.iloc[0]

    if not current_weights.index.equals(pd.Index(TARGET_ALLOC.keys())):
        raise ValueError("Mismatch between current weights and target allocation")

    drifts = abs(current_weights - pd.Series(TARGET_ALLOC))
    return (drifts > RISK_RULES["rebalance"]["drift_threshold"]).any()
