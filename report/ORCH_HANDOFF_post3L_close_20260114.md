# ORCH_HANDOFF Phase 3L Close — 2026-01-14

## Baseline

- **main HEAD previo**: 2fd07e3 (Merge PR #30 from feature/AG-3K-6-1_closeout)
- **Nueva rama closeout**: feature/AG-3L-4-1_closeout
- **HEAD closeout**: 3de4827

## Commits Consolidados

| Ticket | Commit | Descripción |
|--------|--------|-------------|
| AG-3L-1-1 | 261b987 | LoopStepper.run_adapter_mode() consume MarketDataAdapter directamente |
| AG-3L-2-1 | de07ef5 | CCXT opcional + tests gated (sin red en CI) |
| AG-3L-3-1 | 3de4827 | MockOHLCVClient edge-cases + strict validation |

## Resumen de Cambios

### 3L.1 — LoopStepper Adapter Integration

- Nuevo método `run_adapter_mode()` que consume `MarketDataAdapter.poll(up_to_ts)`
- Guard no-lookahead: `assert event.ts <= current_step_ts`
- Shim OHLCV interno (no expuesto como API)
- Flag `--data-mode adapter` en `run_live_3E.py`
- 11 tests nuevos

### 3L.2 — CCXT Optional Dependency

- `requirements-ccxt.txt` con `ccxt==4.4.54`
- Tests gated que solo corren con `INVESTBOT_ALLOW_NETWORK=1`
- Tests parity offline sin ccxt instalado
- Sección en README.md

### 3L.3 — MockOHLCVClient Hardening

- `OHLCVValidationError` para errores de validación
- `validate_ohlcv_data()` con policy estricta
- `MockOHLCVClient` con data injection y `strict=True`
- Atributo `has_gaps` para detección de gaps
- 16 tests de edge-cases

## Verificación

### pytest

```
711 passed, 11 skipped, 7 warnings in 44.31s
```

Ver: [pytest_3L4_closeout.txt](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/report/pytest_3L4_closeout.txt)

### Smoke Offline (adapter mode)

```bash
python tools/run_live_3E.py --data fixture --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv --data-mode adapter --clock simulated --exchange paper --seed 42 --outdir report/out_3L4_smoke
```

Artefactos generados:

- events.ndjson, run_meta.json, results.csv, run_metrics.json, state.db

Ver: [smoke_3L4.txt](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/report/smoke_3L4.txt)

## Riesgos / Deuda Técnica

1. **stderr/NativeCommandError en PowerShell**: Los logs a stderr causan exit code 1 falso positivo. Considerar redirigir INFO a stdout o suprimir en CI.

2. **Shim OHLCV interno**: El slice DataFrame se reconstruye en cada step (potencial optimización futura).

3. **run_adapter_mode() limitado**: No soporta bus workers, checkpoint ni resume (scope futuro).

## Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `engine/loop_stepper.py` | +187 líneas (run_adapter_mode) |
| `engine/market_data/ccxt_adapter.py` | +130 líneas (validate_ohlcv_data, MockOHLCVClient) |
| `tools/run_live_3E.py` | +25 líneas (--data-mode) |
| `requirements-ccxt.txt` | Dependencia opcional |
| `README.md` | Sección CCXT opcional |
