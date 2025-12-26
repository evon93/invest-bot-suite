# AG-2B-3-3 Return Packet

**Ticket:** AG-2B-3-3  
**Fecha:** 2025-12-21  
**Rama:** `feature/2B_risk_calibration`

---

## Resumen

Implementado runner de calibración 2B con:
- CLI: `--mode {quick,full}`, `--max-combinations N`, `--seed 42`
- Error handling: continúa ante fallos, registra status=error con traceback
- Logging estructurado a TXT y CSV
- Métricas: cagr, total_return, max_drawdown, sharpe_ratio, volatility, num_trades, calmar_ratio

---

## Archivos Modificados/Creados

| Archivo | Acción |
|---------|--------|
| `tools/run_calibration_2B.py` | Creado - Runner principal |
| `report/calibration_run_log_2B.txt` | Generado - Log de ejecución |
| `report/calibration_results_2B.csv` | Generado - Resultados con métricas |
| `report/AG-2B-3-3_run.txt` | Generado - Salida del runner |
| `report/AG-2B-3-3_pytest.txt` | Generado - 52 passed |
| `report/AG-2B-3-3_return.md` | Este archivo |

---

## Verificación

### Pytest
```
52 passed in 1.16s
```

### Runner Quick (3 combos)
```
Mode: quick, Total grid: 216, Running: 3, Seed: 42
START combo_id=c648aadd02dc (1/3)
END combo_id=c648aadd02dc status=ok duration_s=0.06
START combo_id=2a7b39f06e64 (2/3)
END combo_id=2a7b39f06e64 status=ok duration_s=0.33
START combo_id=ffae19fec604 (3/3)
END combo_id=ffae19fec604 status=ok duration_s=0.02
DONE: 3 ok, 0 errors, total 3
```

### CSV Sample (última fila con métricas)
```
combo_id: ffae19fec604
status: ok
cagr: 0.143
max_drawdown: -0.099
sharpe_ratio: 1.07
num_trades: 4
calmar_ratio: 1.44
kelly.cap_factor: 0.7
```

---

## Paths de Evidencia

- `report/AG-2B-3-3_pytest.txt`
- `report/AG-2B-3-3_run.txt`
- `report/calibration_run_log_2B.txt`
- `report/calibration_results_2B.csv`
- `report/AG-2B-3-3_return.md`
