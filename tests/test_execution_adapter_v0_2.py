import pytest
from contracts.event_messages import OrderIntent, ExecutionReport
from execution.execution_adapter_v0_2 import simulate_execution

def test_execution_deterministic_seed_42():
    intent = OrderIntent(
        symbol="BTC-USD",
        side="BUY",
        qty=1.0,
        meta={"current_price": 50000.0}
    )
    
    cfg = {"slippage_bps": 5.0, "avg_latency_ms": 100.0}
    
    # Run 1
    reports1 = simulate_execution([intent], cfg, seed=42)
    
    # Run 2
    reports2 = simulate_execution([intent], cfg, seed=42)
    
    assert len(reports1) == 1
    assert len(reports2) == 1
    
    r1 = reports1[0]
    r2 = reports2[0]
    
    assert r1.filled_qty == r2.filled_qty
    assert r1.avg_price == r2.avg_price
    assert r1.latency_ms == r2.latency_ms
    assert r1.slippage == r2.slippage

def test_partial_fills_qty_conservation():
    intent = OrderIntent(
        symbol="ETH-USD",
        side="SELL",
        qty=10.0,
        meta={"current_price": 3000.0}
    )
    
    cfg = {
        "slippage_bps": 2.0,
        "avg_latency_ms": 50.0,
        "partial_fill": True
    }
    
    # Use a seed that triggers >1 splits usually
    reports = simulate_execution([intent], cfg, seed=99)
    
    assert len(reports) > 1 # Expect splits
    
    total_filled = sum(r.filled_qty for r in reports)
    assert abs(total_filled - 10.0) < 1e-9
    
    # Check status
    assert reports[0].status == "PARTIALLY_FILLED"
    assert reports[-1].status == "FILLED"

def test_slippage_directionality_buy_vs_sell():
    # BUY should fill HIGHER than ref
    intent_buy = OrderIntent(symbol="A", side="BUY", qty=1.0, meta={"current_price": 100.0})
    
    # SELL should fill LOWER than ref
    intent_sell = OrderIntent(symbol="B", side="SELL", qty=1.0, meta={"current_price": 100.0})
    
    cfg = {"slippage_bps": 10.0} # 10 bps = 0.1% -> ~100.1 or 99.9
    
    reports_buy = simulate_execution([intent_buy], cfg, seed=1)
    reports_sell = simulate_execution([intent_sell], cfg, seed=1)
    
    fill_buy = reports_buy[0].avg_price
    fill_sell = reports_sell[0].avg_price
    
    assert fill_buy > 100.0
    assert fill_sell < 100.0
    
    # Check magnitude roughly
    # 10bps = 0.001 * 100 = 0.1. So fill_buy ~ 100.1, fill_sell ~ 99.9
    # allowing variance from RNG
    assert 100.0 < fill_buy < 101.0
    assert 99.0 < fill_sell < 100.0

def test_latency_reporting():
    intent = OrderIntent(symbol="C", side="BUY", qty=1.0, meta={"current_price": 10.0})
    cfg = {"avg_latency_ms": 200.0}
    
    reports = simulate_execution([intent], cfg, seed=123)
    r = reports[0]
    
    assert r.latency_ms is not None
    assert r.latency_ms > 0
    # Check roughly around 200
    assert 100 < r.latency_ms < 300
