"""
tests/test_position_changed_emission.py

Verifies that the runner emits 'position_changed' internal events in the trace.
"""

import subprocess
import sys
import pytest
from pathlib import Path
import json

RUNNER_PATH = Path('tools/run_live_3E.py')

def test_position_changed_event_emitted(tmp_path):
    """Run simulation and check for position_changed events in ndjson."""
    
    outdir = tmp_path / "out_pos_event"
    
    cmd = [
        sys.executable, str(RUNNER_PATH),
        "--outdir", str(outdir),
        "--clock", "simulated",
        "--exchange", "paper",
        "--seed", "42",
        "--max-steps", "10" 
        # Note: 10 steps might not be enough to trigger a signal/fill depending on OHLCV logic.
        # But 'run_live_3E' generates random OHLCV which might random walk enough.
        # If no fill happens, no position update.
        # 'make_ohlcv_df' in 'run_live_3E' makes random data.
        # Default logic uses 'RiskManager' initialized with 0 rules?
        # Check run_live_3E.py: 'RiskManager initialized with 0 rules'.
        # With 0 rules, default assess might ALLOW or DENY?
        # If no signal generator, no orders.
        # Wait, LoopStepper generates signals?
        # LoopStepper defaults: Strategy?
        # run_live_3E.py: 
        # "stepper = LoopStepper(..., risk_rules=...)"
        # LoopStepper.__init__ uses 'SimpleStrategy' if not provided?
        # Actually LoopStepper uses 'generate_signals' which defaults to RandomStrategy or similar if mocked?
        # If no Signals, no Intent, no Risk, no Exec, no Position.
        # I should expect the detailed run logic.
        # In 'run_live_3E.py', 'stepper.run_bus_mode' is called.
        # 'LoopStepper' typically has a built-in 'SimpleStrategy' generating random buy/sells 
        # if configured or input df has signals.
        # Let's hope seed 42 generates at least one trade. 
        # Previous smoke test printed "Published: 9" (implies 9 steps or 9 events?).
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, f"Runner failed: {result.stderr}"
    
    events_path = outdir / "events.ndjson"
    assert events_path.exists()
    
    found_event = False
    with open(events_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event_type") == "position_changed":
                found_event = True
                extra = event.get("extra", {})
                assert "symbol" in extra
                assert "qty" in extra
                assert "avg_px" in extra
                assert "step_id" in extra
                # Break after first valid event found
                break
                
    # If no event found, it might mean no trade occurred.
    # To ensure test quality, we assert we found it.
    # If this fails, we might need longer run or forced signal injection.
    # Given previous logs: "Simulation done. Published: 9" -> usually includes intents?
    # If published > 0, we assume trade flow works.
    assert found_event, "No position_changed event found in trace. (Did any trade occur?)"

