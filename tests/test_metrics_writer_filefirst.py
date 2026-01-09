"""
tests/test_metrics_writer_filefirst.py

Tests for MetricsWriter file-first persistence.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.metrics_collector import MetricsWriter


class TestMetricsWriterBasic:
    """Basic functionality tests."""
    
    def test_creates_ndjson_file(self, tmp_path):
        """Writer creates NDJSON file on first append."""
        writer = MetricsWriter(run_dir=tmp_path)
        
        writer.append_event({"type": "test", "value": 42})
        writer.close()
        
        ndjson_path = tmp_path / "metrics.ndjson"
        assert ndjson_path.exists()
        
        # Read and parse
        with open(ndjson_path, "r") as f:
            line = f.readline()
            data = json.loads(line)
        
        assert data["type"] == "test"
        assert data["value"] == 42
    
    def test_appends_multiple_events(self, tmp_path):
        """Multiple events appended to same file."""
        writer = MetricsWriter(run_dir=tmp_path)
        
        for i in range(5):
            writer.append_event({"index": i})
        
        writer.close()
        
        ndjson_path = tmp_path / "metrics.ndjson"
        with open(ndjson_path, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == 5
        
        # Verify ordering
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["index"] == i
    
    def test_writes_summary_json(self, tmp_path):
        """Summary JSON written correctly."""
        writer = MetricsWriter(run_dir=tmp_path)
        
        summary = {
            "processed": 100,
            "filled": 50,
            "errors": 5,
        }
        writer.write_summary(summary)
        writer.close()
        
        summary_path = tmp_path / "metrics_summary.json"
        assert summary_path.exists()
        
        with open(summary_path, "r") as f:
            loaded = json.load(f)
        
        assert loaded["processed"] == 100
        assert loaded["filled"] == 50
        assert loaded["errors"] == 5


class TestMetricsWriterNoOp:
    """No-op mode tests (run_dir=None)."""
    
    def test_noop_enabled_false(self):
        """Writer with no run_dir has enabled=False."""
        writer = MetricsWriter(run_dir=None)
        
        assert writer.enabled is False
    
    def test_noop_append_does_nothing(self):
        """Append in no-op mode doesn't raise."""
        writer = MetricsWriter(run_dir=None)
        
        # Should not raise
        writer.append_event({"test": "data"})
        writer.close()
    
    def test_noop_summary_does_nothing(self):
        """Summary in no-op mode doesn't raise."""
        writer = MetricsWriter(run_dir=None)
        
        # Should not raise
        writer.write_summary({"test": "summary"})
        writer.close()


class TestMetricsWriterPersistence:
    """Persistence across writer instances."""
    
    def test_append_persists_and_reopens(self, tmp_path):
        """Events persist across writer close/reopen."""
        # First writer
        writer1 = MetricsWriter(run_dir=tmp_path)
        writer1.append_event({"phase": 1, "count": 10})
        writer1.close()
        
        # Second writer (append mode)
        writer2 = MetricsWriter(run_dir=tmp_path)
        writer2.append_event({"phase": 2, "count": 20})
        writer2.close()
        
        ndjson_path = tmp_path / "metrics.ndjson"
        with open(ndjson_path, "r") as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        data1 = json.loads(lines[0])
        data2 = json.loads(lines[1])
        
        assert data1["phase"] == 1
        assert data2["phase"] == 2


class TestMetricsWriterDeterminism:
    """Determinism tests."""
    
    def test_keys_sorted_in_output(self, tmp_path):
        """JSON keys are sorted for deterministic output."""
        writer = MetricsWriter(run_dir=tmp_path)
        
        # Unsorted input
        writer.append_event({"z_field": 1, "a_field": 2, "m_field": 3})
        writer.close()
        
        ndjson_path = tmp_path / "metrics.ndjson"
        with open(ndjson_path, "r") as f:
            line = f.readline().strip()
        
        # Should be sorted: a_field, m_field, z_field
        assert line.index("a_field") < line.index("m_field")
        assert line.index("m_field") < line.index("z_field")
