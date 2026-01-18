# AG-3N-1-1 Return Packet

**Status**: ✅ PASS  
**Branch**: `feature/AG-3N-1-1_config_preset`  
**Commit**: 53979d7 `3N.1: add --config/--preset to run_live_3E with tested merge precedence`  
**Baseline**: `main@7317871`

## Summary

Added `--config` and `--preset` flags to `tools/run_live_3E.py` with tested merge precedence.

## Changes

| File | Change |
|------|--------|
| `configs/run_live_3E_presets.yaml` | [NEW] Preset file with `paper_offline_adapter` |
| `tools/run_live_3E.py` | [MODIFY] 2-phase parse, loader functions, config merge |
| `engine/idempotency.py` | [MODIFY] Added `close()` to `InMemoryIdempotencyStore` |
| `tests/test_run_live_3E_config_merge_3N1.py` | [NEW] Unit tests for merge precedence |
| `tests/test_run_live_3E_preset_smoke_3N1.py` | [NEW] Smoke tests for preset execution |

## Features

- **Parse 2 fases**: Early capture de `--config`/`--preset` → merge → final parse
- **Precedencia**: `preset < config < CLI` (CLI siempre gana)
- **Loader**: Soporta YAML y JSON
- **Seguridad**: `allow_network: false` por defecto en presets
- **Compat backwards**: Sin flags = comportamiento idéntico al anterior

## Verification

### pytest (750 passed)

```
750 passed, 11 skipped, 7 warnings in 234.37s
```

### Smoke manual

```bash
python tools/run_live_3E.py --preset paper_offline_adapter --max-steps 25 \
  --outdir report/out_3N1_preset_smoke --run-dir report/out_3N1_preset_smoke
```

Artefactos generados:

- checkpoint.json
- events.ndjson
- run_meta.json
- results.csv
- run_metrics.json
- state.db

### --help

```
--config PATH         Path to config file (YAML or JSON). Overrides preset values.
--preset NAME         Preset name from configs/run_live_3E_presets.yaml
```

## Artifacts

- `report/AG-3N-1-1_diff.patch` (562 lines)
- `report/AG-3N-1-1_last_commit.txt`
- `report/pytest_3N1_postmerge.txt`
- `report/smoke_3N1_preset_smoke.txt`
- `report/ls_out_3N1_preset_smoke.txt`

## Bug Fix Included

Durante la implementación se detectó que `InMemoryIdempotencyStore` no tenía método `close()`, lo que causaba error cuando el preset usaba `idempotency_backend: memory`. Se añadió como no-op para consistencia de interfaz.
