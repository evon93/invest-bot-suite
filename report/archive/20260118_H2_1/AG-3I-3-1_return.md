# AG-3I-3-1: Rotate Keep — Return Packet

**Ticket**: AG-3I-3-1 — Rotate keep (no-dup)  
**Date**: 2026-01-12  
**Status**: ✅ ALREADY IMPLEMENTED

## Summary

Este ticket ya fue implementado:

- **Commit**: `d4bdce6` — AG-3I-3-1: --metrics-rotate-keep flag for retention of rotated files
- **Merge**: `28db80d` — PR #25

## Implementation Details

| Component | Location |
|-----------|----------|
| `rotate_keep` parameter | `engine/metrics_collector.py:MetricsWriter.__init__()` |
| `_cleanup_rotated()` | `engine/metrics_collector.py:378-412` |
| CLI flag | `tools/run_live_3E.py:--metrics-rotate-keep` |
| Tests | `tests/test_metrics_rotate_keep_3I3.py` (6 tests) |

## Features

- `rotate_keep=N`: Mantiene solo N archivos rotados más recientes
- `rotate_keep=0`: Elimina todos los archivos rotados
- `rotate_keep=None`: Mantiene todos (default)
- Cleanup best-effort (errores individuales no detienen el proceso)

## Verification

```
pytest tests/test_metrics_rotate_keep_3I3.py → 6 passed
pytest -q → 581 passed, 10 skipped
```

## DoD

- [x] Trabajo ya implementado y mergeado
- [x] Tests pasan
- [x] No se requiere commit adicional
