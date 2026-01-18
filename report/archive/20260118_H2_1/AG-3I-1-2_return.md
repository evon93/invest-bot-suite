# AG-3I-1-2: TimeProvider Correctivos DS — Return Packet

**Ticket**: AG-3I-1-2 — TimeProvider: test isolation + tz validation + docs  
**Parent**: AG-3I-1-1 @ 04d6a6b  
**Date**: 2026-01-12  
**Status**: ✅ PASS

## Summary

Implementados los correctivos del audit DeepSeek (DS-3I-1-1):

| Correctivo | Implementación |
|------------|----------------|
| tz validation | `set_utc()` → ValueError si naive, normaliza non-UTC a UTC |
| Test isolation | fixture `autouse=True` en `conftest.py` para reset singleton |
| Documentación | docstring expandido en `SimulatedTimeProvider.monotonic_ns()` |
| Tests | +2 tests: naive ValueError, UTC normalization |

## Files Modified

| File | Change |
|------|--------|
| `engine/time_provider.py` | +26 lines: validación tz, docstring |
| `tests/conftest.py` | +27 lines: fixture autouse |
| `tests/test_time_provider_3I1.py` | +28 lines: 2 tests nuevos |

## Verification

```
pytest -q tests/test_time_provider_3I1.py → 16 passed
pytest -q → 581 passed, 10 skipped
git diff --stat → solo 3 archivos del scope
```

## DoD Checklist

- [x] `pytest -q` PASS
- [x] `pytest -q tests/test_time_provider_3I1.py` PASS
- [x] no cambios fuera de scope
- [x] Commit con mensaje apropiado

## AUDIT_SUMMARY

**Ficheros modificados**:

- `engine/time_provider.py` — validación tz en set_utc(), docstring mejorado
- `tests/conftest.py` — fixture autouse para aislamiento singleton
- `tests/test_time_provider_3I1.py` — 2 tests nuevos

**Ficheros referenciados**:

- `report/external_ai/inbox_external/DS-3I-1-1_audit.md` — copia del audit DS

**Riesgos / Dudas**: Ninguno. Cambios aditivos, backward-compatible.
