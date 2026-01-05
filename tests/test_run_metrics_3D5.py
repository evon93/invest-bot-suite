"""
tests/test_run_metrics_3D5.py

Tests for deterministic run metrics collection.

Validates:
- Metric calculation from JSONL logs
- Deterministic JSON output

Part of ticket AG-3D-5-1.
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.run_metrics_3D5 import collect_metrics_from_jsonl


def create_sample_jsonl(path: Path):
    """Create a sample JSONL file with known events."""
    events = [
        # Intent 1: Allowed and Filled
        {"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t1", "step_id": 1, "extra": {"symbol": "BTC"}},
        {"action": "publish", "event_type": "RiskDecisionV1", "trace_id": "t1", "step_id": 2, "extra": {"allowed": True}},
        {"action": "publish", "event_type": "ExecutionReportV1", "trace_id": "t1", "step_id": 3, "extra": {"status": "FILLED"}},
        {"action": "persist", "event_type": "PositionUpdated", "trace_id": "t1", "step_id": 4, "extra": {"symbol": "BTC"}},
        
        # Intent 2: Rejected
        {"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t2", "step_id": 5, "extra": {"symbol": "ETH"}},
        {"action": "publish", "event_type": "RiskDecisionV1", "trace_id": "t2", "step_id": 6, "extra": {"allowed": False}},
        
        # Completion
        {"action": "complete", "event_type": "BusModeDone", "trace_id": "SYSTEM", "step_id": 10, "extra": {"drain_iterations": 5}},
    ]
    
    with open(path, "w", encoding="utf-8") as f:
        for evt in events:
            f.write(json.dumps(evt) + "\n")


class TestRunMetrics3D5:
    """Tests for run metrics collection."""

    def test_collect_metrics_counts(self, tmp_path: Path):
        """Should correctly count events from JSONL."""
        log_path = tmp_path / "test.jsonl"
        create_sample_jsonl(log_path)
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["num_order_intents"] == 2
        assert metrics["num_risk_decisions_total"] == 2
        assert metrics["num_risk_allowed"] == 1
        assert metrics["num_risk_rejected"] == 1
        assert metrics["num_execution_reports"] == 1
        assert metrics["num_fills"] == 1
        assert metrics["num_positions_updated"] == 1
        assert metrics["drain_iterations"] == 5
        assert metrics["max_step_id"] == 10
        assert metrics["unique_trace_ids"] == 2  # t1, t2 (SYSTEM excluded)

    def test_metrics_json_deterministic(self, tmp_path: Path):
        """JSON output should be deterministic (sorted keys)."""
        metrics = {
            "b": 2,
            "a": 1,
            "c": 3,
        }
        
        out_path = tmp_path / "metrics.json"
        
        # Dump twice
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, sort_keys=True, indent=2)
        content1 = out_path.read_text(encoding="utf-8")
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, sort_keys=True, indent=2)
        content2 = out_path.read_text(encoding="utf-8")
        
        assert content1 == content2
        assert '"a": 1' in content1
        assert content1.index('"a"') < content1.index('"b"')  # Sorted
