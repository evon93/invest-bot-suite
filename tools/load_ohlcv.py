"""
load_ohlcv.py — Local OHLCV data loader (CSV / Parquet)

Loads OHLCV data from local files with normalization:
- Canonical columns: date, open, high, low, close, volume
- Timezone: naive (no tz, user responsibility)
- Dtypes: date=datetime64[ns], OHLCV=float64
- Sorted ascending by date, duplicates dropped (keep last)

Hardening (2F.1H):
- H1: NaT/NaN policy - drop invalid dates/OHLC, fillna(0) for volume
- H2: Epoch s/ms parsing with unit inference
- H3: Encoding parameter for CSV files

Usage:
    from tools.load_ohlcv import load_ohlcv
    df, stats = load_ohlcv("data/btc_daily.csv")
    
CLI:
    python tools/load_ohlcv.py --path data/btc_daily.csv [--encoding utf-8]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# Column name mappings (lowercase -> canonical)
COLUMN_ALIASES = {
    # Date
    "date": "date",
    "timestamp": "date",
    "time": "date",
    "datetime": "date",
    "dt": "date",
    "unix": "date",
    "epoch": "date",
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

# Epoch parsing thresholds
EPOCH_MS_THRESHOLD = 1e12  # If > 1e12, interpret as milliseconds
MIN_VALID_YEAR = 1990
MAX_VALID_YEAR = 2100


@dataclass
class LoadStats:
    """Statistics from loading/cleaning process."""
    rows_input: int = 0
    rows_output: int = 0
    dropped_nat_date: int = 0
    dropped_ohlc_nan: int = 0
    volume_filled_zero: int = 0
    duplicates_removed: int = 0
    epoch_unit_used: Optional[str] = None  # "s", "ms", or None
    
    @property
    def rows_dropped(self) -> int:
        return self.rows_input - self.rows_output - self.duplicates_removed


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
    
    # Ensure all canonical columns exist with helpful error
    missing = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if missing:
        present = list(df.columns)
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Present after normalization: {present}. "
            f"Expected: {CANONICAL_COLUMNS}"
        )
    
    return df[CANONICAL_COLUMNS]


def _is_numeric_epoch(series: pd.Series) -> bool:
    """Check if series looks like Unix epoch timestamps."""
    # Check if numeric or can be converted to numeric
    try:
        numeric = pd.to_numeric(series, errors="coerce")
        # At least 50% should be valid numbers
        valid_ratio = numeric.notna().mean()
        if valid_ratio < 0.5:
            return False
        # Check if values are in epoch range (> 1e8 for seconds since ~1973)
        sample = numeric.dropna().iloc[:min(10, len(numeric))]
        if len(sample) == 0:
            return False
        return all(v > 1e8 for v in sample)
    except Exception:
        return False


def _infer_epoch_unit(values: pd.Series) -> str:
    """Infer epoch unit: 's' for seconds, 'ms' for milliseconds."""
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if len(numeric) == 0:
        return "s"
    median_val = numeric.median()
    if median_val > EPOCH_MS_THRESHOLD:
        return "ms"
    return "s"


def _parse_date(df: pd.DataFrame, stats: LoadStats) -> pd.DataFrame:
    """Parse date column to datetime64[ns], naive (no timezone)."""
    df = df.copy()
    date_col = df["date"]
    
    # Check for epoch timestamps
    if _is_numeric_epoch(date_col):
        unit = _infer_epoch_unit(date_col)
        stats.epoch_unit_used = unit
        numeric = pd.to_numeric(date_col, errors="coerce")
        df["date"] = pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
        # Convert to naive (remove UTC)
        df["date"] = df["date"].dt.tz_localize(None)
    else:
        # Standard parsing
        df["date"] = pd.to_datetime(df["date"], utc=False, errors="coerce")
        # Remove timezone if present (make naive)
        if df["date"].dt.tz is not None:
            df["date"] = df["date"].dt.tz_localize(None)
    
    # Validate date range
    valid_dates = df["date"].notna()
    if valid_dates.any():
        min_date = df.loc[valid_dates, "date"].min()
        max_date = df.loc[valid_dates, "date"].max()
        if min_date.year < MIN_VALID_YEAR or max_date.year > MAX_VALID_YEAR:
            raise ValueError(
                f"Dates out of valid range [{MIN_VALID_YEAR}-{MAX_VALID_YEAR}]: "
                f"found [{min_date.year}-{max_date.year}]. "
                f"Check epoch unit (detected: {stats.epoch_unit_used or 'none'})."
            )
    
    return df


def _ensure_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure OHLCV columns are float64."""
    df = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    return df


def _apply_nan_policy(df: pd.DataFrame, stats: LoadStats) -> pd.DataFrame:
    """Apply H1 NaN policy: drop NaT dates, drop OHLC NaN, volume fillna(0)."""
    df = df.copy()
    n_before = len(df)
    
    # H1.1: Drop rows with NaT dates
    nat_mask = df["date"].isna()
    stats.dropped_nat_date = nat_mask.sum()
    df = df[~nat_mask]
    
    # H1.2: Drop rows with NaN in any OHLC column (not volume)
    ohlc_cols = ["open", "high", "low", "close"]
    ohlc_nan_mask = df[ohlc_cols].isna().any(axis=1)
    stats.dropped_ohlc_nan = ohlc_nan_mask.sum()
    df = df[~ohlc_nan_mask]
    
    # H1.3: Fill volume NaN with 0
    volume_nan_mask = df["volume"].isna()
    stats.volume_filled_zero = volume_nan_mask.sum()
    df["volume"] = df["volume"].fillna(0.0)
    
    return df


def load_ohlcv(
    path: str | Path,
    encoding: str = "utf-8",
    *,
    return_stats: bool = False,
) -> pd.DataFrame | Tuple[pd.DataFrame, LoadStats]:
    """
    Load OHLCV data from CSV or Parquet file.
    
    Args:
        path: Path to data file (.csv, .parquet, .pq)
        encoding: Encoding for CSV files (default: utf-8)
        return_stats: If True, return (df, stats) tuple. If False (default),
                      return just the DataFrame for backward compatibility.
    
    Returns:
        If return_stats=False (default): DataFrame with columns [date, open, high, low, close, volume]
        If return_stats=True: Tuple of (DataFrame, LoadStats)
    
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If required columns missing or dates out of range
        ImportError: If parquet engine not available
    """
    path = Path(path)
    stats = LoadStats()
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    fmt = _detect_format(path)
    
    if fmt == "csv":
        df = pd.read_csv(path, encoding=encoding)
    elif fmt == "parquet":
        try:
            df = pd.read_parquet(path)
        except ImportError as e:
            raise ImportError(
                f"Parquet engine not available. Install pyarrow or fastparquet: {e}"
            ) from e
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    
    stats.rows_input = len(df)
    
    # Normalize columns
    df = _normalize_columns(df)
    
    # Parse dates (with epoch detection)
    df = _parse_date(df, stats)
    
    # Ensure numeric dtypes
    df = _ensure_dtypes(df)
    
    # Apply NaN policy (H1)
    df = _apply_nan_policy(df, stats)
    
    # Sort and dedupe
    df = df.sort_values("date", ascending=True)
    n_before_dedup = len(df)
    df = df.drop_duplicates(subset=["date"], keep="last")
    stats.duplicates_removed = n_before_dedup - len(df)
    
    # Reset index
    df = df.reset_index(drop=True)
    stats.rows_output = len(df)
    
    if return_stats:
        return df, stats
    return df


def summarize(df: pd.DataFrame, stats: LoadStats) -> dict:
    """Generate summary statistics for OHLCV DataFrame."""
    summary = {
        "n_rows": len(df),
        "date_min": df["date"].min() if len(df) > 0 else None,
        "date_max": df["date"].max() if len(df) > 0 else None,
        "rows_input": stats.rows_input,
        "dropped_nat_date": stats.dropped_nat_date,
        "dropped_ohlc_nan": stats.dropped_ohlc_nan,
        "volume_filled_zero": stats.volume_filled_zero,
        "duplicates_removed": stats.duplicates_removed,
        "epoch_unit_used": stats.epoch_unit_used,
    }
    return summary


def print_summary(path: str, df: pd.DataFrame, stats: LoadStats):
    """Print human-readable summary to stdout."""
    s = summarize(df, stats)
    
    print(f"=== OHLCV Summary: {path} ===")
    print(f"Rows: {s['n_rows']} (input: {s['rows_input']})")
    print(f"Date range: {s['date_min']} → {s['date_max']}")
    print(f"Dropped NaT dates: {s['dropped_nat_date']}")
    print(f"Dropped OHLC NaN: {s['dropped_ohlc_nan']}")
    print(f"Volume filled zero: {s['volume_filled_zero']}")
    print(f"Duplicates removed: {s['duplicates_removed']}")
    if s['epoch_unit_used']:
        print(f"Epoch unit detected: {s['epoch_unit_used']}")
    
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
    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8",
        help="Encoding for CSV files (default: utf-8)",
    )
    
    args = parser.parse_args()
    
    try:
        df, stats = load_ohlcv(args.path, encoding=args.encoding, return_stats=True)
        print_summary(args.path, df, stats)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
