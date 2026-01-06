"""
tests/test_exchange_adapter_paper.py

Tests for PaperExchangeAdapter behavior.
"""

from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from engine.exchange_adapter import PaperExchangeAdapter, ExecutionContext

def test_paper_adapter_behavior():
    """Verify Paper Adapter produces expected ExecutionReportV1."""
    
    adapter = PaperExchangeAdapter(slippage_bps=5.0, fee_bps=10.0)
    
    # Synthetic inputs
    intent = OrderIntentV1(
        symbol="BTC-USD",
        side="BUY",
        qty=1.0,
        limit_price=100.0,
        event_id="order-1",
        trace_id="trace-1"
    )
    
    decision = RiskDecisionV1(
        ref_order_event_id="order-1",
        allowed=True,
        event_id="risk-1",
        trace_id="trace-1"
    )
    
    ctx: ExecutionContext = {"step_id": 1, "time_provider": None}
    
    # Execute
    report = adapter.submit(
        intent=intent,
        decision=decision,
        context=ctx,
        report_event_id="exec-1"
    )
    
    # Verification
    assert report.trace_id == "trace-1"
    assert report.ref_risk_event_id == "risk-1"
    assert report.status == "FILLED"
    assert report.filled_qty == 1.0
    
    # Price verification (5 bps slippage on 100)
    # Buy -> 100 * (1.0005) = 100.05
    assert abs(report.avg_price - 100.05) < 1e-6
    
    # Fee (10 bps of notional: 1.0 * 100.05 * 0.0010)
    expected_fee = 1.0 * 100.05 * 0.0010
    assert abs(report.fee - expected_fee) < 1e-6
    
    assert report.event_id == "exec-1"
    assert report.latency_ms == 1.0

def test_paper_adapter_meta_price_fallback():
    """Verify price fallback to metadata."""
    adapter = PaperExchangeAdapter()
    
    intent = OrderIntentV1(
        symbol="ETH-USD",
        side="SELL",
        qty=2.0,
        limit_price=None, # No limit price
        event_id="o2",
        trace_id="t2"
    )
    decision = RiskDecisionV1("o2", True, "r2", trace_id="t2", event_id="r2")
    
    # Meta provides price
    meta = {"current_price": 2000.0}
    
    report = adapter.submit(intent, decision, {"step_id": 1, "time_provider": None}, "e2", extra_meta=meta)
    
    # Sell -> 2000 * (1 - 0.0005) = 1999.0
    assert abs(report.avg_price - 1999.0) < 1e-4

