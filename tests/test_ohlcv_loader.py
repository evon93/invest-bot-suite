import pytest
import pandas as pd
import numpy as np
from data_adapters.ohlcv_loader import load_ohlcv

def test_load_csv_standard_aliases(tmp_path):
    # Create sample CSV
    csv_path = tmp_path / "sample.csv"
    data = {
        "Date": ["2023-01-01 10:00", "2023-01-01 11:00"],
        "Open": [100, 101],
        "High": [105, 106],
        "Low": [99, 100],
        "Close": [102, 103],
        "Vol": [1000, 1500]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    
    assert list(df.columns) == ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    assert df['timestamp'].dtype.name.startswith("datetime64[ns, UTC]")
    assert len(df) == 2
    assert df.iloc[0]['open'] == 100.0

def test_load_parquet(tmp_path):
    pytest.importorskip("pyarrow")
    parquet_path = tmp_path / "sample.parquet"
    data = {
        "ts": [pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2023-01-02", tz="UTC")],
        "o": [10, 11],
        "h": [12, 13],
        "l": [9, 10],
        "c": [11, 12],
        "v": [100, 200]
    }
    pd.DataFrame(data).to_parquet(parquet_path)
    
    df = load_ohlcv(parquet_path)
    assert len(df) == 2
    assert df.iloc[1]['close'] == 12.0

def test_missing_columns(tmp_path):
    csv_path = tmp_path / "bad.csv"
    pd.DataFrame({"Date": ["2023-01-01"], "Open": [1]}).to_csv(csv_path, index=False)
    
    with pytest.raises(ValueError, match="Missing required columns"):
        load_ohlcv(csv_path)

def test_nan_values(tmp_path):
    csv_path = tmp_path / "nans.csv"
    data = {
        "timestamp": ["2023-01-01", "2023-01-02"],
        "open": [100, None], # NaN
        "high": [105, 106],
        "low": [99, 100],
        "close": [102, 103],
        "volume": [1000, 1500]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    with pytest.raises(ValueError, match="Found NaN values"):
        load_ohlcv(csv_path)

def test_duplicate_timestamps(tmp_path):
    csv_path = tmp_path / "dups.csv"
    data = {
        "timestamp": ["2023-01-01", "2023-01-01"], # Dup
        "open": [100, 101],
        "high": [105, 106],
        "low": [99, 100],
        "close": [102, 103],
        "volume": [1000, 1500]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    with pytest.raises(ValueError, match="Duplicate timestamps"):
        load_ohlcv(csv_path)

def test_unsorted_timestamps(tmp_path):
    csv_path = tmp_path / "unsorted.csv"
    data = {
        "timestamp": ["2023-01-02", "2023-01-01"], # Desorden
        "open": [100, 101],
        "high": [105, 106],
        "low": [99, 100],
        "close": [102, 103],
        "volume": [1000, 1500]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    with pytest.raises(ValueError, match="Timestamps are not strictly monotonic"):
        load_ohlcv(csv_path)
