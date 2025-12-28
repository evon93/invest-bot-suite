# 2E-4-2: Breakdown de Razones de Rechazo por Riesgo

Generado a partir de `run_meta.json` (no logs).

## Datos de run_meta.json

```json
{
  "risk_reject_reasons_topk": {
    "kelly_cap:ETF": 4887,
    "position_limits": 78,
    "dd_soft": 72
  }
}
```

## Análisis

| Motivo | Conteo | % |
|--------|--------|---|
| `kelly_cap:ETF` | 4887 | 97.0% |
| `position_limits` | 78 | 1.5% |
| `dd_soft` | 72 | 1.4% |

### Interpretación

- **kelly_cap:ETF** domina: el Kelly cap (sizing) bloquea la mayoría de operaciones cuando `kelly.cap_factor` es bajo (0.3, 0.5).
- **position_limits** y **dd_soft** aparecen marginalmente.

### Fuente

- Datos: `report/out_2E_4_2_smoke/run_meta.json`
- Columna CSV: `risk_reject_reasons_top` (por combo)
