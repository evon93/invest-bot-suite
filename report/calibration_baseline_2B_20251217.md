# 2B — Calibration Baseline Freeze

- Fecha: 2025-12-17T20:10:43+01:00
- Rama: `feature/2B_risk_calibration`
- HEAD: `7fcb9c4 2A: RiskContext v0.6, monitor mode, structured risk logging`
- Python: `Python 3.12.3`
- VENV: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite/.venv`

## Inputs congelados

### Risk config
- Archivo: `risk_rules.yaml`
- SHA256: `749a12a4b588f1a3ed426758d6678698bf090b7b116f586ec317fd7c6a7b8ecd`

### Backtest runner
- Archivo: `backtest_initial.py`
- SHA256: `4d3e955aad8b7564274a4c9a060223aeb6828099fc60fd8c7432f5c5c0669574`
- Seed detectada en código: `42`

### Dataset / Generación de precios (según runner)
```python
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
```

## Comando baseline (reproducible)
```bash
python backtest_initial.py 2>&1 | tee report/backtest_initial_run_2B_baseline_20251217.txt
```

## Output baseline (capturado)
```text
{'cagr': np.float64(0.15790395006451363), 'total_return': np.float64(0.15790395006451363), 'max_drawdown': np.float64(-0.09847045115855935), 'sharpe_ratio': np.float64(1.30109905514287), 'volatility': np.float64(0.11853472060855608)}
```
