from __future__ import annotations
import logging
from typing import Dict, Tuple, Union, Any
from pathlib import Path
import yaml

class RiskManager:
    """Gestor de riesgo mejorado; compatible con los tests y con lógica avanzada."""

    # --------------------------------------------------------------------- #
    #  Inicialización                                                        #
    # --------------------------------------------------------------------- #
    def __init__(self, rules: Union[Dict, str, Path]):
        if isinstance(rules, (str, Path)):
            with open(rules, "r", encoding="utf-8") as f:
                self.rules = yaml.safe_load(f)
        else:
            self.rules = rules

        # Defaults robustos
        self.pos_limits = self.rules.get(
            "position_limits",
            {
                "max_single_asset_pct": 0.10,
                "max_crypto_pct": 0.30,
                "max_altcoin_pct": 0.05,
            },
        )

        self.kelly_rules = self.rules.get(
            "kelly",
            {
                "cap_factor": 0.5,
                "crypto_overrides": {"high_vol": 0.3, "med_vol": 0.4, "low_vol": 0.5},
                "percentile_thresholds": {"low": 0.5, "high": 0.8},
            },
        )

        self.major_cryptos = set(self.rules.get("major_cryptos", []))
        self.liquidity_filter = self.rules.get(
            "liquidity_filter", {"min_volume_usd": 10_000_000}
        )

        # Logger sencillo
        self.logger = logging.getLogger("RiskManager")
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.INFO)
        self.logger.info("RiskManager initialized with %d rules", len(self.rules))

    # --------------------------------------------------------------------- #
    #  Kelly / tamaño de posición                                           #
    # --------------------------------------------------------------------- #
    def cap_position_size(self, asset: str, nav_eur: float, vol_pct: float) -> float:
        """Calcula el tamaño máximo en EUR aplicando Kelly dinámico y overrides."""
        base_fraction = self.kelly_rules.get("cap_factor", 0.5)

        crypto_over = self.kelly_rules.get("crypto_overrides", {})
        thresholds = self.kelly_rules.get("percentile_thresholds", {})
        th_high = thresholds.get("high", 0.8)
        th_low = thresholds.get("low", 0.5)

        if asset in self.major_cryptos:
            if vol_pct >= th_high:
                base_fraction = crypto_over.get("high_vol", base_fraction)
            elif vol_pct >= th_low:
                base_fraction = crypto_over.get("med_vol", base_fraction)
            else:
                base_fraction = crypto_over.get("low_vol", base_fraction)

        return nav_eur * base_fraction

    def max_position_size(self, nav_eur: float) -> float:
        """Tamaño máximo absoluto (EUR) permitido por reglas generales."""
        pct = self.pos_limits.get("max_single_asset_pct", 0.10)
        return nav_eur * pct

    # --------------------------------------------------------------------- #
    #  Límites de posición                                                  #
    # --------------------------------------------------------------------- #
    def within_position_limits(self, alloc: Dict[str, float]) -> bool:
        """Comprueba que un allocation dict respeta límites single/sector/altcoin."""
        max_single = self.pos_limits.get("max_single_asset_pct", 0.10)
        if any(w > max_single for w in alloc.values()):
            self.logger.warning("Asset limit exceeded")
            return False

        crypto_assets = [a for a in alloc if a.startswith("CRYPTO")]
        if crypto_assets:
            crypto_total = sum(alloc[a] for a in crypto_assets)
            if crypto_total > self.pos_limits.get("max_crypto_pct", 0.30):
                self.logger.warning("Crypto sector limit exceeded")
                return False

            altcoins = [a for a in crypto_assets if a not in self.major_cryptos]
            if altcoins:
                altcoin_total = sum(alloc[a] for a in altcoins)
                if altcoin_total > self.pos_limits.get("max_altcoin_pct", 0.05):
                    self.logger.warning("Altcoin limit exceeded")
                    return False
        return True

    # --------------------------------------------------------------------- #
    #  Filtro principal de señales                                          #
    # --------------------------------------------------------------------- #
    def filter_signal(
        self, signal: dict, current_weights: dict, nav_eur: float | None = None, **kwargs
    ) -> Tuple[bool, dict]:
        """Filtra señales; devuelve (allow, annotated_signal) – compatible con tests."""
        allow = True
        reasons: list[str] = []
        annotated = signal.copy()

        # 1) Límites de posición
        if not self.within_position_limits(current_weights):
            allow = False
            reasons.append("position_limits")

        # 2) (Stub) Liquidez
        for asset in signal.get("assets", []):
            if not self._check_liquidity(asset):
                allow = False
                reasons.append(f"liquidity:{asset}")

        # 3) Kelly sizing (sólo si nav_eur está disponible)
        if nav_eur:
            for asset, target_weight in signal.get("deltas", {}).items():
                vol_pct = self._get_volatility(asset)
                max_eur = self.cap_position_size(asset, nav_eur, vol_pct)
                max_weight = max_eur / nav_eur
                if target_weight > max_weight:
                    allow = False
                    reasons.append(f"kelly_cap:{asset}")
                    annotated["deltas"][asset] = max_weight

        annotated["risk_allow"] = allow
        annotated["risk_reasons"] = reasons
        return allow, annotated

    # --------------------------------------------------------------------- #
    #  Helpers (stubs)                                                      #
    # --------------------------------------------------------------------- #
    def _get_volatility(self, asset: str) -> float:
        """Stub: devuelve volatilidad histórica (para tests)."""
        return 0.65  # reemplazar con cálculo real

    def _check_liquidity(self, asset: str) -> bool:
        """Stub: chequea liquidez mínima (para tests)."""
        return True
