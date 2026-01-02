# 2F.1 External AI Findings Summary

> **Date**: 2026-01-02  
> **Sources**: DeepSeek, Gemini, Grok  
> **Target**: `tools/load_ohlcv.py`

---

## Convergence Matrix (DS ∩ G3)

| Finding | DeepSeek | Gemini | Priority |
|---------|----------|--------|----------|
| NaT/NaN policy | "Filter NaT dates" (P1) | "Strict Drop NaNs" (A) | **P1** |
| Unix epoch parsing | "Timestamps numéricos" (P3) | "unit='s'/'ms' inference" (B) | **P1** |
| Encoding param | "Add encoding param" (P1) | Not mentioned | P1 |
| TZ stripping warning | "Log warning" (P2) | "Confirm wall-time" (3.4) | P2 |
| Volume fillna | Not mentioned | "fillna(0)" (C) | P2 |
| Empty/header-only | Not mentioned | "Correct behavior" | OK |

---

## Research Deltas (Grok vs Gemini)

| Source | Grok Findings | Gemini Findings |
|--------|---------------|-----------------|
| **Binance Vision** | Best for BTC/ETH daily | Recommended for spot data |
| **CryptoDataDownload** | Meta-row risk (first row) | Not mentioned |
| **Kaggle** | Inconsistent columns | Similar warning |
| **CoinGecko API** | Rate limits, no OHLCV | API caveat noted |

---

## Next Hardening Candidates (2G)

| ID | Enhancement | Impact | Effort |
|----|-------------|--------|--------|
| H1 | **NaT filter** after `_parse_date` | Critical | Low |
| H2 | **Epoch unit inference** (s/ms detection) | High | Medium |
| H3 | **Encoding param** with fallback | Medium | Low |
| H4 | **Empty file dtype preservation** | Low | Low |
| H5 | **TZ stripping logging** | Low | Low |

---

## Audit Verdicts

| Model | Verdict | Condition |
|-------|---------|-----------|
| DeepSeek | **APPROVE** | With P1 improvements |
| Gemini | **APPROVE (Yellow)** | With NaN/epoch hardening for 2G |

---

## Files Created

- `report/DS-2F-1-1_audit.md` — DeepSeek audit
- `report/G3-2F-1-1_audit.md` — Gemini audit
- `report/GR-2F-1-1_research.md` — Grok research (data sources)
- `report/G3-2F-1-1_research.md` — Gemini research (data sources)
