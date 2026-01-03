import pandas as pd
from pathlib import Path
import logging
from typing import Union

# Logger configuration
logger = logging.getLogger(__name__)

# Column Aliases Mapping
COLUMN_ALIASES = {
    'timestamp': ['ts', 'datetime', 'date', 'time', 'timestamp'],
    'open': ['o', 'open'],
    'high': ['h', 'high'],
    'low': ['l', 'low'],
    'close': ['c', 'close'],
    'volume': ['v', 'vol', 'volume']
}

REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

def load_ohlcv(path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads OHLCV data from a CSV or Parquet file, normalizes columns, 
    and validates integrity (monotonicity, duplicates, missing values).

    Args:
        path: Path to the CSV or Parquet file.

    Returns:
        pd.DataFrame: Normalized OHLCV DataFrame with UTC timestamp index (or column).
        Actually, per req, return DataFrame with columns. 
        We will keep 'timestamp' as a column to match "pd.DataFrame (OHLCV normalizado)".
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # 1. Detect format and load
    suffix = path.suffix.lower()
    if suffix == '.csv':
        df = pd.read_csv(path)
    elif suffix == '.parquet':
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file extension: {suffix}. Use .csv or .parquet")

    # 2. Normalize Columns
    # Invert mapping for easier lookup
    alias_map = {}
    for standard, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            alias_map[alias.lower()] = standard
    
    # Normalize current columns
    new_columns = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in alias_map:
            new_columns[col] = alias_map[col_lower]
        elif col_lower in COLUMN_ALIASES: # direct match
            new_columns[col] = col_lower
            
    df = df.rename(columns=new_columns)

    # Check required columns
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Found: {list(df.columns)}")

    # 3. Parse Timestamp
    # utc=True -> converts to UTC datetime64[ns, UTC]
    try:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    except Exception as e:
        raise ValueError(f"Failed to parse timestamp column: {e}")

    # 4. Cast OHLCV to float
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        try:
            df[col] = df[col].astype(float)
        except ValueError as e:
            raise ValueError(f"Failed to cast column {col} to float: {e}")

    # 5. Validations
    
    # NaNs
    if df[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Found NaN values in required columns.")

    # Duplicates in timestamp
    if df['timestamp'].duplicated().any():
        raise ValueError("Duplicate timestamps found.")

    # Monotonicity
    if not df['timestamp'].is_monotonic_increasing:
        raise ValueError("Timestamps are not strictly monotonic increasing (unsorted).")

    # 6. Gap Detection
    if len(df) > 1:
        deltas = df['timestamp'].diff().dropna()
        median_delta = deltas.median()
        
        # Consider a gap if delta > 1.5 * median_delta (heuristic)
        # Using a slight tolerance
        gap_mask = deltas > (1.5 * median_delta)
        num_gaps = gap_mask.sum()
        
        if num_gaps > 0:
            logger.warning(f"Detected {num_gaps} gaps in data (median delta: {median_delta}).")

    # Ensure final column order
    df = df[REQUIRED_COLUMNS].copy()
    
    return df
