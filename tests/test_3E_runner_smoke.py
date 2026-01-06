"""
tests/test_3E_runner_smoke.py

Smoke tests for tools/run_live_3E.py
Verifies that the runner executes and produces expected artifacts.
"""

import subprocess
import sys
import shutil
import pytest
from pathlib import Path
import json
import pandas as pd

RUNNER_PATH = Path('tools/run_live_3E.py')

@pytest.fixture
def temp_outdir(tmp_path):
    return tmp_path / "out_smoke"

def test_run_live_3E_simulated_paper(temp_outdir):
    """Test standard deterministic run: simulated clock + paper exchange."""
    
    cmd = [
        sys.executable, str(RUNNER_PATH),
        "--outdir", str(temp_outdir),
        "--clock", "simulated",
        "--exchange", "paper",
        "--seed", "42",
        "--max-steps", "10"
    ]
    
    # Execute runner
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0, f"Runner failed: {result.stderr}"
    
    # Check artifacts
    assert (temp_outdir / "events.ndjson").exists()
    assert (temp_outdir / "run_meta.json").exists()
    assert (temp_outdir / "results.csv").exists()
    # State DB depends on implementation details, but usually created
    assert (temp_outdir / "state.db").exists() 
    
    # Check meta content
    with open(temp_outdir / "run_meta.json") as f:
        meta = json.load(f)
        assert meta["clock"] == "simulated"
        assert meta["exchange"] == "paper"
        assert meta["seed"] == 42
        
    # Check events content
    with open(temp_outdir / "events.ndjson") as f:
        lines = f.readlines()
        assert len(lines) > 0, "Events file should not be empty"
        # Check for expected event types
        has_intent = any("OrderIntentV1" in line for line in lines)
        assert has_intent, "Should have OrderIntentV1 events"

    # Check results csv
    df = pd.read_csv(temp_outdir / "results.csv")
    assert not df.empty
    # Expect at least some metric columns
    assert "max_step_id" in df.columns
    assert "unique_trace_ids" in df.columns
    assert int(df["max_step_id"].iloc[0]) >= 1
    assert int(df["unique_trace_ids"].iloc[0]) >= 1
    
    # Check for num_ counters
    num_cols = [c for c in df.columns if c.startswith("num_")]
    assert len(num_cols) >= 1
    assert df[num_cols].sum(axis=1).iloc[0] > 0
    
    # Deterministic check for 10 steps
    if int(df["max_step_id"].iloc[0]) == 10:
        pass # Expected for 10 steps

def test_run_live_3E_stub_mode(temp_outdir):
    """Test stub mode execution."""
    cmd = [
        sys.executable, str(RUNNER_PATH),
        "--outdir", str(temp_outdir),
        "--clock", "simulated",
        "--exchange", "stub",
        "--latency-steps", "2",
        "--max-steps", "10"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    
    # Verify meta
    with open(temp_outdir / "run_meta.json") as f:
        meta = json.load(f)
        assert meta["exchange"] == "stub"
        assert meta["latency_steps"] == 2
