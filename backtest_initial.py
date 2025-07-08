"""
backtest_initial.py · Sprint-1 · v0.1  (Series-ready)
Backtest con datos sintéticos y gestión de riesgo.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import pandas as pd

# ------------------------------------------------------------------------------
# Configuración
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
np.random.seed(42)

# ------------------------------------------------------------------------------
# Datos sintéticos
# ------------------------------------------------------------------------------
def generate_synthetic_prices(
    start_date: str = "2024-01-01",
    periods: int = 252,
    assets: Dict[str, Dict[str, float]] | None = None,
) -> pd.DataFrame:
    if assets is None:
        assets = {
            "ETF": {"price": 100, "mu": 0.07 / 252, "sigma": 0.15 / np.sqrt(252)},
            "CRYPTO_BTC": {
                "price": 40_000,
                "mu": 0.50 / 252,
                "sigma": 0.80 / np.sqrt(252),
            },
            "CRYPTO_ETH": {
                "price": 3_000,
                "mu": 0.40 / 252,
                "sigma": 0.90 / np.sqrt(252),
            },
            "BONDS": {"price": 95, "mu": 0.03 / 252, "sigma": 0.05 / np.sqrt(252)},
        }

    dates = pd.date_range(start_date, periods=periods, freq="D")
    prices = pd.DataFrame(index=dates)

    for asset, prm in assets.items():
        returns = np.random.normal(prm["mu"], prm["sigma"], periods)
        prices[asset] = prm["price"] * np.exp(np.cumsum(returns))

    return prices

# ------------------------------------------------------------------------------
# Backtester
# ------------------------------------------------------------------------------
class SimpleBacktester:
    """Backtester con rebalanceo mensual; acepta Series o DataFrame."""

    def __init__(
        self, prices: Union[pd.Series, pd.DataFrame], initial_capital: float = 10_000
    ):
        # Normalizar formato
        if isinstance(prices, pd.Series):
            self.prices = prices.to_frame(name=prices.name or "ASSET")
            self.single_asset = True
        else:
            self.prices = prices
            self.single_asset = False

        # Estado
        self.initial_capital = initial_capital
        self.portfolio_value: List[float] = [initial_capital]
        self.positions: Dict[str, float] = {c: 0.0 for c in self.prices.columns}
        self.trades: List[Dict] = []

        # Pesos objetivo
        if self.single_asset:
            self.target_weights = {self.prices.columns[0]: 1.0}
        else:
            self.target_weights = {
                "ETF": 0.60,
                "CRYPTO_BTC": 0.08,
                "CRYPTO_ETH": 0.04,
                "BONDS": 0.28,
            }

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    def _current_weights(self, date) -> Dict[str, float]:
        """Calcula pesos actuales para la fecha dada."""
        values = {
            a: self.positions.get(a, 0) * self.prices.loc[date, a]
            for a in self.prices.columns
        }
        total = sum(values.values())
        return {a: v / total for a, v in values.items()} if total > 0 else {}

    def _rebalance(self, date, risk_manager=None):
        nav = self.portfolio_value[-1]
        current_w = self._current_weights(date)
        deltas = {
            a: self.target_weights.get(a, 0) - current_w.get(a, 0)
            for a in self.prices.columns
        }

        if risk_manager:
            allow, annotated = risk_manager.filter_signal(
                {"deltas": deltas}, current_w, nav
            )
            if not allow:
                logger.warning("Señal rechazada: %s", annotated["risk_reasons"])
                return

        for asset, delta in deltas.items():
            if abs(delta) < 0.01:
                continue
            target_val = self.target_weights.get(asset, 0) * nav
            target_shares = target_val / self.prices.loc[date, asset]
            shares_delta = target_shares - self.positions.get(asset, 0)
            if shares_delta != 0:
                self.positions[asset] = target_shares
                self.trades.append(
                    {
                        "date": date,
                        "asset": asset,
                        "shares": shares_delta,
                        "price": self.prices.loc[date, asset],
                    }
                )

    # ----------------------------------------------------------------------
    # Loop principal
    # ----------------------------------------------------------------------
    def run(self, risk_manager=None) -> pd.DataFrame:
        first_date = self.prices.index[0]
        if first_date.weekday() < 5:            # solo días hábiles
    self._rebalance(first_date, risk_manager)

        records: List[Dict] = []
        for date in self.prices.index:
            pv = sum(
                self.positions.get(a, 0) * self.prices.loc[date, a]
                for a in self.prices.columns
            )
            self.portfolio_value.append(pv)
            records.append({"date": date, "value": pv})

            if date.day == 1 and date != first_date and date.weekday() < 5:
                self._rebalance(date, risk_manager)

        return pd.DataFrame(records)

# ------------------------------------------------------------------------------
# Métricas
# ------------------------------------------------------------------------------
def calculate_metrics(
    df: pd.DataFrame, benchmark_return: float = 0.08
) -> Dict[str, float]:
    returns = df["value"].pct_change().dropna()
    total_return = df["value"].iloc[-1] / df["value"].iloc[0] - 1
    years = len(df) / 252
    cagr = (1 + total_return) ** (1 / years) - 1
    rolling_max = df["value"].cummax()
    drawdown = (df["value"] / rolling_max - 1).min()
    sharpe = returns.mean() / returns.std() * np.sqrt(252)
    return {
        "cagr": cagr,
        "total_return": total_return,
        "max_drawdown": drawdown,
        "sharpe_ratio": sharpe,
        "volatility": returns.std() * np.sqrt(252),
    }

# ------------------------------------------------------------------------------
# CLI rápido
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    prices = generate_synthetic_prices()
    bt = SimpleBacktester(prices)
    result = bt.run()
    print(calculate_metrics(result))
