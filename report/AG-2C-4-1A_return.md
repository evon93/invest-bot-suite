# AG-2C-4-1A — Return Packet

**Fecha:** 2025-12-25 22:00 CET  
**Rama:** `feature/2C_apply_best_params_v0_1`  
**Commit:** `c494dc9`

---

## Resumen de cambios

| Archivo | Propósito |
|---------|-----------|
| `tools/best_params_schema_2C.py` | Validadores + selector determinista |
| `tools/build_best_params_2C.py` | CLI builder |
| `tests/test_best_params_2C.py` | 12 tests |
| `configs/best_params_2C.json` | Output generado |

---

## Selección

| Campo | Valor |
|-------|-------|
| **combo_id** | `ffae19fec604` |
| **rank** | 1 |
| **score** | 0.9926 |
| **selection_method** | `rank_1_verified` |

### Params aplicados

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

## Nota

> [!IMPORTANT]
> **No se recalcula `score_formula`.**  
> Solo se guarda como metadata. Las métricas `win_rate` y `pct_time_hard_stop` no están presentes en topk.json actual.

---

## Resultado pytest

```
69 passed in 2.66s
```

---

## Artefactos generados

| Archivo | Propósito |
|---------|-----------|
| `report/AG-2C-4-1A_pytest.txt` | Salida pytest completa |
| `report/AG-2C-4-1A_pytest_new.txt` | Salida tests nuevos |
| `report/AG-2C-4-1A_run.txt` | Salida builder CLI |
| `report/AG-2C-4-1A_status.txt` | Status pre-commit |
| `report/AG-2C-4-1A_last_commit.txt` | Hash del commit |
| `report/AG-2C-4-1A_return.md` | Este documento |

---

## DoD

- [x] Schema/selector implementado con circuit breaker
- [x] CLI builder funcional
- [x] 12 tests para nuevo código
- [x] `configs/best_params_2C.json` generado
- [x] Commit creado (`c494dc9`)
- [x] 69 tests totales passed
