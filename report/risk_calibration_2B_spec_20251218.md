# Risk Calibration 2B — Spec Document

**Fecha:** 2025-12-18  
**Rama:** `feature/2B_risk_calibration`  
**Archivo config:** `configs/risk_calibration_2B.yaml`

---

## Mapping Grid → risk_rules.yaml

| Grid key | risk_rules.yaml path | RiskManager method |
|----------|---------------------|-------------------|
| `stop_loss.atr_multiplier` | `stop_loss.atr_multiplier` | `compute_atr_stop()` |
| `stop_loss.min_stop_pct` | `stop_loss.min_stop_pct` | `compute_atr_stop()` |
| `max_drawdown.soft_limit_pct` | `max_drawdown.soft_limit_pct` | `get_dd_cfg()` → `max_dd_soft` |
| `max_drawdown.hard_limit_pct` | `max_drawdown.hard_limit_pct` | `get_dd_cfg()` → `max_dd_hard` |
| `max_drawdown.size_multiplier_soft` | `max_drawdown.size_multiplier_soft` | `get_dd_cfg()` |
| `kelly.cap_factor` | `kelly.cap_factor` | `cap_position_size()` |

---

## Estructura del Grid

```yaml
grid:
  stop_loss:
    atr_multiplier: [2.0, 2.5, 3.0]        # 3 valores
    min_stop_pct: [0.02, 0.03]             # 2 valores
  max_drawdown:
    soft_limit_pct: [0.05, 0.08]           # 2 valores
    hard_limit_pct: [0.10, 0.15]           # 2 valores
    size_multiplier_soft: [0.5, 0.7, 1.0]  # 3 valores
  kelly:
    cap_factor: [0.30, 0.50, 0.70]         # 3 valores
```

**Total combinaciones:** 3 × 2 × 2 × 2 × 3 × 3 = **216 variantes**

---

## Execution Mode

```yaml
execution:
  mode: "active"           # o "monitor" para dry-run
  max_combinations: null   # null = full grid, 12 = quick smoke
```

- **Quick mode:** `max_combinations: 12` — para validar pipeline
- **Full mode:** `max_combinations: null` — grid completo

---

## Métricas

### Implementadas (compute)
| Métrica | Descripción |
|---------|-------------|
| `cagr` | Compound Annual Growth Rate |
| `total_return` | Retorno total del período |
| `max_drawdown` | Máximo drawdown observado |
| `sharpe_ratio` | Sharpe ratio anualizado |
| `volatility` | Volatilidad anualizada |
| `num_trades` | Número de operaciones |
| `calmar_ratio` | CAGR / max_drawdown |
| `win_rate` | % trades ganadores |

### Pendientes de implementar (compute_pending)
| Métrica | Descripción |
|---------|-------------|
| `atr_stop_count` | Veces que ATR stop triggereó |
| `hard_stop_trigger_count` | Veces que DD hard_stop se activó |
| `pct_time_hard_stop` | % tiempo en estado hard_stop |

> [!NOTE]
> Las métricas `compute_pending` requieren instrumentación adicional en el runner.

---

## Score Formula

```yaml
score:
  formula: "1.0*sharpe_ratio + 0.5*cagr - 1.5*abs(max_drawdown)"
```

Prioriza Sharpe, premia CAGR, penaliza drawdown.
