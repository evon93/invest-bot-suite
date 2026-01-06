"""
tests/test_3D_canonical_smoke.py

Smoke test for the canonical 3D runner.
Verifies artifact generation, metrics coherence, and absence of timestamps.

Part of Ticket AG-3D-6-1.
"""

import sys
import json
import pytest
import subprocess
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCanonicalRunnerSmoke:
    
    def test_runner_execution_and_artifacts(self, tmp_path: Path):
        """Run the canonical runner and verify artifacts."""
        runner_script = Path("tools/run_3D_canonical.py").resolve()
        out_dir = tmp_path / "out_3D6"
        
        # 1. Execute Runner
        cmd = [
            sys.executable,
            str(runner_script),
            "--outdir", str(out_dir),
            "--seed", "42",
            "--max-steps", "25",
            "--num-signals", "3",
        ]
        
        # Run process
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd() # Run from repo root
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        # 2. Check Artifacts Existence
        trace_path = out_dir / "trace.jsonl"
        metrics_path = out_dir / "run_metrics.json"
        meta_path = out_dir / "run_meta.json"
        state_db_path = out_dir / "state.db"
        
        assert trace_path.exists(), "trace.jsonl missing"
        assert metrics_path.exists(), "run_metrics.json missing"
        assert meta_path.exists(), "run_meta.json missing"
        # state.db is optional but our runner creates it
        
        # 3. Check Metrics Content & Coherence
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
            
        required_keys = [
            "num_order_intents",
            "num_risk_decisions_total",
            "num_execution_reports",
            "num_fills",
            "unique_trace_ids",
            "max_step_id",
        ]
        for k in required_keys:
            assert k in metrics, f"Metric {k} missing"
            
        # Coherence (Conservation of events)
        # Intents -> Risk Decisions
        assert metrics["num_order_intents"] == metrics["num_risk_decisions_total"]
        
        # Risk Decisions -> Allowed + Rejected
        # (Assuming risk worker logs allowed/rejected correctly)
        assert metrics["num_risk_decisions_total"] == (
            metrics.get("num_risk_allowed", 0) + metrics.get("num_risk_rejected", 0)
        )
        
        # Allowed -> Execution Reports
        assert metrics.get("num_risk_allowed", 0) == metrics["num_execution_reports"]
        
        # Reports -> Fills
        assert metrics["num_execution_reports"] == metrics["num_fills"]
        
        # Unique Trace IDs should match Intents (if all initiated from intents)
        # Note: trace IDs count excludes SYSTEM/BusModeDone, so it should match intents count
        assert metrics["unique_trace_ids"] == metrics["num_order_intents"]
        
        # 4. Check Absence of Timestamps
        # Scan trace.jsonl
        with open(trace_path, "r") as f:
            for line in f:
                assert "timestamp" not in line.lower(), f"Timestamp found in log: {line}"
                assert "asctime" not in line.lower(), f"Asctime found in log: {line}"
        
        # Scan run_meta.json
        with open(meta_path, "r") as f:
            meta = json.load(f)
            # Ensure no obvious time fields
            for k in meta.keys():
                assert "time" not in k.lower(), f"Time field in meta: {k}"

    def test_runner_strict_mode(self, tmp_path: Path):
        """Verify strict mode fails on invalid config."""
        runner_script = Path("tools/run_3D_canonical.py").resolve()
        out_dir = tmp_path / "out_strict"
        
        # Create invalid risk rules
        invalid_rules = tmp_path / "invalid_rules.yaml"
        with open(invalid_rules, "w") as f:
            f.write("invalid_yaml: [}")
            
        cmd = [
            sys.executable,
            str(runner_script),
            "--outdir", str(out_dir),
            "--risk-rules", str(invalid_rules),
            "--strict-risk-config", "1",
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0, "Should fail with invalid rules in strict mode"
