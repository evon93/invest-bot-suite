# AG-2C-5-1A — Return Packet

**Fecha:** 2025-12-25 22:10 CET  
**Rama:** `feature/2C_apply_best_params_v0_1`  
**Commit:** `f0e3120`

---

## YAML lib usada

**PyYAML 6.0.2**

---

## Cambios aplicados

| Path | Antes | Después |
|------|-------|---------|
| `stop_loss.atr_multiplier` | 2.5 | **2.0** |
| `max_drawdown.hard_limit_pct` | 0.08 | **0.1** |
| `kelly.cap_factor` | 0.50 | **0.7** |

> [!NOTE]
> `min_stop_pct`, `soft_limit_pct` y `size_multiplier_soft` ya tenían los valores del best_params, por eso no aparecen como cambios.

---

## Archivos generados

| Archivo | Propósito |
|---------|-----------|
| `tools/apply_calibration_topk.py` | CLI tool |
| `tests/test_apply_calibration_topk_2C.py` | 8 tests |
| `risk_rules_candidate.yaml` | Config candidata |
| `report/AG-2C-5-1A_diff.patch` | Diff base vs candidate |

---

## Resultado pytest

```
77 passed in 1.32s
```

---

## Nota

> [!IMPORTANT]
> PyYAML reformatea el YAML (quita comentarios, normaliza quotes). Los **valores** cambiados son solo los 3 listados arriba.

---

## DoD

- [x] `risk_rules_candidate.yaml` generado
- [x] `report/AG-2C-5-1A_diff.patch` generado
- [x] 8 tests para apply_calibration
- [x] Pytest PASS (77 total)
- [x] Commit creado (`f0e3120`)
