"""
tests/test_validate_risk_config_H43.py

Tests dirigidos para tools/validate_risk_config.py y config_schema.py.
Añade cobertura para:
- build_report() function
- main() con diferentes escenarios
- Validación de YAML inválido

Part of ticket AG-H4-3-1.
"""

import pytest
from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_schema import (
    RiskConfigError,
    load_raw_risk_config,
    validate_risk_config_data,
    load_and_validate,
)
from tools.validate_risk_config import build_report, main


class TestBuildReport:
    """Tests for build_report function."""

    def test_build_report_no_errors_no_warnings(self, tmp_path: Path):
        """Report with no issues should show zeros."""
        config_path = tmp_path / "test.yaml"
        report = build_report(config_path, errors=[], warnings=[])
        
        assert "Risk config validation report" in report
        assert "Errors: 0" in report
        assert "Warnings: 0" in report
        assert str(config_path) in report

    def test_build_report_with_errors(self, tmp_path: Path):
        """Report should list errors."""
        config_path = tmp_path / "test.yaml"
        errors = ["Error 1: invalid field", "Error 2: missing section"]
        report = build_report(config_path, errors=errors, warnings=[])
        
        assert "Errors: 2" in report
        assert "Error 1: invalid field" in report
        assert "Error 2: missing section" in report

    def test_build_report_with_warnings(self, tmp_path: Path):
        """Report should list warnings."""
        config_path = tmp_path / "test.yaml"
        warnings = ["Warning: recommended section missing"]
        report = build_report(config_path, errors=[], warnings=warnings)
        
        assert "Warnings: 1" in report
        assert "Warning: recommended section missing" in report


class TestLoadRawRiskConfig:
    """Tests for load_raw_risk_config edge cases."""

    def test_file_not_found_raises_error(self, tmp_path: Path):
        """Missing file should raise RiskConfigError."""
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(RiskConfigError) as exc_info:
            load_raw_risk_config(missing)
        assert "not found" in str(exc_info.value)

    def test_invalid_yaml_raises_error(self, tmp_path: Path):
        """Malformed YAML should raise RiskConfigError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [unclosed bracket", encoding="utf-8")
        
        with pytest.raises(RiskConfigError) as exc_info:
            load_raw_risk_config(bad_yaml)
        assert "YAML parse error" in str(exc_info.value)

    def test_non_dict_root_raises_error(self, tmp_path: Path):
        """YAML with list root should raise RiskConfigError."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n", encoding="utf-8")
        
        with pytest.raises(RiskConfigError) as exc_info:
            load_raw_risk_config(list_yaml)
        assert "must be a mapping/dict" in str(exc_info.value)

    def test_empty_yaml_returns_empty_dict(self, tmp_path: Path):
        """Empty YAML should return empty dict."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("", encoding="utf-8")
        
        result = load_raw_risk_config(empty)
        assert result == {}


class TestValidateRiskConfigData:
    """Tests for validate_risk_config_data function."""

    def test_non_dict_input_returns_error(self):
        """Non-dict input should return error."""
        errors, warnings = validate_risk_config_data("not a dict")
        assert len(errors) == 1
        assert "must be a dict" in errors[0]

    def test_non_string_keys_returns_error(self):
        """Non-string top-level keys should return error."""
        data = {123: "value", "valid_key": "value"}
        errors, warnings = validate_risk_config_data(data)
        assert any("must be strings" in e for e in errors)

    def test_missing_recommended_sections_warns(self):
        """Missing recommended sections should generate warnings."""
        data = {"some_section": {}}
        errors, warnings = validate_risk_config_data(data)
        
        assert len(errors) == 0
        assert len(warnings) > 0
        assert any("risk_limits" in w for w in warnings)

    def test_invalid_max_drawdown_pct_returns_error(self):
        """Non-positive max_drawdown_pct should error."""
        data = {"dd_limits": {"max_drawdown_pct": -5}}
        errors, warnings = validate_risk_config_data(data)
        
        assert any("max_drawdown_pct" in e and "positive" in e for e in errors)

    def test_invalid_atr_multiple_returns_error(self):
        """Non-positive atr_multiple should error."""
        data = {"atr_stop": {"atr_multiple": 0}}
        errors, warnings = validate_risk_config_data(data)
        
        assert any("atr_multiple" in e and "positive" in e for e in errors)

    def test_invalid_risk_manager_mode_returns_error(self):
        """Invalid risk_manager mode should error."""
        data = {"risk_manager": {"mode": "invalid_mode"}}
        errors, warnings = validate_risk_config_data(data)
        
        assert any("mode" in e for e in errors)

    def test_valid_config_no_errors(self):
        """Valid minimal config should have no errors."""
        data = {
            "risk_limits": {"max_position_pct": 10},
            "position_limits": {},
            "dd_limits": {"max_drawdown_pct": 20},
            "atr_stop": {"atr_multiple": 2.5},
            "kelly": {},
            "position_sizing": {},
        }
        errors, warnings = validate_risk_config_data(data)
        assert len(errors) == 0


class TestMainFunction:
    """Tests for main() CLI entry point."""

    def test_main_valid_config(self, tmp_path: Path):
        """main() returns 0 for valid config."""
        config = tmp_path / "valid.yaml"
        config.write_text("risk_limits:\n  max_pos: 10\n", encoding="utf-8")
        output = tmp_path / "report.txt"
        
        result = main(["-c", str(config), "-o", str(output)])
        
        assert result == 0
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "Errors: 0" in content

    def test_main_invalid_config(self, tmp_path: Path):
        """main() returns 1 for invalid config."""
        config = tmp_path / "invalid.yaml"
        # Non-dict root via content that parses to list
        config.write_text("- item1\n- item2\n", encoding="utf-8")
        output = tmp_path / "report.txt"
        
        result = main(["-c", str(config), "-o", str(output)])
        
        assert result == 1
        assert output.exists()

    def test_main_missing_config(self, tmp_path: Path):
        """main() returns 1 for missing config file."""
        output = tmp_path / "report.txt"
        
        result = main(["-c", str(tmp_path / "missing.yaml"), "-o", str(output)])
        
        assert result == 1
