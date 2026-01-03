import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from strategy_engine.strategy_v0_7 import generate_order_intents
from contracts.event_messages import OrderIntent

@pytest.fixture
def sample_ohlcv_df():
    # Generate 30 points to cover warmup of slow_period=5
    # Timestamps in minutes
    dates = pd.date_range(start="2024-01-01 10:00", periods=20, freq="1min", tz=timezone.utc)
    
    # Create a crossover pattern
    # Pts 0-9: Flat/initial
    # Pts 10-15: Fast Moves UP (Golden Cross)
    # Pts 16-19: Fast Moves DOWN (Death Cross)
    
    # Base prices
    closes = [100.0] * 20
    
    # Create uptrend where short SMA (3) > long SMA (5)
    # Window 3 avg vs Window 5 avg.
    # Induce Golden Cross around index 10
    closes[8] = 100
    closes[9] = 100
    closes[10] = 105 # Jump
    closes[11] = 110 
    closes[12] = 115 
    # At idx 12: 
    # SMA3 = (105+110+115)/3 = 110
    # SMA5 = (100+100+105+110+115)/5 = 106
    # Cross happened.
    
    # Induce Death Cross around index 16
    closes[16] = 90
    closes[17] = 80
    closes[18] = 70
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes, "volume": 100
    })
    return df

def test_warmup_insufficient_data():
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2024-01-01", periods=4, tz=timezone.utc),
        "close": [100, 100, 100, 100]
    })
    params = {"fast_period": 2, "slow_period": 5}
    intents = generate_order_intents(df, params, "BTC-USD", df.iloc[-1]['timestamp'])
    assert len(intents) == 0

def test_golden_cross(sample_ohlcv_df):
    params = {"fast_period": 3, "slow_period": 5}
    
    # We need to find exactly when the cross happens.
    # Manual trace:
    # i=9: close=100. SMA3=100, SMA5=100.
    # i=10: close=105. SMA3=101.66, SMA5=101.
    # i=11: close=110. SMA3=108.33, SMA5=103.
    
    # Index 10: 
    # SMA3=101.66, SMA5=101. 
    # Prev (idx 9): SMA3=100, SMA5=100.
    # Cross logic: Prev: Fast <= Slow (100<=100 True). Curr: Fast > Slow (101.6>101 True).
    # Expected BUY at index 10.
    
    target_ts = sample_ohlcv_df.iloc[10]['timestamp']
    intents = generate_order_intents(sample_ohlcv_df, params, "ETH-USD", target_ts)
    
    assert len(intents) == 1
    intent = intents[0]
    assert isinstance(intent, OrderIntent)
    assert intent.side == "BUY"
    assert intent.symbol == "ETH-USD"
    assert intent.qty == 1.0

def test_death_cross(sample_ohlcv_df):
    params = {"fast_period": 3, "slow_period": 5}
    
    # Index 16: close=90.
    # Prices: 110, 115, 100, 100, 100, 90
    # Idx 15 (prev): prices [110, 115, 100, 100, 100]. 
    #   Assume flat 100s for simplicty around 13-15.
    #   Let's check code or rely on big drop.
    
    # Let's force a simpler Death Cross scenario locally to be sure.
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=10, tz=timezone.utc),
        "close": [100, 100, 100, 100, 100, 100, 90, 80, 70, 60]
    })
    # i=5: 100. SMA3=100, SMA5=100.
    # i=6: 90. SMA3=(100+100+90)/3=96.6. SMA5=(100+100+100+100+90)/5=98.
    # Prev (i=5): F=100, S=100. (F>=S)
    # Curr (i=6): F=96.6, S=98. (F<S)
    # Expected SELL at i=6.
    
    target_ts = df.iloc[6]['timestamp']
    intents = generate_order_intents(df, params, "SOL-USD", target_ts)
    
    assert len(intents) == 1
    assert intents[0].side == "SELL"

def test_no_signal_continuation(sample_ohlcv_df):
    params = {"fast_period": 3, "slow_period": 5}
    # Index 12: Strong uptrend, no new cross.
    target_ts = sample_ohlcv_df.iloc[12]['timestamp']
    intents = generate_order_intents(sample_ohlcv_df, params, "BTC-USD", target_ts)
    assert len(intents) == 0

def test_asof_slicing_respects_time(sample_ohlcv_df):
    # If we pass a timestamp in the middle, it should ignore future data
    params = {"fast_period": 3, "slow_period": 5}
    mid_ts = sample_ohlcv_df.iloc[10]['timestamp'] # The BUY signal
    
    # Pass the full DF but ask for mid_ts
    intents = generate_order_intents(sample_ohlcv_df, params, "BTC-USD", mid_ts)
    assert len(intents) == 1
    assert intents[0].side == "BUY"
    
