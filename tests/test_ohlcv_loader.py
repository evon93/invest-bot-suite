import pytest
import pandas as pd
import numpy as np
import datetime
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
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    assert str(df["timestamp"].dt.tz) == "datetime.timezone.utc" or str(df["timestamp"].dt.tz) == "UTC"
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

def test_epoch_seconds_timestamp_parses_to_utc(tmp_path):
    csv_path = tmp_path / "epoch_sec.csv"
    # ~2023 in seconds
    ts = [1672531200, 1672534800] 
    data = {
        "ts": ts,
        "o": [1, 2], "h": [3, 4], "l": [1, 2], "c": [2, 3], "v": [10, 20]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    assert df["timestamp"].iloc[0].year == 2023

def test_epoch_milliseconds_timestamp_parses_to_utc(tmp_path):
    csv_path = tmp_path / "epoch_ms.csv"
    # ~2023 in milliseconds
    ts = [1672531200000, 1672534800000]
    data = {
        "ts": ts,
        "o": [1, 2], "h": [3, 4], "l": [1, 2], "c": [2, 3], "v": [10, 20]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    assert df["timestamp"].iloc[0].year == 2023

def test_epoch_microseconds_timestamp_parses_to_utc(tmp_path):
    csv_path = tmp_path / "epoch_us.csv"
    # ~2023 in microseconds
    ts = [1672531200000000, 1672534800000000]
    data = {
        "ts": ts,
        "o": [1, 2], "h": [3, 4], "l": [1, 2], "c": [2, 3], "v": [10, 20]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    assert df["timestamp"].iloc[0].year == 2023

def test_timezone_offset_string_converts_to_utc(tmp_path):
    csv_path = tmp_path / "tz_offset.csv"
    # 2023-01-01 00:00:00-05:00 maps to 05:00 UTC
    data = {
        "ts": ["2023-01-01 00:00:00-05:00", "2023-01-01 01:00:00-05:00"],
        "o": [1, 2], "h": [3, 4], "l": [1, 2], "c": [2, 3], "v": [10, 20]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    assert isinstance(df["timestamp"].dtype, pd.DatetimeTZDtype)
    # 00:00 -0500 is 05:00 UTC
    assert df["timestamp"].iloc[0].hour == 5

def test_micro_consumption_pattern_itertuples_and_rolling(tmp_path):
    csv_path = tmp_path / "micro.csv"
    data = {
        "ts": ["2023-01-01 00:00", "2023-01-01 01:00", "2023-01-01 02:00"],
        "o": [10.0, 11.0, 12.0],
        "h": [12.0, 13.0, 14.0],
        "l": [9.0, 10.0, 11.0],
        "c": [11.0, 12.0, 13.0],
        "v": [100, 200, 300]
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)
    
    df = load_ohlcv(csv_path)
    
    # Test strict attribute access (used in paper loop)
    for row in df.itertuples():
        assert hasattr(row, 'timestamp')
        assert hasattr(row, 'close')
        assert hasattr(row, 'volume')
        assert isinstance(row.close, float)
    
    # Test rolling capability
    ma = df['close'].rolling(2).mean()
    assert pd.isna(ma.iloc[0])
    assert ma.iloc[1] == 11.5
