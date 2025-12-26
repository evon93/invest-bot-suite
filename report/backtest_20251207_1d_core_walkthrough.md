# 1D.core Risk Manager Walkthrough

**Fecha**: 2025-12-07  
**Rama**: `feature/1D_riskmanager_v0_5_hardening`

---

## Resumen de Cambios

### Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `risk_manager_v0_5.py` | compute_drawdown robusto (NaN/inf), flags dd_skipped/atr_skipped, método get_dd_cfg() |
| `backtest_initial.py` | Wiring de filter_signal con dd_cfg desde yaml |
| `risk_rules.yaml` | Añadido size_multiplier_soft: 0.5 |
| `tests/test_risk_v0_5_extended.py` | 7 tests nuevos para dd_skipped/atr_skipped |

---

## Cambios Detallados

### 1. `risk_manager_v0_5.py`

**compute_drawdown:**
- Filtra NaN/inf antes del cálculo
- Devuelve `skipped: True` si no hay datos válidos
- Preserva índices originales para peak/trough

**filter_signal:**
- Flag `dd_skipped` cuando falta contexto o curva inválida
- Flag `atr_skipped` cuando atr_ctx vacío/faltante
- `logging.warning` cuando DD se desactiva por datos inválidos

**get_dd_cfg():**
- Nuevo método que expone configuración DD desde risk_rules.yaml
- Mapea: soft_limit_pct → max_dd_soft, hard_limit_pct → max_dd_hard

### 2. `backtest_initial.py`

```python
if risk_manager:
    equity_curve = self.portfolio_value if self.portfolio_value else []
    dd_cfg = risk_manager.get_dd_cfg()  # Desde yaml
    
    allow, annotated = risk_manager.filter_signal(
        {"deltas": deltas, "assets": list(self.prices.columns)},
        current_w,
        nav,
        equity_curve=equity_curve,
        dd_cfg=dd_cfg,
        atr_ctx={},
        last_prices=self.last_valid_prices,
    )
```

### 3. `risk_rules.yaml`

```yaml
max_drawdown:
  soft_limit_pct: 0.05
  hard_limit_pct: 0.08
  lookback_days: 90
  size_multiplier_soft: 0.5  # NUEVO
```

---

## Tests Añadidos

| Test | Cobertura |
|------|-----------|
| test_filter_signal_dd_skipped_empty_equity | equity vacía → dd_skipped=True |
| test_filter_signal_dd_skipped_only_nan | equity solo NaN/inf → dd_skipped=True |
| test_filter_signal_dd_skipped_missing_context | sin equity/dd_cfg → dd_skipped=True |
| test_filter_signal_atr_skipped_empty_ctx | atr_ctx vacío → atr_skipped=True |
| test_filter_signal_atr_skipped_missing_ctx | sin atr_ctx → atr_skipped=True |
| test_compute_drawdown_skipped_flag | flag skipped en compute_drawdown |

---

## Resultados de Tests

```
47 passed in 1.80s
```

---

## Riesgos / TODOs

1. **ATR dinámico**: Actualmente atr_ctx se pasa vacío desde backtest. Sería deseable calcularlo automáticamente.
2. **lookback_days**: Existe en yaml pero no se usa en la lógica actual de DD.

---

## AUDIT_SUMMARY

**Ficheros modificados:**
- risk_manager_v0_5.py
- backtest_initial.py
- risk_rules.yaml
- tests/test_risk_v0_5_extended.py

**Descripción:**
- Hardening del núcleo 1D.core: robustez ante NaN/inf en DD, flags para contexto faltante, wiring de dd_cfg desde yaml.

**Riesgos abiertos:**
- atr_ctx no se calcula automáticamente en backtest (se pasa vacío).
