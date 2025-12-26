# 2B Runner Wiring Findings

**Fecha:** 2025-12-21  
**Rama:** `feature/2B_risk_calibration`  
**Objetivo:** Auditoría para construir `tools/run_calibration_2B.py`

---

## 1. RiskManagerV05 — Firmas y Wiring

### Constructor
```python
# risk_manager_v0_5.py:32-81
def __init__(self, rules: Union[Dict, str, Path]):
    if isinstance(rules, (str, Path)):
        with open(rules, "r", encoding="utf-8") as f:
            self.rules = yaml.safe_load(f)
    else:
        self.rules = rules  # ← ACEPTA DICT IN-MEMORY
```

**Conclusión:** Se puede pasar un dict overlay directamente sin crear archivo temporal.

### Modo active/monitor
```python
# risk_manager_v0_5.py:73-78
rm_cfg = self.rules.get("risk_manager", {}) or {}
self.mode = str(rm_cfg.get("mode", "active")).lower()
```

**Cómo activar execution.mode:**
```python
overlay = base_rules.copy()
overlay["risk_manager"] = {"mode": "active"}  # o "monitor"
rm = RiskManagerV05(overlay)
```

### get_dd_cfg()
```python
# risk_manager_v0_5.py:86-99
def get_dd_cfg(self) -> Dict[str, Any]:
    dd_rules = self.rules.get("max_drawdown", {})
    return {
        "max_dd_soft": float(dd_rules.get("soft_limit_pct", 0.05)),
        "max_dd_hard": float(dd_rules.get("hard_limit_pct", 0.10)),
        "size_multiplier_soft": float(dd_rules.get("size_multiplier_soft", 0.5)),
    }
```

---

## 2. SimpleBacktester — Datos Disponibles

### run() retorna
```python
# backtest_initial.py:175-230
def run(self, risk_manager=None) -> pd.DataFrame:
    # Returns DataFrame con columnas: date, value
    return pd.DataFrame(records)  # [{"date": ..., "value": ...}, ...]
```

### Atributos accesibles post-run
| Atributo | Tipo | Contenido |
|----------|------|-----------|
| `bt.trades` | `List[Dict]` | `{date, asset, shares, price}` |
| `bt.portfolio_value` | `List[float]` | Equity curve |
| `bt.positions` | `Dict[str, float]` | Posiciones finales |

### Estructura de trades
```python
# backtest_initial.py:163-170
self.trades.append({
    "date": date,
    "asset": asset,
    "shares": shares_delta,
    "price": price,
})
```

---

## 3. calculate_metrics — Métricas Actuales

```python
# backtest_initial.py:235-290
return {
    "cagr": cagr,
    "total_return": total_return,
    "max_drawdown": drawdown,
    "sharpe_ratio": sharpe,
    "volatility": volatility,
}
```

---

## 4. Métricas Adicionales — Implementación

### Implementables desde datos existentes

| Métrica | Fórmula | Datos necesarios |
|---------|---------|------------------|
| `calmar_ratio` | `cagr / abs(max_drawdown)` | Ya calculados |
| `win_rate` | `len([t for t in trades if t["shares"] > 0 and ganancia > 0]) / len(trades)` | Requiere precio de cierre |
| `num_trades` | `len(bt.trades)` | Disponible |

### Requieren instrumentación adicional

| Métrica | Cómo obtener |
|---------|--------------|
| `atr_stop_count` | Instrumentar `filter_signal` para contar `stop_signals` |
| `hard_stop_trigger_count` | Instrumentar cuando `risk_decision["force_close_positions"] == True` |
| `pct_time_hard_stop` | Acumular días en estado hard_stop / total días |

---

## 5. Recomendación de Implementación

### Overlay de rules (sin archivo temporal)
```python
import yaml
from pathlib import Path
from copy import deepcopy

def load_and_overlay(base_path: Path, overrides: dict) -> dict:
    with open(base_path, "r") as f:
        base = yaml.safe_load(f)
    
    # Deep merge overrides
    result = deepcopy(base)
    for section, values in overrides.items():
        if section not in result:
            result[section] = {}
        if isinstance(values, dict):
            result[section].update(values)
        else:
            result[section] = values
    
    return result

# Uso:
rules = load_and_overlay(
    Path("risk_rules.yaml"),
    {
        "max_drawdown": {"soft_limit_pct": 0.08, "hard_limit_pct": 0.15},
        "kelly": {"cap_factor": 0.30},
        "risk_manager": {"mode": "active"},
    }
)
rm = RiskManagerV05(rules)
```

### Runner skeleton
```python
def run_single_variant(base_rules: dict, variant_overrides: dict) -> dict:
    rules = load_and_overlay(base_rules, variant_overrides)
    rm = RiskManagerV05(rules)
    
    prices = generate_synthetic_prices(...)
    bt = SimpleBacktester(prices)
    df = bt.run(risk_manager=rm)
    
    metrics = calculate_metrics(df)
    metrics["num_trades"] = len(bt.trades)
    metrics["calmar_ratio"] = metrics["cagr"] / abs(metrics["max_drawdown"]) if metrics["max_drawdown"] != 0 else 0
    
    return {
        "variant": variant_overrides,
        "metrics": metrics,
    }
```

---

## 6. Rutas Clave

| Archivo | Propósito |
|---------|-----------|
| `risk_rules.yaml` | Config base (NO modificar) |
| `risk_manager_v0_5.py` | RiskManagerV05 class |
| `backtest_initial.py` | SimpleBacktester + calculate_metrics |
| `configs/risk_calibration_2B.yaml` | Grid spec |

---

## Resumen Ejecutivo

| Pregunta | Respuesta |
|----------|-----------|
| ¿Cómo activar mode=active? | `rules["risk_manager"]["mode"] = "active"` en dict |
| ¿Overlay sin modificar archivo? | ✅ RiskManagerV05 acepta dict in-memory |
| ¿Métricas adicionales posibles? | calmar_ratio, num_trades (directas); win_rate (requiere lógica); atr_stop_count (instrumentación) |
