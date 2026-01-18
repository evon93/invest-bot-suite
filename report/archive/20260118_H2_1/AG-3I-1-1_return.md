# AG-3I-1-1: Monotonic Time Provider — Return Packet

**Ticket**: AG-3I-1-1 — Monotonic Time Provider (centralización + contrato)  
**Parent**: 3I.0 snapshot PASS @ 83349b217b3467ae091427e2733b6c42f1f408cc  
**Date**: 2026-01-12  
**Status**: ✅ PASS

## Summary

Extendido `engine/time_provider.py` para centralizar el acceso a tiempo con contrato definido:

- `now_utc()` → datetime tz-aware UTC
- `monotonic_ns()` → nanosegundos monotónicos para latencias
- `FrozenTimeProvider` para tests deterministas
- Singleton `get_time_provider()` / `set_time_provider()`

## Files Modified

| File | Change |
|------|--------|
| `engine/time_provider.py` | +155 lines: new methods, FrozenTimeProvider, SystemTimeProvider, singleton |
| `tests/test_time_provider_3I1.py` | NEW: 14 tests del contrato |

## Grep Analysis — Before/After

**Antes**: El grep por `time.time(`, `datetime.now(`, `perf_counter(`, `monotonic(` no encontró usos directos en código de métricas/latencias de negocio.

**Después**: No se reemplazaron usos existentes porque:

1. `MetricsCollector` ya usaba `time.monotonic` inyectable via `clock_fn`
2. Usos en tests son para validar "no blocking" (no métricas de negocio)
3. Usos en `loop_stepper`, `supervisor` son `time.sleep()` (no afectan métricas)

**Decisión**: El valor del ticket es establecer el contrato centralizado. El wiring será consumido en tickets futuros.

## Verification

```
pytest -q tests/test_time_provider_3I1.py → 14 passed
pytest -q → 579 passed, 10 skipped
git diff --stat → solo engine/time_provider.py (155+, 2-)
```

## DoD Checklist

- [x] `pytest -q` PASS
- [x] `pytest -q tests/test_time_provider_3I1.py` PASS
- [x] `git diff --stat` solo afecta archivos del scope
- [x] Commit con mensaje: `AG-3I-1-1: monotonic time provider`

## AUDIT_SUMMARY

**Ficheros modificados**:

- `engine/time_provider.py` — añadidos now_utc(), monotonic_ns(), FrozenTimeProvider, SystemTimeProvider, singleton

**Ficheros nuevos**:

- `tests/test_time_provider_3I1.py` — 14 tests del contrato

**Riesgos / Dudas**:

- Ninguno identificado. Cambio aditivo, backward-compatible.
