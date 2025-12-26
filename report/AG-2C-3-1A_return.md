# AG-2C-3-1A — Return Packet

**Fecha:** 2025-12-25 17:42 CET  
**Rama:** `feature/2C_apply_best_params_v0_1`

---

## Archivo fuente seleccionado

| Campo | Valor |
|-------|-------|
| **Path** | `report/calibration_2B/topk.json` |
| **Tamaño** | 1673 bytes (57 líneas) |
| **Formato** | JSON dict |

### Justificación

- Nombre explícito (`topk.json`) indica resultados rankeados
- Ubicación dentro de `report/calibration_2B/` (directorio de resultados 2B)
- Contiene `score_formula` + `candidates[]` ordenados por `rank`
- Estructura clara con `params` listos para mapear a `risk_rules.yaml`

---

## Resumen de estructura

```
topk.json
├── score_formula: "1.0*sharpe_ratio + 0.5*cagr + ..."
├── top_k: 20
└── candidates: [
      {rank: 1, combo_id, score: 0.9926, params: {...}},
      {rank: 2, ...},  // score=0 (fallido)
      {rank: 3, ...}   // score=0 (fallido)
    ]
```

### Best candidate (rank=1)

| Métrica | Valor |
|---------|-------|
| score | 0.9926 |
| sharpe_ratio | 1.070 |
| cagr | 14.26% |
| max_drawdown | -9.93% |
| calmar_ratio | 1.436 |

### Params a aplicar

```json
{
  "stop_loss.atr_multiplier": 2.0,
  "stop_loss.min_stop_pct": 0.02,
  "max_drawdown.soft_limit_pct": 0.05,
  "max_drawdown.hard_limit_pct": 0.1,
  "max_drawdown.size_multiplier_soft": 0.5,
  "kelly.cap_factor": 0.7
}
```

---

## Artefactos generados

| Archivo | Propósito |
|---------|-----------|
| `report/AG-2C-3-1A_head.txt` | HEAD actual |
| `report/AG-2C-3-1A_status.txt` | Status repo |
| `report/AG-2C-3-1A_topk_head.json` | Copia del topk.json |
| `report/AG-2C-3-1A_contract.md` | Contrato de estructura |
| `report/AG-2C-3-1A_return.md` | Este documento |

---

## DoD

- [x] Archivo fuente localizado: `report/calibration_2B/topk.json`
- [x] Estructura caracterizada
- [x] Contrato documentado
- [x] Params del best candidate extraídos
