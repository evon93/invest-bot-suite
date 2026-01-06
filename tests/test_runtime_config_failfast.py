"""
tests/test_runtime_config_failfast.py

Tests for engine/runtime_config.py fail-fast validation.
Ensures proper behavior for paper vs non-paper modes and secret protection.
"""

import os
import pytest
import sys
from unittest import mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.runtime_config import RuntimeConfig


class TestRuntimeConfigFromEnv:
    """Tests for RuntimeConfig.from_env() loading."""
    
    def test_defaults_when_env_empty(self):
        """Caso A: env vacío → defaults paper+simulated."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            assert cfg.mode_clock == "simulated"
            assert cfg.exchange_kind == "paper"
            assert cfg.api_key is None
            assert cfg.api_secret is None
            assert cfg.dry_run is True
    
    def test_loads_values_from_env(self):
        """Values from env are properly loaded."""
        env = {
            "INVESTBOT_MODE_CLOCK": "REAL",
            "INVESTBOT_EXCHANGE_KIND": "CCXT_SANDBOX",
            "INVESTBOT_API_KEY": "test_key_123",
            "INVESTBOT_API_SECRET": "test_secret_456",
            "INVESTBOT_BASE_URL": "https://api.example.com",
            "INVESTBOT_DRY_RUN": "0",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = RuntimeConfig.from_env()
            assert cfg.mode_clock == "real"  # normalized to lowercase
            assert cfg.exchange_kind == "ccxt_sandbox"  # normalized
            assert cfg.api_key == "test_key_123"
            assert cfg.api_secret == "test_secret_456"
            assert cfg.base_url == "https://api.example.com"
            assert cfg.dry_run is False
    
    def test_whitespace_treated_as_missing(self):
        """Caso D: valores con espacios tratados como missing."""
        env = {
            "INVESTBOT_API_KEY": "   ",
            "INVESTBOT_API_SECRET": "",
            "INVESTBOT_MODE_CLOCK": "  simulated  ",  # should be stripped
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = RuntimeConfig.from_env()
            assert cfg.api_key is None, "Whitespace-only should be None"
            assert cfg.api_secret is None, "Empty string should be None"
            assert cfg.mode_clock == "simulated", "Should strip and normalize"


class TestRuntimeConfigValidateFor:
    """Tests for validate_for() fail-fast behavior."""
    
    def test_paper_simulated_no_secrets_ok(self):
        """Caso A: paper+simulated no exige secrets → no error."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="paper",
            api_key=None,
            api_secret=None,
        )
        # Should not raise
        cfg.validate_for("simulated", "paper")
    
    def test_stub_simulated_no_secrets_ok(self):
        """stub+simulated no exige secrets → no error."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="stub",
            api_key=None,
            api_secret=None,
        )
        # Should not raise
        cfg.validate_for("simulated", "stub")
    
    def test_real_clock_without_secrets_fails(self):
        """Caso B: MODE_CLOCK=real sin secrets → SystemExit."""
        cfg = RuntimeConfig(
            mode_clock="real",
            exchange_kind="ccxt_sandbox",
            api_key=None,
            api_secret=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            cfg.validate_for("real", "ccxt_sandbox")
        # Check exit code or message
        assert "INVESTBOT_API_KEY" in str(exc_info.value)
        assert "INVESTBOT_API_SECRET" in str(exc_info.value)
    
    def test_ccxt_sandbox_without_secrets_fails(self):
        """Caso C: EXCHANGE_KIND=ccxt_sandbox sin secrets → SystemExit."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="ccxt_sandbox",
            api_key=None,
            api_secret=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            cfg.validate_for("simulated", "ccxt_sandbox")
        assert "INVESTBOT_API_KEY" in str(exc_info.value)
    
    def test_ccxt_sandbox_requires_base_url(self):
        """ccxt_sandbox requires base_url in addition to api credentials."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="ccxt_sandbox",
            api_key="key123",
            api_secret="secret456",
            base_url=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            cfg.validate_for("simulated", "ccxt_sandbox")
        assert "INVESTBOT_BASE_URL" in str(exc_info.value)
    
    def test_ccxt_sandbox_with_all_secrets_ok(self):
        """ccxt_sandbox with all required secrets passes."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="ccxt_sandbox",
            api_key="key123",
            api_secret="secret456",
            base_url="https://api.example.com",
        )
        # Should not raise
        cfg.validate_for("simulated", "ccxt_sandbox")
    
    def test_error_message_does_not_contain_secret_values(self):
        """Caso E: mensaje de error no contiene valores de secrets."""
        secret_key = "SUPER_SECRET_KEY_12345"
        secret_value = "SUPER_SECRET_VALUE_67890"
        
        cfg = RuntimeConfig(
            mode_clock="real",
            exchange_kind="ccxt_sandbox",
            api_key=secret_key,  # Has key but missing secret
            api_secret=None,
            base_url=None,
        )
        
        with pytest.raises(SystemExit) as exc_info:
            cfg.validate_for("real", "ccxt_sandbox")
        
        error_msg = str(exc_info.value)
        # Error should mention missing keys but NOT the actual secret values
        assert secret_key not in error_msg, "Secret key value should not be in error"
        assert "INVESTBOT_API_SECRET" in error_msg, "Should mention missing key name"
    
    def test_unknown_exchange_requires_secrets(self):
        """Unknown exchange (not paper/stub) requires secrets."""
        cfg = RuntimeConfig(
            mode_clock="simulated",
            exchange_kind="some_new_exchange",
            api_key=None,
            api_secret=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            cfg.validate_for("simulated", "some_new_exchange")
        assert "INVESTBOT_API_KEY" in str(exc_info.value)


class TestRuntimeConfigIntegration:
    """Integration tests simulating CLI behavior."""
    
    def test_full_flow_paper_mode(self):
        """Full flow: load from env and validate for paper mode."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            # Should not raise
            cfg.validate_for("simulated", "paper")
            assert cfg.exchange_kind == "paper"
    
    def test_full_flow_real_mode_fails_without_env(self):
        """Full flow: real mode without env vars fails."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            with pytest.raises(SystemExit):
                cfg.validate_for("real", "ccxt_sandbox")
    
    def test_full_flow_real_mode_with_env_works(self):
        """Full flow: real mode with proper env vars works."""
        env = {
            "INVESTBOT_MODE_CLOCK": "real",
            "INVESTBOT_EXCHANGE_KIND": "ccxt_sandbox",
            "INVESTBOT_API_KEY": "key123",
            "INVESTBOT_API_SECRET": "secret456",
            "INVESTBOT_BASE_URL": "https://api.example.com",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = RuntimeConfig.from_env()
            # Should not raise
            cfg.validate_for("real", "ccxt_sandbox")
