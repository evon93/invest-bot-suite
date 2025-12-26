# Risk Calibration 2B — Alignment Note

**Fecha:** 2025-12-18  
**Rama:** `feature/2B_risk_calibration`

---

## Cambios en `configs/risk_calibration_2B.yaml`

| Antes (incorrecto) | Después (alineado) | Archivo referencia |
|--------------------|-------------------|-------------------|
| `atr_stop.atr_multiplier` | `stop_loss.atr_multiplier` | `risk_rules.yaml:24-28` |
| `atr_stop.min_stop_pct` | `stop_loss.min_stop_pct` | `risk_rules.yaml:24-28` |
| `dd_guardrail.max_drawdown_pct` | `max_drawdown.soft_limit_pct` + `hard_limit_pct` | `risk_rules.yaml:67-71`, `risk_manager_v0_5.py:get_dd_cfg()` |
| `kelly.kelly_fraction_cap` | `kelly.cap_factor` | `risk_rules.yaml:37` |

---

## Justificación

1. **stop_loss vs atr_stop**: En `risk_rules.yaml` la sección `atr_stop: {}` está vacía (placeholder Antigravity). La lógica real de ATR stops usa `stop_loss.atr_multiplier` y `stop_loss.min_stop_pct`.

2. **max_drawdown vs dd_guardrail**: El RiskManager en `get_dd_cfg()` lee de `rules.get("max_drawdown", {})` y mapea `soft_limit_pct` → `max_dd_soft`, `hard_limit_pct` → `max_dd_hard`.

3. **kelly.cap_factor vs kelly_fraction_cap**: En `risk_rules.yaml` el campo es `kelly.cap_factor` (valor 0.50). El RiskManager usa `kelly_rules.get("cap_factor", 0.5)` en `cap_position_size()`.

---

## Nuevos valores del grid

```yaml
grid:
  stop_loss:
    atr_multiplier: [2.0, 2.5, 3.0]
    min_stop_pct: [0.02, 0.03]
  max_drawdown:
    soft_limit_pct: [0.05, 0.08]
    hard_limit_pct: [0.10, 0.15]
  kelly:
    cap_factor: [0.30, 0.50, 0.70]
```

**Total combinaciones:** 3 × 2 × 2 × 2 × 3 = 72 variantes
