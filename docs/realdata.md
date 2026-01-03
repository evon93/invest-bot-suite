# RealData Usage Guide

> **Phase**: 2F  
> **Status**: Implemented  
> **Last Updated**: 2026-01-03

This guide covers using real OHLCV data with invest-bot-suite tools.

---

## Quickstart

### 1. Set Environment Variable

**PowerShell (Windows)**

```powershell
$env:INVESTBOT_REALDATA_PATH = "data\btc_daily.csv"
```

**Bash (Linux/Mac)**

```bash
export INVESTBOT_REALDATA_PATH="data/btc_daily.csv"
```

### 2. Run Smoke Test

```bash
# Explicit path
python tools/run_realdata_smoke_2F.py --path data/btc_daily.csv --outdir report/smoke_out

# Using env var
python tools/run_realdata_smoke_2F.py --outdir report/smoke_out --max-rows 2000
```

### 3. Run Tests

```bash
# Run only realdata tests (skip if env var not set)
python -m pytest -q -m realdata

# Run all tests (realdata skipped if env var not set)
python -m pytest -q
```

---

## OHLCV Loader

The loader (`tools/load_ohlcv.py`) handles CSV and Parquet files:

```python
from tools.load_ohlcv import load_ohlcv

# Basic usage (returns DataFrame)
df = load_ohlcv("data/btc_daily.csv")

# With stats
df, stats = load_ohlcv("data/btc_daily.csv", return_stats=True)
```

### Features

- **Column normalization**: Accepts various aliases (timestamp→date, o→open, vol→volume)
- **Epoch parsing**: Auto-detects Unix timestamps (seconds/milliseconds)
- **NaN handling**: Drops NaT dates (H1.1), drops OHLC NaN (H1.2), fills volume NaN with 0 (H1.3)
- **Date validation**: Rejects dates outside 1990-2100 range

### CLI

```bash
python tools/load_ohlcv.py --path data/btc_daily.csv --encoding utf-8
```

---

## Robustness Runner with RealData

### Config Schema

Add these keys to `configs/robustness_2D.yaml`:

```yaml
# Optional: synthetic (default) or realdata
data_source: realdata

# Required when data_source=realdata
realdata:
  path: "data/btc_daily.csv"  # Relative to repo root, or absolute

# Date slicing (applies to realdata)
baseline:
  dataset:
    start_date: "2022-01-01"
    end_date: "2024-12-31"
```

### Path Resolution Order

1. `realdata.path` in config (explicit)
2. `INVESTBOT_REALDATA_PATH` env var (fallback)
3. Error if neither available

### run_meta.json Output

When using realdata, extra fields are added:

```json
{
  "data_source": "realdata",
  "realdata_path": "/absolute/path/to/file.csv",
  "n_rows": 730,
  "start_date": "2022-01-01 00:00:00",
  "end_date": "2024-12-31 00:00:00"
}
```

---

## Smoke Test Runner

`tools/run_realdata_smoke_2F.py` performs a minimal buy-and-hold validation:

```bash
python tools/run_realdata_smoke_2F.py \
  --path data/btc_daily.csv \
  --outdir report/smoke_out \
  --max-rows 2000
```

### Output Files

| File | Contents |
|------|----------|
| `results.json` | Metrics: total_return, cagr, max_drawdown, sharpe |
| `run_meta.json` | Metadata with data_source="realdata" |

---

## Data Sources (Recommended)

Based on external research (GR-2F-1-1, G3-2F-1-1):

| Source | License | Granularity | Notes |
|--------|---------|-------------|-------|
| **CryptoDataDownload** | CC BY-NC-SA 4.0 | 1min/hourly/daily | Binance, Coinbase |
| **Kaggle (mczielinski)** | CC0 | 1min | BTC 2011-2021 |
| **Binance Public Data** | Open | Varies | [data.binance.vision](https://data.binance.vision/) |
| **CoinGecko** | ToS | Daily | API limits apply |

### Reproducibility Checklist

When using external data:

1. **Document source URL** and download date
2. **Record file hash**: `Get-FileHash data.csv -Algorithm SHA256` (PowerShell)
3. **Note license** for audit trail
4. **Store in `data/`** folder (gitignored by default)

---

## Example Config

Create `configs/robustness_2D_realdata.yaml`:

```yaml
meta:
  schema_version: "1.0.0"
  description: "Robustness test with real BTC data"

data_source: realdata
realdata:
  path: "data/btc_binance_daily_2022_2024.csv"

baseline:
  risk_rules_path: "risk_rules.yaml"
  candidate_params_path: "configs/best_params_2C.json"
  dataset:
    source: "binance"
    symbols: ["BTCUSDT"]
    start_date: "2022-01-01"
    end_date: "2024-12-31"
    frequency: "1d"

# ... rest of config unchanged
```

---

## Artifacts Reference

| Task ID | Description |
|---------|-------------|
| AG-2F-1-1 | OHLCV loader implementation |
| AG-2F-1-H | Hardening (NaN policy, epoch parsing) |
| AG-2F-1-HF | API fix (return_stats optional) |
| AG-2F-2-1 | Smoke test runner |
| AG-2F-3-1 | Robustness runner wiring |
