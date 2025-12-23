# Return Packet — AG-2B-5-6A

**Ticket**: AG-2B-5-6A — Cierre 2B (docs + evidencia + commit)  
**Fecha**: 2025-12-23T22:48

---

## Comando Reproducible

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```

---

## output.dir

```
report/calibration_2B/
```

---

## Artefactos en output.dir

| Archivo | Descripción |
|---------|-------------|
| `results.csv` | Resultados completos (26 columnas, incluye nuevas métricas) |
| `run_log.txt` | Log de ejecución con timestamps |
| `summary.md` | Resumen markdown (sin truncados) |
| `topk.json` | Top-K candidatos con nueva score formula |
| `run_meta.json` | Metadata (seed=42, mode=quick, git_head, config_hash) |

---

## Evidencia PASO 6

| Comando | Resultado | Artefacto |
|---------|-----------|-----------|
| `pytest -q` | 57 passed | `report/pytest_2B_final.txt` |
| `validate_risk_config.py` | 0 errors | `report/validate_risk_config_2B_final.txt` |
| `run_calibration_2B.py` | 3 ok, 0 errors | `report/calibration_2B/*` |

---

## Documentación PASO 5

| Archivo | Descripción |
|---------|-------------|
| `report/risk_calibration_2B_impl_20251223.md` | Guía de implementación |
| `bridge_2B_to_2C_report.md` | Bridge report para 2C |
| `registro_de_estado_invest_bot.md` | Estado 2B cerrado |

---

## Higiene PASO 5.1

✅ `summary.md` sin truncados (`...`)  
✅ `topk.json` sin truncados

---

## Git

```
git log -1 --oneline
```

(ejecutar después del commit)

---

## NOTA CRÍTICA

**NO hacer git push desde la sesión actual.** El push se hace manualmente en PowerShell tras exit.
