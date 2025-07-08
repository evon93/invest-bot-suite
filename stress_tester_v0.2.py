
from __future__ import annotations

"""stress_tester_v0.2.py · Sprint‑1
------------------------------------
Amplía escenarios y métricas:

• Volatility Shock ×{1.2,1.5,2.0}
• Tail Events −10 %, −20 %
• DeFi crisis: caída −30 % en activos cap<5 bn
• Sharpe ratio anualizado
• VaR 95 % diario

Salida: DataFrame con return %, max DD, Sharpe, VaR.
"""

from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------


def shock_volatility(series: pd.Series, factor: float) -> pd.Series:
    log_ret = np.log(series / series.shift(1)).dropna()
    shocked = log_ret * factor
    return series.iloc[0] * np.exp(shocked.cumsum()).rename(series.name)


def inject_tail_event(series: pd.Series, pct_drop: float, day_idx: int) -> pd.Series:
    shock_series = series.copy()
    if 0 < day_idx < len(series):
        shock_series.iloc[day_idx:] *= 1 - pct_drop
    return shock_series


def defi_crisis(series: pd.Series) -> pd.Series:
    # 2‑day 30 % drop
    shock_series = series.copy()
    mid = len(series) // 2
    shock_series.iloc[mid:] *= 0.7
    return shock_series


# ---------------------------------------------------------------------------


class StressTester:
    def __init__(self, price_df: pd.DataFrame, mcap: Dict[str, float] | None = None):
        self.price_df = price_df
        self.mcap = mcap or {}

    def run(self) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for sym in self.price_df.columns:
            base = self.price_df[sym]
            # Vol shocks
            for f in (1.2, 1.5, 2.0):
                rows.append(self._metrics(sym, f"vol_x{f}", shock_volatility(base, f)))
            # Tail events
            for pct in (0.10, 0.20):
                rows.append(self._metrics(sym, f"tail_{int(pct*100)}pc", inject_tail_event(base, pct, len(base)//2)))
            # DeFi crisis for small caps (<5bn)
            if self.mcap.get(sym, 1e10) < 5e9:
                rows.append(self._metrics(sym, "defi_crisis", defi_crisis(base)))
        return pd.DataFrame(rows)

    def _metrics(self, symbol: str, label: str, series: pd.Series) -> Dict[str, Any]:
        dd = (series / series.cummax() - 1).min()
        ret = series.iloc[-1] / series.iloc[0] - 1
        daily_ret = np.log(series).diff().dropna()
        sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(252)
        var95 = np.percentile(daily_ret, 5)
        return {
            "symbol": symbol,
            "scenario": label,
            "return_pct": ret,
            "max_drawdown_pct": dd,
            "sharpe": sharpe,
            "var95": var95,
        }

    def to_parquet(self, df: pd.DataFrame, path: Path | str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)


if __name__ == "__main__":  # pragma: no cover
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022‑01‑01", periods=365, freq="D")
    price = pd.Series(np.cumprod(1 + rng.normal(0, 0.01, len(dates))), index=dates, name="SOL")
    tester = StressTester(pd.DataFrame({"SOL": price}), {"SOL": 3e9})
    print(tester.run().head())
