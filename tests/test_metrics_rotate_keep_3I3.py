"""
tests/test_metrics_rotate_keep_3I3.py

Tests for --metrics-rotate-keep functionality (AG-3I-3-1).

Validates:
- keep=2: Only 2 most recent rotated files retained
- keep=0: All rotated files deleted
- keep=None: No cleanup, all rotated files kept
"""

import json
import pytest
from pathlib import Path

from engine.metrics_collector import MetricsWriter


class TestMetricsRotateKeep:
    """Tests for MetricsWriter rotate_keep functionality."""
    
    def _write_events(self, writer: MetricsWriter, n: int) -> None:
        """Write n events to force rotations."""
        for i in range(n):
            writer.append_event({"idx": i, "data": "x" * 50})
    
    def test_keep_two_retains_only_two(self, tmp_path: Path):
        """With keep=2, only 2 most recent rotated files should remain."""
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=2,  # Rotate every 2 lines
            rotate_keep=2,
        )
        
        # Write enough events to trigger 4 rotations
        # 2 lines per rotation, 10 events = 5 cycles = 4 rotations
        self._write_events(writer, 10)
        writer.close()
        
        # Find rotated files
        rotated = list(tmp_path.glob("metrics.ndjson.*"))
        rotated_numeric = [p for p in rotated if p.suffix.lstrip(".").isdigit()]
        
        assert len(rotated_numeric) == 2, (
            f"Expected 2 rotated files, got {len(rotated_numeric)}: {rotated_numeric}"
        )
        
        # Verify it's the most recent ones (highest suffixes)
        suffixes = sorted([int(p.suffix.lstrip(".")) for p in rotated_numeric])
        # After 4 rotations we should have .3, .4 (most recent 2)
        # Note: the cleanup happens after rotation, so suffixes are 3, 4
        assert 1 not in suffixes, "Old rotation .1 should have been deleted"
        assert 2 not in suffixes, "Old rotation .2 should have been deleted"
        
        # Active file should exist
        active = tmp_path / "metrics.ndjson"
        assert active.exists(), "Active metrics.ndjson should exist"
    
    def test_keep_zero_deletes_all(self, tmp_path: Path):
        """With keep=0, all rotated files should be deleted."""
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=2,
            rotate_keep=0,
        )
        
        # Trigger several rotations
        self._write_events(writer, 10)
        writer.close()
        
        # Find rotated files
        rotated = list(tmp_path.glob("metrics.ndjson.*"))
        rotated_numeric = [p for p in rotated if p.suffix.lstrip(".").isdigit()]
        
        assert len(rotated_numeric) == 0, (
            f"Expected 0 rotated files with keep=0, got {len(rotated_numeric)}"
        )
        
        # Active file should exist
        assert (tmp_path / "metrics.ndjson").exists()
    
    def test_keep_none_keeps_all(self, tmp_path: Path):
        """With keep=None (default), all rotated files should be kept."""
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=2,
            rotate_keep=None,  # Default - no cleanup
        )
        
        # Trigger rotations: 10 events with max 2 lines = 5 batches = 4-5 rotations
        self._write_events(writer, 10)
        writer.close()
        
        # Find rotated files
        rotated = list(tmp_path.glob("metrics.ndjson.*"))
        rotated_numeric = [p for p in rotated if p.suffix.lstrip(".").isdigit()]
        
        # Should have all rotated files (no cleanup with keep=None)
        # The exact number depends on check timing, but should be >= 4
        assert len(rotated_numeric) >= 4, (
            f"Expected at least 4 rotated files with keep=None, got {len(rotated_numeric)}: {rotated_numeric}"
        )
    
    def test_rotation_count_property(self, tmp_path: Path):
        """rotation_count should track number of rotations."""
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=3,
            rotate_keep=1,  # Keep only 1
        )
        
        assert writer.rotation_count == 0
        
        # Write 9 events = 3 full rotations of 3 lines each
        self._write_events(writer, 9)
        
        # Should have rotated 2 times (after 3 and 6 events, not after 9 since that's current file)
        # Actually: 3, 6 = 2 rotations, plus maybe 9 if check happens...
        # With rotate_max_lines=3 and writing 9 events:
        # After 3 events: rotate (now at .1, count=1)
        # After 6 events: rotate (now at .2, count=2)
        # After 9 events: might rotate depending on implementation
        # Actually with my impl, we rotate AFTER reaching limit, so:
        # Events 1-3: write 3 events, check, rotate -> .1
        # Events 4-6: write 3 events, check, rotate -> .2
        # Events 7-9: write 3 events, still in buffer
        assert writer.rotation_count >= 2
        
        writer.close()
    
    def test_does_not_delete_active_file(self, tmp_path: Path):
        """Even with keep=0, the active metrics.ndjson should not be deleted."""
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=5,
            rotate_keep=0,
        )
        
        self._write_events(writer, 20)  # Trigger multiple rotations
        writer.close()
        
        # Active file must exist
        active = tmp_path / "metrics.ndjson"
        assert active.exists(), "Active file should never be deleted"
    
    def test_does_not_delete_non_metrics_files(self, tmp_path: Path):
        """Cleanup should not touch files that don't match metrics.ndjson.* pattern."""
        # Create some unrelated files
        (tmp_path / "other.log").write_text("unrelated")
        (tmp_path / "metrics.ndjson.backup").write_text("backup")  # Non-numeric suffix
        
        writer = MetricsWriter(
            run_dir=tmp_path,
            rotate_max_lines=2,
            rotate_keep=0,  # Delete all rotated
        )
        
        self._write_events(writer, 10)
        writer.close()
        
        # Unrelated files should still exist
        assert (tmp_path / "other.log").exists()
        assert (tmp_path / "metrics.ndjson.backup").exists()  # Non-numeric suffix preserved
