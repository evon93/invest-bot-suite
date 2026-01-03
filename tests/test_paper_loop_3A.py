"""
tests/test_paper_loop_3A.py

Integration test for tools/run_paper_loop_3A.py.
"""
import pytest
import json
import shutil
from pathlib import Path
from tools.run_paper_loop_3A import PaperLoop, OrderIntent

@pytest.fixture
def run_dir(tmp_path):
    d = tmp_path / "run_paper_smoke"
    d.mkdir()
    return d

@pytest.fixture
def signals_file(tmp_path):
    f = tmp_path / "signals.ndjson"
    intents = [
        OrderIntent(symbol="BTC-USD", side="BUY", qty=1.0, event_id="ev1", limit_price=100.0, trace_id="tr1"),
        OrderIntent(symbol="ETH-USD", side="SELL", qty=10.0, event_id="ev2", limit_price=200.0, trace_id="tr2")
    ]
    with f.open("w") as out:
        for i in intents:
            out.write(i.to_json() + "\n")
    return f

@pytest.fixture
def risk_config(tmp_path):
    # Minimal config that satisfies risk_manager_factory
    f = tmp_path / "risk_test.yaml"
    cfg = {
        "risk_manager": {"version": "0.4", "mode": "active"},
        "max_drawdown": {"hard_limit_pct": 0.2}, # Relaxed
        "position_limits": {"max_single_asset_pct": 1.0}
    }
    import yaml
    with f.open("w") as out:
        yaml.dump(cfg, out)
    return f

def test_paper_loop_run(run_dir, signals_file, risk_config):
    # Run with 0 latency for speed
    loop = PaperLoop(str(risk_config), seed=123, latency_ms=0.0)
    loop.run(str(signals_file), str(run_dir), max_events=10)
    
    # Check outputs
    events_path = run_dir / "events.ndjson"
    metrics_path = run_dir / "metrics.json"
    
    assert events_path.exists()
    assert metrics_path.exists()
    
    # Check Metrics
    with metrics_path.open() as f:
        metrics = json.load(f)
    
    assert metrics["n_signals"] == 2
    # Check observability fields
    assert "max_drawdown_pct" in metrics
    assert "max_gross_exposure_pct" in metrics
    assert "active_rate" in metrics
    assert "latency_ms_mean" in metrics
    assert "latency_ms_p95" in metrics
    
    # Check hardening: aliases
    assert "rejected_by_reason" in metrics
    assert metrics["rejected_by_reason"] == metrics["rejection_reasons"]
    
    # Verify ranges
    assert metrics["max_drawdown_pct"] <= 0.0
    assert metrics["max_gross_exposure_pct"] >= 0.0
    assert 0.0 <= metrics["active_rate"] <= 1.0
    
    # Check Trace ID propagation
    lines = events_path.read_text().strip().split("\n")
    risk_events = [json.loads(line) for line in lines if "RiskDecision" in line]
    assert len(risk_events) >= 1
    # Check that trace_id matches input (tr1 or tr2)
    assert risk_events[0]["trace_id"] in ["tr1", "tr2"]
