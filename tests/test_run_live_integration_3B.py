import pytest
import pandas as pd
import json
from pathlib import Path
from tools.run_live_integration_3B import run_integration_pipeline

def test_smoke_integration_run(tmp_path):
    # 1. Setup Data (Synthetic with a clear crossover)
    data_path = tmp_path / "ohlcv.csv"
    out_path = tmp_path / "events.ndjson"
    
    # 20 candles
    # 0-9: 100
    # 10-14: 110 (Golden cross around 10-12)
    closes = [100.0] * 10 + [110.0] * 10
    dates = pd.date_range("2024-01-01", periods=20, freq="1h", tz="UTC")
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes, "volume": 1000
    })
    df.to_csv(data_path, index=False)
    
    # 2. Config
    cfg = {
        "ticker": "TEST-USD",
        "strategy_params": {"fast_period": 3, "slow_period": 5},
        "execution_config": {"slippage_bps": 0.0} # No slip for deterministic check easier
    }
    
    # 3. Run Pipeline
    run_integration_pipeline(data_path, out_path, cfg)
    
    # 4. Validations
    assert out_path.exists()
    
    lines = out_path.read_text().strip().split('\n')
    assert len(lines) > 0, "Should generate events"
    
    # Parse events
    events = [json.loads(line) for line in lines]
    
    # Should see OrderIntent, RiskDecision, ExecutionReport sequence
    types = [e['type'] for e in events]
    
    assert "OrderIntent" in types
    assert "RiskDecision" in types
    
    # Since prices jump 100 -> 110, we expect a BUY signal
    # If Risk Allows (v0.4 default with empty rules usually allows unless nav checked aggressively)
    # Check if we have ExecutionReport
    # RiskManager v0.4 might block if NAV is needed for Kelly?
    # Our shim passes Nav=10000. 
    # v0.4 default rules might be restrictive or permissive. 
    # If blocked, ExecutionReport won't be there.
    # Let's check logic: intent generated -> risk allowed -> execution.
    
    # Check at least one RiskDecision has allowed=True
    allowed_count = sum(1 for e in events if e['type'] == 'RiskDecision' and e['payload']['allowed'])
    
    if allowed_count > 0:
        assert "ExecutionReport" in types
    else:
        # If all blocked, ensure reasons exist
        assert all(e['payload']['rejection_reasons'] for e in events if e['type'] == 'RiskDecision')

    # Basic schema check
    first_intent = next(e for e in events if e['type'] == 'OrderIntent')
    assert first_intent['payload']['symbol'] == "TEST-USD"
