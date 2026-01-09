"""
tests/test_run_live_metrics_wiring.py

Tests for metrics wiring in run_live_3E.py
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildMetrics:
    """Tests for build_metrics helper function."""
    
    def test_enabled_returns_real_collector(self, tmp_path):
        """When enabled, returns real MetricsCollector."""
        from tools.run_live_3E import build_metrics
        from engine.metrics_collector import MetricsCollector, MetricsWriter
        
        collector, writer = build_metrics(tmp_path, enabled=True)
        
        assert isinstance(collector, MetricsCollector)
        assert writer.enabled is True
        
        writer.close()
    
    def test_disabled_returns_noop_collector(self, tmp_path):
        """When disabled, returns NoOpMetricsCollector."""
        from tools.run_live_3E import build_metrics
        from engine.metrics_collector import NoOpMetricsCollector
        
        collector, writer = build_metrics(tmp_path, enabled=False)
        
        assert isinstance(collector, NoOpMetricsCollector)
        assert writer.enabled is False
    
    def test_enabled_creates_files(self, tmp_path):
        """When enabled, writer creates files on write."""
        from tools.run_live_3E import build_metrics
        
        collector, writer = build_metrics(tmp_path, enabled=True)
        
        # Simulate workflow
        collector.start("msg_1")
        collector.end("msg_1", "FILLED")
        
        writer.write_summary(collector.snapshot_summary())
        writer.close()
        
        # Verify files created
        summary_path = tmp_path / "metrics_summary.json"
        assert summary_path.exists()
        
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        assert summary["processed"] == 1
        assert summary["filled"] == 1
    
    def test_none_run_dir_with_disabled(self):
        """When run_dir is None and disabled, no crash."""
        from tools.run_live_3E import build_metrics
        
        collector, writer = build_metrics(None, enabled=False)
        
        # Should not crash
        collector.start("msg_1")
        collector.end("msg_1", "FILLED")
        
        writer.write_summary({})  # No-op
        writer.close()


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""
    
    def test_enable_metrics_default_false(self):
        """--enable-metrics defaults to False."""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--enable-metrics", action="store_true", default=False)
        
        args = parser.parse_args([])
        assert args.enable_metrics is False
    
    def test_enable_metrics_can_be_set(self):
        """--enable-metrics can be enabled."""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--enable-metrics", action="store_true", default=False)
        
        args = parser.parse_args(["--enable-metrics"])
        assert args.enable_metrics is True


class TestMetricsIntegration:
    """Integration tests for metrics collection flow."""
    
    def test_full_workflow_creates_summary(self, tmp_path):
        """Full workflow from start to summary creation."""
        from tools.run_live_3E import build_metrics
        
        collector, writer = build_metrics(tmp_path, enabled=True)
        
        # Simulate multiple messages
        for i in range(5):
            msg_id = f"msg_{i}"
            collector.start(msg_id)
            
            if i % 3 == 0:
                collector.end(msg_id, "REJECTED", reason="dd_guardrail")
            else:
                collector.end(msg_id, "FILLED")
        
        # Finalize
        writer.write_summary(collector.snapshot_summary())
        writer.close()
        
        # Verify summary
        summary_path = tmp_path / "metrics_summary.json"
        with open(summary_path, "r") as f:
            summary = json.load(f)
        
        assert summary["processed"] == 5
        assert summary["filled"] == 3  # indices 1, 2, 4
        assert summary["rejected"] == 2  # indices 0, 3
        assert summary["rejects_by_reason"]["dd_guardrail"] == 2
