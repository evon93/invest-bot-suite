import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
    
from backtest_initial import SimpleBacktester, calculate_metrics

# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------
@pytest.fixture
def synthetic_prices():
    dates = pd.date_range(datetime(2023, 1, 1), periods=100)
    base = np.linspace(100, 150, 100)
    noise = np.random.normal(0, 5, 100)
    return pd.Series(base + noise, index=dates, name='price')

@pytest.fixture
def crash_prices():
    dates = pd.date_range(datetime(2023, 1, 1), periods=100)
    prices = np.linspace(100, 150, 100)
    prices[50:] *= 0.6   # −40 % crash
    return pd.Series(prices, index=dates, name='price')

# ------------------------------------------------------------------------------
# Métricas
# ------------------------------------------------------------------------------
def test_metrics_calculation(synthetic_prices):
    backtester = SimpleBacktester(synthetic_prices)
    portfolio = backtester.run()
    metrics = calculate_metrics(portfolio)
    assert -0.5 < metrics['max_drawdown'] < 0
    assert -0.5 < metrics['cagr'] < 2.0

def test_metrics_after_crash(crash_prices):
    backtester = SimpleBacktester(crash_prices)
    portfolio = backtester.run()
    metrics = calculate_metrics(portfolio)
    assert metrics['max_drawdown'] <= -0.35
    assert metrics['cagr'] < 0

# ------------------------------------------------------------------------------
# Rebalanceo
# ------------------------------------------------------------------------------
def test_rebalance_frequency(synthetic_prices):
    backtester = SimpleBacktester(synthetic_prices)
    backtester.run()
    trade_days = sorted({t['date'] for t in backtester.trades})
    assert len(trade_days) >= 3        # al menos 3 rebalanceos en 100 días
    intervals = [ (trade_days[i+1] - trade_days[i]).days for i in range(len(trade_days)-1) ]
    assert 25 < sum(intervals)/len(intervals) < 35

def test_no_rebalance_on_weekend():
    dates = pd.date_range(datetime(2023, 1, 1), periods=30, freq='D')
    prices = pd.Series(np.random.uniform(100, 110, 30), index=dates)
    backtester = SimpleBacktester(prices)
    backtester.run()
    for tr in backtester.trades:
        assert tr['date'].weekday() < 5, "Trade en fin de semana"

# ------------------------------------------------------------------------------
# Bordes y consistencia
# ------------------------------------------------------------------------------
def test_zero_prices():
    dates = pd.date_range(datetime(2023, 1, 1), periods=10)
    prices = pd.Series([100, 0, -5, 150, 200, 0, 180, 190, 200, 210], index=dates)
    backtester = SimpleBacktester(prices)
    portfolio = backtester.run()
    assert portfolio.iloc[-1]['value'] > 0

def test_single_day_backtest():
    prices = pd.Series([100], index=[datetime(2023, 1, 1)])
    backtester = SimpleBacktester(prices)
    portfolio = backtester.run()
    assert len(portfolio) == 1
    assert len(backtester.trades) == 0
