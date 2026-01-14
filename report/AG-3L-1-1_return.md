# AG-3L-1-1 Return Packet

## Baseline

- **Branch**: main
- **HEAD**: 2fd07e3df29684736e861b65bf0e443ca262a613

## Objetivo

Integrar `MarketDataAdapter` directamente en `LoopStepper` para consumir eventos vía `poll(up_to_ts)` sin DataFrame bridge público.

## Cambios Realizados

### engine/loop_stepper.py

- **Nuevo método `run_adapter_mode()`**:
  - Consume eventos de `MarketDataAdapter` usando `poll(max_items=1, up_to_ts=current_step_ts)`
  - Guard no-lookahead: `assert event.ts <= current_step_ts`
  - Construye slice OHLCV incrementalmente como shim interno (NO exportado)
  - Soporta logging JSONL y metrics_collector

### tools/run_live_3E.py

- **Nuevo flag `--data-mode`**: `dataframe` (default) o `adapter`
- Wiring para usar `run_adapter_mode()` cuando `--data-mode adapter` con `--data fixture`

### tests/ (nuevos)

- `test_loop_stepper_market_data_integration_3L1.py`: 7 tests de integración
- `test_market_data_no_lookahead_enforced_3L1.py`: 4 tests adversariales

## Pytest

```
686 passed, 10 skipped, 7 warnings in 44.12s
```

Ver: `report/pytest_3L1_loop_stepper_feed.txt`

## Smoke Test

```
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv --data-mode adapter --clock simulated --seed 42 --max-steps 5 --outdir report/out_3L1_smoke
```

Artefactos generados:

- `events.ndjson` (AdapterModeDone: 10 consumed, 5 steps)
- `run_meta.json`
- `results.csv`
- `run_metrics.json`
- `state.db`

Ver: `report/smoke_3L1.txt`, `report/ls_out_3L1_smoke.txt`

## Invariantes Verificados

- ✓ No-lookahead: Guard activo, tests adversariales PASS
- ✓ Determinismo: seed=42 produce mismo output (tests PASS)
- ✓ Offline default: Sin acceso a red

## AUDIT_SUMMARY

### Ficheros Modificados

- `engine/loop_stepper.py` (+187 líneas)
- `tools/run_live_3E.py` (+25 líneas)

### Ficheros Nuevos

- `tests/test_loop_stepper_market_data_integration_3L1.py`
- `tests/test_market_data_no_lookahead_enforced_3L1.py`

### Descripción

- Nuevo método `run_adapter_mode()` permite consumo directo de MarketDataAdapter
- Guard no-lookahead valida `event.ts <= current_step_ts` con AssertionError si se viola
- DataFrame bridge ahora es interno (no exportado como API)

### Riesgos/TODOs

- El shim interno construye DataFrame en cada step (potencial optimización futura)
- `run_adapter_mode()` no soporta bus workers, checkpoint ni resume (scope futuro)
