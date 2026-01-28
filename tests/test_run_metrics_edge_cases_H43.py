"""
tests/test_run_metrics_edge_cases_H43.py

Edge case tests for engine/run_metrics_3D5.py.
Extends existing coverage with:
- Empty file handling
- Malformed JSON lines
- Missing fields graceful handling

Part of ticket AG-H4-3-1.
"""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.run_metrics_3D5 import collect_metrics_from_jsonl


class TestRunMetricsEdgeCases:
    """Edge case tests for run metrics collection."""

    def test_nonexistent_file_returns_zero_metrics(self, tmp_path: Path):
        """Missing file should return zero metrics, not raise."""
        missing = tmp_path / "nonexistent.jsonl"
        metrics = collect_metrics_from_jsonl(missing)
        
        assert metrics["num_order_intents"] == 0
        assert metrics["num_risk_decisions_total"] == 0
        assert metrics["unique_trace_ids"] == 0

    def test_empty_file_returns_zero_metrics(self, tmp_path: Path):
        """Empty file should return zero metrics."""
        empty = tmp_path / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(empty)
        
        assert metrics["num_order_intents"] == 0
        assert metrics["max_step_id"] == 0

    def test_malformed_json_lines_skipped(self, tmp_path: Path):
        """Malformed JSON lines should be skipped gracefully."""
        log_path = tmp_path / "mixed.jsonl"
        lines = [
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t1", "step_id": 1, "extra": {}}',
            'this is not valid json',
            '{"unclosed": bracket',
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t2", "step_id": 2, "extra": {}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        # Should count only the 2 valid OrderIntentV1 events
        assert metrics["num_order_intents"] == 2
        assert metrics["unique_trace_ids"] == 2

    def test_blank_lines_skipped(self, tmp_path: Path):
        """Blank lines in file should be skipped."""
        log_path = tmp_path / "blanks.jsonl"
        lines = [
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t1", "step_id": 1, "extra": {}}',
            '',
            '   ',
            '{"action": "publish", "event_type": "RiskDecisionV1", "trace_id": "t1", "step_id": 2, "extra": {"allowed": true}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["num_order_intents"] == 1
        assert metrics["num_risk_allowed"] == 1

    def test_missing_optional_fields_handled(self, tmp_path: Path):
        """Events with missing optional fields should not crash."""
        log_path = tmp_path / "minimal.jsonl"
        # Minimal events without trace_id, step_id, or extra
        lines = [
            '{"action": "publish", "event_type": "OrderIntentV1"}',
            '{"action": "publish", "event_type": "RiskDecisionV1", "extra": {}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["num_order_intents"] == 1
        assert metrics["num_risk_decisions_total"] == 1
        # allowed not present in extra → rejected
        assert metrics["num_risk_rejected"] == 1

    def test_partially_filled_counted_as_fill(self, tmp_path: Path):
        """PARTIALLY_FILLED executions should count as fills."""
        log_path = tmp_path / "partial.jsonl"
        lines = [
            '{"action": "publish", "event_type": "ExecutionReportV1", "trace_id": "t1", "step_id": 1, "extra": {"status": "PARTIALLY_FILLED"}}',
            '{"action": "publish", "event_type": "ExecutionReportV1", "trace_id": "t2", "step_id": 2, "extra": {"status": "REJECTED"}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["num_execution_reports"] == 2
        assert metrics["num_fills"] == 1  # Only PARTIALLY_FILLED

    def test_system_trace_id_excluded_from_unique_count(self, tmp_path: Path):
        """SYSTEM trace_id should not be counted in unique_trace_ids."""
        log_path = tmp_path / "system.jsonl"
        lines = [
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t1", "step_id": 1, "extra": {}}',
            '{"action": "complete", "event_type": "BusModeDone", "trace_id": "SYSTEM", "step_id": 10, "extra": {"drain_iterations": 3}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["unique_trace_ids"] == 1  # Only t1, SYSTEM excluded
        assert metrics["drain_iterations"] == 3

    def test_non_integer_step_id_ignored(self, tmp_path: Path):
        """Non-integer step_id should not update max_step_id."""
        log_path = tmp_path / "bad_step.jsonl"
        lines = [
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t1", "step_id": 5, "extra": {}}',
            '{"action": "publish", "event_type": "OrderIntentV1", "trace_id": "t2", "step_id": "not_a_number", "extra": {}}',
        ]
        log_path.write_text("\n".join(lines), encoding="utf-8")
        
        metrics = collect_metrics_from_jsonl(log_path)
        
        assert metrics["max_step_id"] == 5  # String step_id ignored
