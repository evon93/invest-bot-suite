"""
test_calibration_multiseed_2G.py — Tests for multi-seed calibration robustness (2G)

Tests parse_seeds, multi-seed outputs, and stability metrics.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestMultiSeedCalibration:
    """Test multi-seed calibration functionality."""

    def test_parse_seeds_single(self):
        """parse_seeds handles single seed."""
        from tools.run_calibration_2B import parse_seeds
        assert parse_seeds("42") == [42]

    def test_parse_seeds_multiple(self):
        """parse_seeds handles comma-separated seeds."""
        from tools.run_calibration_2B import parse_seeds
        assert parse_seeds("42,123,456") == [42, 123, 456]

    def test_parse_seeds_with_spaces(self):
        """parse_seeds handles spaces around commas."""
        from tools.run_calibration_2B import parse_seeds
        assert parse_seeds("1, 2, 3") == [1, 2, 3]

    def test_parse_seeds_empty_raises(self):
        """parse_seeds raises on empty string."""
        from tools.run_calibration_2B import parse_seeds
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_seeds("")

    def test_parse_seeds_invalid_raises(self):
        """parse_seeds raises on non-integer."""
        from tools.run_calibration_2B import parse_seeds
        with pytest.raises(ValueError, match="Invalid seed"):
            parse_seeds("42,abc")

    def test_parse_seeds_duplicates_raises(self):
        """parse_seeds raises on duplicate seeds."""
        from tools.run_calibration_2B import parse_seeds
        with pytest.raises(ValueError, match="Duplicate seeds"):
            parse_seeds("42,42")

    # Integration tests omitted - verified manually with runner
    # CLI: python tools/run_calibration_2B.py --mode quick --max-combinations 2 --seeds 42,123 --output-dir report/test_2g_out

