# Risk Calibration 2B — Implementation Guide

**Fecha**: 2025-12-23  
**Versión**: 1.0

---

## Cómo Ejecutar

### Quick Mode (desarrollo/testing)

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 12 --seed 42
```

### Full Mode (producción)

```bash
python tools/run_calibration_2B.py --mode full --seed 42
```

### Con output.dir personalizado

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42 --output-dir /tmp/calibration_test
```

---

## output.dir y Artefactos

**Directorio por defecto**: `report/calibration_2B/`

**Artefactos generados**:

| Archivo | Descripción |
|---------|-------------|
| `results.csv` | Resultados completos de todas las combinaciones |
| `run_log.txt` | Log de ejecución con timestamps |
| `summary.md` | Resumen en markdown del run |
| `topk.json` | Top-K candidatos con scores y params |
| `run_meta.json` | Metadata del run (seed, hash, git head, timing) |

---

## Métricas

### Métricas Base (backtest)

| Métrica | Descripción |
|---------|-------------|
| `cagr` | Compound Annual Growth Rate |
| `total_return` | Retorno total del período |
| `max_drawdown` | Drawdown máximo (negativo) |
| `sharpe_ratio` | Sharpe ratio anualizado |
| `volatility` | Volatilidad anualizada |
| `calmar_ratio` | CAGR / abs(max_drawdown) |
| `num_trades` | Número de trades ejecutados |

### Métricas de Closed Trades

| Métrica | Descripción |
|---------|-------------|
| `closed_trades_count` | Total de trades cerrados |
| `wins_count` | Trades con PnL > 0 |
| `losses_count` | Trades con PnL < 0 |
| `win_rate` | wins_count / closed_trades_count |
| `gross_pnl` | Suma de realized_pnl de todos los trades |
| `avg_win` | Promedio de PnL en trades ganadores |
| `avg_loss` | Promedio de PnL en trades perdedores (negativo) |

### Métricas de Risk Events

| Métrica | Descripción |
|---------|-------------|
| `atr_stop_count` | Transiciones False→True de ATR stop |
| `hard_stop_trigger_count` | Transiciones False→True de DD hard_stop |
| `pct_time_hard_stop` | % de ticks en estado hard_stop |
| `missing_risk_events` | True si no hay risk_events (fallback) |

---

## Score Formula

```python
1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop
```

**Interpretación**:
- Premia rendimiento ajustado al riesgo (sharpe, cagr)
- Premia consistencia (win_rate)
- Penaliza drawdown y tiempo en hard_stop

---

## Configuración

**Archivo**: `configs/risk_calibration_2B.yaml`

**Secciones principales**:
- `grid`: Parámetros a calibrar y sus valores
- `execution`: Modos quick/full y límites
- `score`: Fórmula de puntuación
- `output`: Directorio y flags de guardado
