# Bridge Report: 2B → 2C

**Fecha**: 2025-12-23  
**Estado 2B**: ✅ Completado

---

## Resumen de 2B

**Objetivo**: Calibración de parámetros de riesgo con métricas extendidas.

**Entregables**:
- Runner de calibración: `tools/run_calibration_2B.py`
- Configuración: `configs/risk_calibration_2B.yaml`
- Tests: `tests/test_calibration_runner_2B.py`, `tests/test_backtester_closed_trades.py`

**Nuevas Métricas**:
- `closed_trades` con `realized_pnl` y `win_rate`
- `risk_events` con contadores ATR/hard_stop
- Score formula con penalización por tiempo en hard_stop

---

## APIs Expuestas para 2C

### SimpleBacktester

```python
bt = SimpleBacktester(prices, initial_capital=10_000)
df = bt.run(risk_manager=rm)

# Nuevas estructuras
bt.closed_trades  # List[Dict] con {date, asset, qty, entry_cost, exit_price, realized_pnl}
bt.risk_events    # List[Dict] con {date, risk_decision}
bt._avg_cost      # Dict[str, float] coste medio por asset
```

### run_calibration_2B.py

```python
run_calibration(
    mode="quick",           # "quick" o "full"
    max_combinations=12,    # límite en quick mode
    seed=42,                # reproducibilidad
    output_dir_override=None,  # CLI override de output.dir
)
```

### CLI

```bash
python tools/run_calibration_2B.py \
    --mode quick \
    --max-combinations 12 \
    --seed 42 \
    --output-dir /path/to/output
```

---

## Dependencias para 2C

1. **Baseline validado**: `risk_rules.yaml` sin errores/warnings
2. **Métricas disponibles**: closed_trades, risk_events, win_rate, atr_stop_count, etc.
3. **Score formula**: Configurable en YAML, evaluada con todas las métricas

---

## Recomendaciones para 2C

1. **Usar scores de 2B** como baseline para optimización adicional
2. **Considerar Alternativa B** (más estricta) si A no filtra suficiente
3. **Extender topk.json** con campos adicionales según necesidad
4. **Mantener seed 42** para reproducibilidad cruzada
