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
        OrderIntent(symbol="BTC-USD", side="BUY", qty=1.0, event_id="ev1"),
        OrderIntent(symbol="ETH-USD", side="SELL", qty=10.0, event_id="ev2")
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
    loop = PaperLoop(str(risk_config), seed=123)
    loop.run(str(signals_file), str(run_dir), max_events=10)
    
    # Check outputs
    events_path = run_dir / "events.ndjson"
    metrics_path = run_dir / "metrics.json"
    
    assert events_path.exists()
    assert metrics_path.exists()
    
    # Check metrics
    with metrics_path.open() as f:
        metrics = json.load(f)
    
    assert metrics["n_signals"] == 2
    # Outcome depends on RiskManager logic which might reject if no price etc,
    # but the loop mocks prices so it might allow.
    # We mainly check that it processed.
    assert metrics["n_allowed"] + metrics["n_rejected"] == 2
    
    # Check events trace
    lines = events_path.read_text().strip().split("\n")
    # 2 signals -> 2 Intents + 2 Decisions + (0 or 2 Reports)
    # Total lines >= 4
    assert len(lines) >= 4
    
    # Verify we have at least one RiskDecision
    decisions = [json.loads(line) for line in lines if "RiskDecision" in line]
    assert len(decisions) >= 2
    assert decisions[0]["schema_id"] == "RiskDecision"
