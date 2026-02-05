"""
tests/test_validate_local_h51.py

Unit tests for tools/validate_local.py harness.
Uses mocked subprocess to avoid running actual pytest.

AG-H5-1-1
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_local


class TestValidateLocalHarness:
    """Unit tests for validate_local.py."""

    def test_all_gates_pass_returns_0(self, tmp_path, monkeypatch):
        """When all gates return rc=0, main() returns 0."""
        # Patch REPORT_DIR to tmp_path
        monkeypatch.setattr(validate_local, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(validate_local, "REPO_ROOT", tmp_path)
        
        # Mock subprocess.run to always succeed
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "All tests passed\n"
        mock_result.stderr = ""
        
        def mock_run(cmd, **kwargs):
            # For git commands, return branch/head
            if "rev-parse" in cmd:
                if "--abbrev-ref" in cmd:
                    mock_result.stdout = "main"
                else:
                    mock_result.stdout = "abc123def456"
            else:
                mock_result.stdout = "passed\n"
            return mock_result
        
        with patch.object(validate_local.subprocess, "run", side_effect=mock_run):
            # Simulate args
            monkeypatch.setattr(
                sys, "argv",
                ["validate_local.py", "--preset", "quick", "--out-prefix", "test_run"]
            )
            
            exit_code = validate_local.main()
        
        assert exit_code == 0
        
        # Check artifacts created
        assert (tmp_path / "test_run.txt").exists()
        assert (tmp_path / "test_run_run_meta.json").exists()
        
        # Check run_meta content
        with open(tmp_path / "test_run_run_meta.json") as f:
            meta = json.load(f)
        
        assert meta["overall_status"] == "PASS"
        assert meta["preset"] == "quick"

    def test_one_gate_fail_returns_1(self, tmp_path, monkeypatch):
        """When any gate returns rc!=0, main() returns 1."""
        monkeypatch.setattr(validate_local, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(validate_local, "REPO_ROOT", tmp_path)
        
        call_count = [0]
        
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if "rev-parse" in cmd:
                result.returncode = 0
                result.stdout = "main" if "--abbrev-ref" in cmd else "abc123"
                result.stderr = ""
            else:
                call_count[0] += 1
                # First pytest call fails
                if call_count[0] == 1:
                    result.returncode = 1
                    result.stdout = "FAILED test_something\n"
                else:
                    result.returncode = 0
                    result.stdout = "passed\n"
                result.stderr = ""
            return result
        
        with patch.object(validate_local.subprocess, "run", side_effect=mock_run):
            monkeypatch.setattr(
                sys, "argv",
                ["validate_local.py", "--preset", "quick", "--out-prefix", "test_fail"]
            )
            
            exit_code = validate_local.main()
        
        assert exit_code == 1
        
        with open(tmp_path / "test_fail_run_meta.json") as f:
            meta = json.load(f)
        
        assert meta["overall_status"] == "FAIL"

    def test_run_meta_has_required_fields(self, tmp_path, monkeypatch):
        """run_meta.json contains all required fields."""
        monkeypatch.setattr(validate_local, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(validate_local, "REPO_ROOT", tmp_path)
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        
        with patch.object(validate_local.subprocess, "run", return_value=mock_result):
            monkeypatch.setattr(
                sys, "argv",
                ["validate_local.py", "--preset", "quick", "--out-prefix", "test_meta"]
            )
            
            validate_local.main()
        
        with open(tmp_path / "test_meta_run_meta.json") as f:
            meta = json.load(f)
        
        required_fields = {
            "iso_time", "branch", "head", "python", "platform",
            "preset", "cov_fail_under", "gates", "overall_status", "elapsed_total_s"
        }
        
        assert required_fields.issubset(set(meta.keys()))
        assert isinstance(meta["gates"], list)
        assert len(meta["gates"]) >= 1
        
        # Check gate structure
        gate = meta["gates"][0]
        gate_fields = {"name", "cmd", "rc", "elapsed_s", "status", "log_path"}
        assert gate_fields.issubset(set(gate.keys()))

    def test_cov_fail_under_override(self, tmp_path, monkeypatch):
        """--cov-fail-under overrides preset default."""
        monkeypatch.setattr(validate_local, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(validate_local, "REPO_ROOT", tmp_path)
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        
        with patch.object(validate_local.subprocess, "run", return_value=mock_result):
            monkeypatch.setattr(
                sys, "argv",
                ["validate_local.py", "--preset", "quick", "--cov-fail-under", "85", "--out-prefix", "test_cov"]
            )
            
            validate_local.main()
        
        with open(tmp_path / "test_cov_run_meta.json") as f:
            meta = json.load(f)
        
        assert meta["cov_fail_under"] == 85

    def test_preset_ci_has_three_gates(self, tmp_path, monkeypatch):
        """Preset 'ci' includes all 3 gates."""
        monkeypatch.setattr(validate_local, "REPORT_DIR", tmp_path)
        monkeypatch.setattr(validate_local, "REPO_ROOT", tmp_path)
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ok"
        mock_result.stderr = ""
        
        with patch.object(validate_local.subprocess, "run", return_value=mock_result):
            monkeypatch.setattr(
                sys, "argv",
                ["validate_local.py", "--preset", "ci", "--out-prefix", "test_ci"]
            )
            
            validate_local.main()
        
        with open(tmp_path / "test_ci_run_meta.json") as f:
            meta = json.load(f)
        
        assert len(meta["gates"]) == 3
        gate_names = [g["name"] for g in meta["gates"]]
        assert "pytest_full" in gate_names
        assert "coverage_gate" in gate_names
        assert "offline_integration" in gate_names
