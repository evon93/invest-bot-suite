# AG-3J-1-1: Strategy v0.8 Selector — Return Packet

**Ticket**: AG-3J-1-1 — Strategy v0.8 contract + selector  
**Branch**: `feature/AG-3J-1-1_strategy_selector_v0_8`  
**Commit**: `fe85f52`  
**Date**: 2026-01-12  
**Status**: ✅ PASS

## Summary

Introducido selector de estrategias con `--strategy {v0_7,v0_8}` en run_live_3E.py:

- v0_7 (default): SMA crossover existente
- v0_8 (stub): Placeholder que retorna lista vacía

## Files Changed

| File | Change |
|------|--------|
| `strategy_engine/strategy_v0_8.py` | NEW: stub strategy (51 lines) |
| `strategy_engine/strategy_registry.py` | NEW: selector/factory (50 lines) |
| `engine/loop_stepper.py` | +10 lines: accept strategy_fn param |
| `tools/run_live_3E.py` | +16 lines: --strategy flag |
| `tests/test_strategy_registry_3J.py` | NEW: 9 tests |

## Verification

```
pytest tests/test_strategy_registry_3J.py → 9 passed
pytest -q → 590 passed, 10 skipped
run_live_3E.py --help → shows --strategy {v0_7,v0_8}
```

## DoD Checklist

- [x] `pytest -q` PASS (590 passed)
- [x] `run_live_3E --strategy v0_7` no cambia comportamiento
- [x] `run_live_3E --strategy v0_8` arranca sin crash
- [x] Cambios solo en paths del scope
- [x] Commit con mensaje correcto

## AUDIT_SUMMARY

**Ficheros nuevos**:

- `strategy_engine/strategy_v0_8.py` — stub v0.8
- `strategy_engine/strategy_registry.py` — selector con `get_strategy_fn()`
- `tests/test_strategy_registry_3J.py` — 9 tests

**Ficheros modificados**:

- `engine/loop_stepper.py` — acepta strategy_fn param
- `tools/run_live_3E.py` — --strategy flag

**Riesgos**: Ninguno. Default es v0_7 (backward compatible).
