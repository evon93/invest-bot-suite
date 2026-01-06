"""
engine/runtime_config.py

Runtime configuration with fail-fast validation for live/exchange modes.
Prevents accidental execution with real exchange without proper credentials.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, List


# Exchanges that require API credentials
EXCHANGES_REQUIRING_SECRETS = frozenset({
    "ccxt_sandbox",
    "ccxt_live",
    "binance",
    "kraken",
    "coinbase",
})


@dataclass
class RuntimeConfig:
    """Runtime configuration loaded from environment variables."""
    
    mode_clock: str = "simulated"
    exchange_kind: str = "paper"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    dry_run: bool = True
    
    @staticmethod
    def from_env(prefix: str = "INVESTBOT_") -> RuntimeConfig:
        """
        Load configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix (default: INVESTBOT_)
            
        Returns:
            RuntimeConfig instance with values from environment
            
        Notes:
            - Empty strings or whitespace-only values are treated as missing
            - Enum-like values (mode_clock, exchange_kind) are normalized to lowercase
        """
        def get_env(key: str) -> Optional[str]:
            """Get env var, treating empty/whitespace as None."""
            val = os.environ.get(f"{prefix}{key}")
            if val is None:
                return None
            val = val.strip()
            return val if val else None
        
        def get_env_bool(key: str, default: bool = True) -> bool:
            """Get boolean env var (1/true/yes = True, 0/false/no = False)."""
            val = get_env(key)
            if val is None:
                return default
            return val.lower() in ("1", "true", "yes", "on")
        
        # Read values
        mode_clock = get_env("MODE_CLOCK")
        exchange_kind = get_env("EXCHANGE_KIND")
        api_key = get_env("API_KEY")
        api_secret = get_env("API_SECRET")
        base_url = get_env("BASE_URL")
        dry_run = get_env_bool("DRY_RUN", default=True)
        
        return RuntimeConfig(
            mode_clock=(mode_clock.lower() if mode_clock else "simulated"),
            exchange_kind=(exchange_kind.lower() if exchange_kind else "paper"),
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url,
            dry_run=dry_run,
        )
    
    def validate_for(self, mode_clock: str, exchange_kind: str) -> None:
        """
        Validate configuration for the given mode and exchange.
        
        Args:
            mode_clock: Clock mode from CLI (simulated/real)
            exchange_kind: Exchange kind from CLI (paper/stub/ccxt_sandbox/...)
            
        Raises:
            SystemExit(2): If required secrets are missing for non-paper modes
            
        Notes:
            - paper and stub exchanges never require secrets
            - real clock mode requires secrets unless exchange is paper/stub
            - Error messages never include secret values, only key names
        """
        mode_clock = mode_clock.lower().strip()
        exchange_kind = exchange_kind.lower().strip()
        
        # Paper and stub exchanges don't require secrets
        if exchange_kind in ("paper", "stub"):
            return
        
        # For non-paper exchanges, check if secrets are required
        requires_secrets = (
            mode_clock == "real" or 
            exchange_kind in EXCHANGES_REQUIRING_SECRETS or
            exchange_kind not in ("paper", "stub")  # Any unknown exchange requires secrets
        )
        
        if not requires_secrets:
            return
        
        # Check required secrets
        missing: List[str] = []
        
        if not self.api_key:
            missing.append("INVESTBOT_API_KEY")
        if not self.api_secret:
            missing.append("INVESTBOT_API_SECRET")
        
        # Some exchanges also require base_url
        if exchange_kind in ("ccxt_sandbox", "ccxt_live") and not self.base_url:
            missing.append("INVESTBOT_BASE_URL")
        
        if missing:
            # SECURITY: Never include actual secret values in error message
            msg = (
                f"Missing required env vars for mode_clock={mode_clock}, "
                f"exchange_kind={exchange_kind}: {', '.join(missing)}"
            )
            raise SystemExit(msg)
