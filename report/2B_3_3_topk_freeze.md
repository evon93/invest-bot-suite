# 2B-3.3 TopK Freeze — Consolidated Candidates

## Metadata

| Campo | Full | Strict |
|-------|------|--------|
| Path | `out_2B_3_3_grid_full_20251230_191032` | `out_2B_3_3_grid_strict_20251230_193344` |
| Git HEAD | c299848 | 3d63d26 |
| Config Hash | `6e8214a42d39b659` | `6e8214a42d39b659` |
| Seed | 42 | 42 |

**Score Formula**: `1.0*sharpe + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_dd) - 0.5*pct_hard_stop`

---

## Top 20 Candidates

| # | Combo ID | Score | Sharpe | CAGR | MaxDD | Kelly | DD Soft | DD Hard |
|---|----------|-------|--------|------|-------|-------|---------|---------|
| 1 | ffae19fec604 | 0.993 | 1.07 | 14.3% | -9.9% | 0.70 | 5% | 10% |
| 2 | 0576d1c2bfe6 | 0.993 | 1.07 | 14.3% | -9.9% | 0.90 | 5% | 10% |
| 3 | 2411a44ce582 | 0.993 | 1.07 | 14.3% | -9.9% | 1.10 | 5% | 10% |
| 4 | f93ac29cc62d | 0.993 | 1.07 | 14.3% | -9.9% | 1.30 | 5% | 10% |
| 5 | fa94dabfc7d9 | 0.993 | 1.07 | 14.3% | -9.9% | 0.70 | 5% | 10% |
| 6 | c9b8c7cf9b5f | 0.993 | 1.07 | 14.3% | -9.9% | 0.90 | 5% | 10% |
| 7 | 2368daacf8d9 | 0.993 | 1.07 | 14.3% | -9.9% | 1.10 | 5% | 10% |
| 8 | 6ecd3e5356e1 | 0.993 | 1.07 | 14.3% | -9.9% | 1.30 | 5% | 10% |
| 9 | abd891f17a53 | 0.993 | 1.07 | 14.3% | -9.9% | 0.70 | 5% | 10% |
| 10 | 70d95e17dd21 | 0.993 | 1.07 | 14.3% | -9.9% | 0.90 | 5% | 10% |

> **Note**: All 20 candidates have identical scores (0.993). Differentiation is by Kelly cap factor and DD multiplier.

---

## How to Replay a Single Combo

El runner actualmente no soporta `--combo-id` directo. Para filtrar un combo específico:

```powershell
# 1. Buscar en results.csv por combo_id
Select-String -Path "report/out_2B_3_3_grid_full_20251230_191032/results.csv" -Pattern "ffae19fec604"

# 2. Extraer los params del topk.json y aplicar manualmente
# Ver report/2B_3_3_topk_freeze.json para params completos
```

**Future**: Añadir `--combo-id` flag al runner para replay directo.

---

## Artifacts

- `2B_3_3_topk_freeze.json` — Consolidated JSON with full params
- `2B_3_3_topk_freeze.md` — This summary document
