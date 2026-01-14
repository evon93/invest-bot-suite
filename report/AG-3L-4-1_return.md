# AG-3L-4-1 Return Packet

## Baseline

- **main HEAD previo**: 2fd07e3 (Merge PR #30 AG-3K-6-1_closeout)
- **Nueva rama closeout**: feature/AG-3L-4-1_closeout
- **HEAD closeout**: 3de4827

## Objetivo

Consolidar los 3 commits de Phase 3L en rama closeout, verificar y documentar.

## Cherry-Picks Realizados

| Orden | Commit Original | Commit en Closeout | Ticket | Descripción |
|-------|-----------------|-------------------|--------|-------------|
| 1 | c46aaec | 261b987 | AG-3L-1-1 | LoopStepper.run_adapter_mode() |
| 2 | 6847c79 | de07ef5 | AG-3L-2-1 | CCXT optional + gated tests |
| 3 | faa0eb9 | 3de4827 | AG-3L-3-1 | MockOHLCVClient hardening |

**Resultado:** Sin conflictos. Los 3 cherry-picks completaron limpiamente.

## Verificación

### pytest

```
711 passed, 11 skipped, 7 warnings in 44.31s
```

Ver: `report/pytest_3L4_closeout.txt`

### Smoke Offline (adapter mode)

```bash
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv --data-mode adapter --clock simulated --exchange paper --seed 42 --outdir report/out_3L4_smoke
```

Artefactos generados:

- events.ndjson (AdapterModeDone)
- run_meta.json
- results.csv
- run_metrics.json
- state.db

Ver: `report/smoke_3L4.txt`, `report/ls_out_3L4_smoke.txt`

## Documentación de Cierre

- `report/ORCH_HANDOFF_post3L_close_20260114.md`
- `report/bridge_3L_to_next_report.md`
- `registro_de_estado_invest_bot.md` (actualizado)

## AUDIT_SUMMARY

### Tickets Consolidados

- **AG-3L-1-1**: run_adapter_mode() consume MarketDataAdapter.poll() directamente
- **AG-3L-2-1**: CCXT como dependencia opcional (requirements-ccxt.txt)
- **AG-3L-3-1**: validate_ohlcv_data() con policy estricta

### Archivos Principales

- `engine/loop_stepper.py` (+187 líneas)
- `engine/market_data/ccxt_adapter.py` (+130 líneas)
- `tools/run_live_3E.py` (+25 líneas)
- `requirements-ccxt.txt` (nuevo)
- `README.md` (sección CCXT)
- 5 archivos de test nuevos

### Riesgos/TODOs

1. stderr en PS causa exit code 1 falso positivo (considerar redirect)
2. Shim OHLCV interno reconstruye DataFrame en cada step
3. run_adapter_mode() no soporta bus workers ni checkpoint (scope futuro)

## Próximo Paso

Merge de `feature/AG-3L-4-1_closeout` a `main` vía PR.
