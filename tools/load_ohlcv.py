"""
load_ohlcv.py — Local OHLCV data loader (CSV / Parquet)

Loads OHLCV data from local files with normalization:
- Canonical columns: date, open, high, low, close, volume
- Timezone: naive (no tz, user responsibility)
- Dtypes: date=datetime64[ns], OHLCV=float64
- Sorted ascending by date, duplicates dropped (keep last)

Usage:
    from tools.load_ohlcv import load_ohlcv
    df = load_ohlcv("data/btc_daily.csv")
    
CLI:
    python tools/load_ohlcv.py --path data/btc_daily.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Column name mappings (lowercase -> canonical)
COLUMN_ALIASES = {
    # Date
    "date": "date",
    "timestamp": "date",
    "time": "date",
    "datetime": "date",
    "dt": "date",
    # OHLCV
    "open": "open",
    "o": "open",
    "high": "high",
    "h": "high",
    "low": "low",
    "l": "low",
    "close": "close",
    "c": "close",
    "volume": "volume",
    "vol": "volume",
    "v": "volume",
}

CANONICAL_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def _detect_format(path: Path) -> str:
    """Detect file format by extension."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    elif suffix in (".parquet", ".pq"):
        return "parquet"
    else:
        # Fallback: try CSV
        return "csv"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to canonical OHLCV format."""
    # Lowercase all columns
    df.columns = [c.lower().strip() for c in df.columns]
    
    # Map aliases
    rename_map = {}
    for col in df.columns:
        if col in COLUMN_ALIASES:
            canonical = COLUMN_ALIASES[col]
            if canonical not in rename_map.values():
                rename_map[col] = canonical
    
    df = df.rename(columns=rename_map)
    
    # Ensure all canonical columns exist
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col} (after normalization)")
    
    return df[CANONICAL_COLUMNS]


def _parse_date(df: pd.DataFrame) -> pd.DataFrame:
    """Parse date column to datetime64[ns], naive (no timezone)."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], utc=False, errors="coerce")
    
    # Remove timezone if present (make naive)
    if df["date"].dt.tz is not None:
        df["date"] = df["date"].dt.tz_localize(None)
    
    return df


def _ensure_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure OHLCV columns are float64."""
    df = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    """
    Load OHLCV data from CSV or Parquet file.
    
    Args:
        path: Path to data file (.csv, .parquet, .pq)
    
    Returns:
        DataFrame with columns: date, open, high, low, close, volume
        - date: datetime64[ns] (naive, no timezone)
        - OHLCV: float64
        - Sorted ascending by date
        - Duplicates dropped (keep last)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns missing
        ImportError: If parquet engine not available
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    fmt = _detect_format(path)
    
    if fmt == "csv":
        df = pd.read_csv(path, encoding="utf-8")
    elif fmt == "parquet":
        try:
            df = pd.read_parquet(path)
        except ImportError as e:
            raise ImportError(
                f"Parquet engine not available. Install pyarrow or fastparquet: {e}"
            ) from e
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    
    # Normalize
    df = _normalize_columns(df)
    df = _parse_date(df)
    df = _ensure_dtypes(df)
    
    # Sort and dedupe
    df = df.sort_values("date", ascending=True)
    n_before = len(df)
    df = df.drop_duplicates(subset=["date"], keep="last")
    n_dupes = n_before - len(df)
    
    # Reset index
    df = df.reset_index(drop=True)
    
    return df


def summarize(df: pd.DataFrame, n_dupes: int = 0) -> dict:
    """Generate summary statistics for OHLCV DataFrame."""
    summary = {
        "n_rows": len(df),
        "date_min": df["date"].min() if len(df) > 0 else None,
        "date_max": df["date"].max() if len(df) > 0 else None,
        "n_duplicates_removed": n_dupes,
        "nans_per_column": df.isna().sum().to_dict(),
    }
    return summary


def print_summary(path: str, df: pd.DataFrame, n_dupes: int = 0):
    """Print human-readable summary to stdout."""
    s = summarize(df, n_dupes)
    
    print(f"=== OHLCV Summary: {path} ===")
    print(f"Rows: {s['n_rows']}")
    print(f"Date range: {s['date_min']} → {s['date_max']}")
    print(f"Duplicates removed: {s['n_duplicates_removed']}")
    print(f"NaNs per column: {s['nans_per_column']}")
    
    if len(df) > 0:
        print("\n--- Head (3 rows) ---")
        print(df.head(3).to_string(index=False))
        print("\n--- Tail (3 rows) ---")
        print(df.tail(3).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(
        description="Load and summarize OHLCV data from CSV or Parquet"
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to OHLCV file (.csv, .parquet, .pq)",
    )
    
    args = parser.parse_args()
    
    try:
        df = load_ohlcv(args.path)
        # Re-compute n_dupes for display (approximate)
        print_summary(args.path, df)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
