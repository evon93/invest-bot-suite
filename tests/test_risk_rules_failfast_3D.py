"""
tests/test_risk_rules_failfast_3D.py

Tests for risk rules fail-fast validation (AG-3D-1-1).

Validates:
- Missing critical keys → ValueError
- Wrong type for critical keys → ValueError
- Valid minimal config → no error
- File not found → ValueError
- Empty YAML → ValueError
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from risk_rules_loader import load_risk_rules, validate_risk_rules_critical, CRITICAL_KEYS


class TestLoadRiskRules:
    """Tests for load_risk_rules function."""

    def test_file_not_found_raises_valueerror(self, tmp_path: Path):
        """Path inexistente → ValueError trazable."""
        nonexistent = tmp_path / "does_not_exist.yaml"
        
        with pytest.raises(ValueError) as exc_info:
            load_risk_rules(nonexistent)
        
        assert "not found" in str(exc_info.value).lower()
        assert str(nonexistent) in str(exc_info.value)

    def test_empty_yaml_raises_valueerror(self, tmp_path: Path):
        """YAML vacío (solo comentarios) → ValueError."""
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("# This is only a comment\n")
        
        with pytest.raises(ValueError) as exc_info:
            load_risk_rules(empty_yaml)
        
        assert "empty" in str(exc_info.value).lower()

    def test_invalid_yaml_raises_valueerror(self, tmp_path: Path):
        """YAML inválido → ValueError."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [unbalanced bracket")
        
        with pytest.raises(ValueError) as exc_info:
            load_risk_rules(bad_yaml)
        
        assert "invalid yaml" in str(exc_info.value).lower()

    def test_non_dict_yaml_raises_valueerror(self, tmp_path: Path):
        """YAML que no es dict → ValueError."""
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")
        
        with pytest.raises(ValueError) as exc_info:
            load_risk_rules(list_yaml)
        
        assert "dict" in str(exc_info.value).lower()

    def test_valid_yaml_loads(self, tmp_path: Path):
        """YAML válido carga correctamente."""
        valid_yaml = tmp_path / "valid.yaml"
        valid_yaml.write_text("key: value\nnested:\n  a: 1\n")
        
        rules = load_risk_rules(valid_yaml)
        
        assert rules == {"key": "value", "nested": {"a": 1}}


class TestValidateRiskRulesCritical:
    """Tests for validate_risk_rules_critical function."""

    def test_missing_critical_raises_valueerror(self, tmp_path: Path):
        """YAML sin key crítica → ValueError con key(s) en mensaje."""
        # Only include one critical key, missing others
        incomplete_rules = {
            "position_limits": {"max_single_asset_pct": 0.10},
            # Missing: kelly, risk_manager
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_risk_rules_critical(incomplete_rules, path="test.yaml")
        
        error_msg = str(exc_info.value)
        assert "kelly" in error_msg
        assert "risk_manager" in error_msg
        assert "missing" in error_msg.lower()

    def test_wrong_type_raises_valueerror(self, tmp_path: Path):
        """Key crítica con tipo incorrecto → ValueError."""
        wrong_type_rules = {
            "position_limits": {"max_single_asset_pct": 0.10},
            "kelly": "not_a_dict",  # Should be dict
            "risk_manager": {"version": "0.4"},
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_risk_rules_critical(wrong_type_rules)
        
        error_msg = str(exc_info.value)
        assert "kelly" in error_msg
        assert "wrong type" in error_msg.lower()

    def test_minimal_valid_passes(self, tmp_path: Path):
        """YAML mínimo válido (incluye critical con tipos correctos) → no error."""
        valid_rules = {
            "position_limits": {"max_single_asset_pct": 0.10},
            "kelly": {"cap_factor": 0.5},
            "risk_manager": {"version": "0.4", "mode": "active"},
        }
        
        # Should not raise
        validate_risk_rules_critical(valid_rules)

    def test_extra_keys_allowed(self, tmp_path: Path):
        """Keys extra no interfieren con validación."""
        rules_with_extras = {
            "position_limits": {"max_single_asset_pct": 0.10},
            "kelly": {"cap_factor": 0.5},
            "risk_manager": {"version": "0.4"},
            "extra_key": "should be ignored",
            "another": {"nested": "value"},
        }
        
        # Should not raise
        validate_risk_rules_critical(rules_with_extras)

    def test_path_included_in_error_message(self, tmp_path: Path):
        """Path del archivo incluido en mensaje de error."""
        incomplete_rules = {"only_one": "key"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_risk_rules_critical(incomplete_rules, path="/path/to/config.yaml")
        
        assert "/path/to/config.yaml" in str(exc_info.value)


class TestIntegrationLoadAndValidate:
    """Integration tests: load + validate pipeline."""

    def test_full_pipeline_valid_config(self, tmp_path: Path):
        """Config válida pasa load + validate."""
        config_path = tmp_path / "valid_risk_rules.yaml"
        config_path.write_text("""
position_limits:
  max_single_asset_pct: 0.06
  max_crypto_pct: 0.12
kelly:
  cap_factor: 0.7
  min_trade_size_eur: 20
risk_manager:
  version: '0.4'
  mode: active
""")
        
        rules = load_risk_rules(config_path)
        validate_risk_rules_critical(rules, path=config_path)
        
        assert rules["kelly"]["cap_factor"] == 0.7

    def test_full_pipeline_missing_critical(self, tmp_path: Path):
        """Config sin keys críticas falla en validate."""
        config_path = tmp_path / "incomplete.yaml"
        config_path.write_text("""
position_limits:
  max_single_asset_pct: 0.06
# Missing kelly and risk_manager
other_stuff: true
""")
        
        rules = load_risk_rules(config_path)  # This should succeed
        
        with pytest.raises(ValueError) as exc_info:
            validate_risk_rules_critical(rules, path=config_path)
        
        error_msg = str(exc_info.value)
        assert "kelly" in error_msg
        assert "risk_manager" in error_msg
