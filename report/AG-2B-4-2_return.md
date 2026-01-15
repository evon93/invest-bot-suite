# Return Packet — AG-2B-4-2

**Ticket**: AG-2B-4-2 — Scoring formula con métricas de riesgo  
**Fecha**: 2025-12-23T22:12

## Fórmula Final

```python
"1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop"
```

**Racional** (Alternativa A - Conservadora):
- Premia `sharpe_ratio` (peso 1.0), `cagr` (0.5), `win_rate` (0.3)
- Penaliza `max_drawdown` (1.5x) y `pct_time_hard_stop` (0.5x)
- No penaliza triggers individuales para evitar descartar estrategias agresivas válidas

## Verificación topk.json

```json
{
  "score_formula": "1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop",
  "candidates": [
    {"rank": 1, "combo_id": "ffae19fec604", "score": 0.9926, ...},
    {"rank": 2, "combo_id": "c648aadd02dc", "score": 0.0, ...},
    ...
  ]
}
```

✅ Score se computa correctamente y ordena candidatos.

## Comando Reproducible

```bash
python tools/run_calibration_2B.py --mode quick --max-combinations 3 --seed 42
```

## Verificación

```
pytest -q → 57 passed ✅
smoke test → 3 ok, 0 errors ✅
```

## Artefactos DoD

- [x] `report/AG-2B-4-2_return.md` (este archivo)
- [x] `report/AG-2B-4-2_notes.md` (alternativas A vs B)
- [x] `report/AG-2B-4-2_diff.patch`
- [x] `report/AG-2B-4-2_pytest.txt`
- [x] `report/AG-2B-4-2_run.txt`
