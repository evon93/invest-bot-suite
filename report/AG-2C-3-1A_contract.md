# AG-2C-3-1A — Contract: topk.json

**Path:** `report/calibration_2B/topk.json`  
**Formato:** JSON (dict)

---

## Estructura

```json
{
  "score_formula": "<string con fórmula de scoring>",
  "top_k": <int>,
  "candidates": [
    {
      "rank": <int>,
      "combo_id": "<string hash>",
      "score": <float>,
      "sharpe_ratio": <float>,
      "cagr": <float>,
      "max_drawdown": <float>,
      "calmar_ratio": <float>,
      "params": {
        "stop_loss.atr_multiplier": <float>,
        "stop_loss.min_stop_pct": <float>,
        "max_drawdown.soft_limit_pct": <float>,
        "max_drawdown.hard_limit_pct": <float>,
        "max_drawdown.size_multiplier_soft": <float>,
        "kelly.cap_factor": <float>
      }
    },
    ...
  ]
}
```

---

## Keys obligatorias

### Root level
| Key | Tipo | Uso |
|-----|------|-----|
| `score_formula` | string | Fórmula usada para calcular score compuesto |
| `top_k` | int | Número máximo de candidatos en lista |
| `candidates` | array | Lista ordenada por rank (1=mejor) |

### Por candidato
| Key | Tipo | Uso |
|-----|------|-----|
| `rank` | int | Posición (1-indexed) |
| `combo_id` | string | Hash único de la combinación de params |
| `score` | float | Score compuesto calculado |
| `sharpe_ratio` | float | Métrica Sharpe |
| `cagr` | float | CAGR del backtest |
| `max_drawdown` | float | Máximo drawdown (negativo) |
| `calmar_ratio` | float | Calmar ratio |
| `params` | dict | Parámetros de risk manager usados |

---

## Criterio "best"

1. **Métrica primaria:** `score` (mayor = mejor)
2. **Tie-breaker:** `sharpe_ratio` > `cagr` > `calmar_ratio`
3. **Para 2C:** usar `candidates[0]` (rank=1)

---

## Notas

- Solo rank=1 tiene score real (0.9926); ranks 2-3 tienen score=0 (runs fallidos o incompletos)
- Para aplicar params, extraer `candidates[0].params` y mapear a `risk_rules.yaml`
