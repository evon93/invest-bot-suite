"""
test_render_risk_rules_prod_2H2.py

Tests for tools/render_risk_rules_prod.py
"""
import pytest
import yaml
import json
import subprocess
import sys
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parent.parent / "tools" / "render_risk_rules_prod.py"
REPO_ROOT = Path(__file__).resolve().parent.parent

class TestRenderRiskRules:

    def test_overrides_simple(self, tmp_path):
        """Test leaf unique key override."""
        base = tmp_path / "base.yaml"
        overlay = tmp_path / "overlay.json"
        out = tmp_path / "out.yaml"

        base_data = {
            "section": {
                "param_a": 10,
                "param_b": 20
            }
        }
        base.write_text(yaml.dump(base_data), encoding="utf-8")

        overlay_data = {
            "selected": {
                "params": {
                    "param_a": 999
                }
            }
        }
        overlay.write_text(json.dumps(overlay_data), encoding="utf-8")

        subprocess.run([sys.executable, str(TOOL_PATH),
                        "--base", str(base),
                        "--overlay", str(overlay),
                        "--out", str(out)], check=True, cwd=str(REPO_ROOT))

        result = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert result["section"]["param_a"] == 999
        assert result["section"]["param_b"] == 20

    def test_overrides_dotted_and_underscore(self, tmp_path):
        """Test dotted path and double underscore logic."""
        base = tmp_path / "base.yaml"
        overlay = tmp_path / "overlay.json"
        out = tmp_path / "out.yaml"

        base_data = {
            "outer": {
                "inner": {
                    "val": 1
                }
            },
            "other": {
                "val": 2
            }
        }
        base.write_text(yaml.dump(base_data), encoding="utf-8")

        overlay_data = {
            "selected": {
                "params": {
                    "outer.inner.val": 100,
                    "other__val": 200
                }
            }
        }
        overlay.write_text(json.dumps(overlay_data), encoding="utf-8")

        subprocess.run([sys.executable, str(TOOL_PATH),
                        "--base", str(base),
                        "--overlay", str(overlay),
                        "--out", str(out)], check=True, cwd=str(REPO_ROOT))

        result = yaml.safe_load(out.read_text(encoding="utf-8"))
        assert result["outer"]["inner"]["val"] == 100
        assert result["other"]["val"] == 200

    def test_unknown_key_fails(self, tmp_path):
        """Test strict validation for unknown keys."""
        base = tmp_path / "base.yaml"
        overlay = tmp_path / "overlay.json"

        base.write_text(yaml.dump({"a": 1}), encoding="utf-8")
        overlay.write_text(json.dumps({"selected": {"params": {"z": 1}}}), encoding="utf-8")

        proc = subprocess.run([sys.executable, str(TOOL_PATH),
                               "--base", str(base),
                               "--overlay", str(overlay),
                               "--out", str(tmp_path/"out.yaml")], 
                               cwd=str(REPO_ROOT), capture_output=True, text=True)
        assert proc.returncode != 0
        assert "Unknown parameter key" in proc.stderr

    def test_ambiguous_key_fails(self, tmp_path):
        """Test strict validation for ambiguous keys."""
        base = tmp_path / "base.yaml"
        overlay = tmp_path / "overlay.json"

        base_data = {
            "s1": {"common": 1},
            "s2": {"common": 2}
        }
        base.write_text(yaml.dump(base_data), encoding="utf-8")
        overlay.write_text(json.dumps({"selected": {"params": {"common": 99}}}), encoding="utf-8")

        proc = subprocess.run([sys.executable, str(TOOL_PATH),
                               "--base", str(base),
                               "--overlay", str(overlay),
                               "--out", str(tmp_path/"out.yaml")], 
                               cwd=str(REPO_ROOT), capture_output=True, text=True)
        assert proc.returncode != 0
        assert "Ambiguous parameter key" in proc.stderr

    def test_validation_gate(self, tmp_path):
        """
        Verify generated config passes validate_risk_config.py
        Uses a subset of real risk_rules structure to check validity.
        """
        base = tmp_path / "risk_rules.yaml"
        overlay = tmp_path / "best_params.json"
        prod = tmp_path / "risk_rules_prod.yaml"

        # Minimal valid config based on config_schema requirements
        min_config = {
            "max_drawdown": {
                "hard_limit_pct": 0.1
            },
            "risk_limits": {},  # Recommended
            "atr_stop": {"atr_multiple": 2.0}, # Check positive number validation
            "risk_manager": {"mode": "active"} 
        }
        base.write_text(yaml.dump(min_config), encoding="utf-8")

        overlay.write_text(json.dumps({
            "selected": {
                "params": {
                    "atr_stop.atr_multiple": 3.0
                }
            }
        }), encoding="utf-8")

        # 1. Render
        subprocess.run([sys.executable, str(TOOL_PATH),
                        "--base", str(base),
                        "--overlay", str(overlay),
                        "--out", str(prod)], check=True, cwd=str(REPO_ROOT))

        # 2. Validate
        validator = REPO_ROOT / "tools" / "validate_risk_config.py"
        proc = subprocess.run([sys.executable, str(validator),
                               "--config", str(prod),
                               "--output", str(tmp_path/"report.txt")],
                               cwd=str(REPO_ROOT), capture_output=True, text=True)
        
        assert proc.returncode == 0
        assert "Errors: 0" in proc.stdout
