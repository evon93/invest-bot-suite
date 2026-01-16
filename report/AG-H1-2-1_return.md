# AG-H1-2-1 Return Packet

**Status**: ✅ PASS  
**Timestamp**: 2026-01-16T16:02:00+01:00

## Objetivo

Exit code 0 SOLO en shutdown controlado (SIGINT/SIGTERM). Fallos reales → exit != 0.

## Cambios Realizados

### [run_live_3E.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_live_3E.py)

- Añadido tracking de `exit_code` variable (línea 571)
- En `except Exception`: si NO es `stop_requested`, log `Fatal error` y `exit_code = 2`
- Cambiado `sys.exit(1)` a `return 1` para trace file missing
- Añadido `return exit_code` al final de `main()`
- Cambiado entrypoint a `sys.exit(main())`

### [test_exit_codes_h1.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_exit_codes_h1.py) [NEW]

5 tests:

- `test_missing_fixture_path_exits_nonzero` → exit != 0 ✓
- `test_nonexistent_fixture_exits_nonzero` → exit != 0 ✓
- `test_sigint_exits_zero` → exit 0 (skip Windows) ✓
- `test_sigterm_exits_zero` → exit 0 (skip Windows) ✓
- `test_normal_run_exits_zero` → exit 0 ✓

## Verificación

### Pytest Focalizado

```
python -m pytest -q tests/test_exit_codes_h1.py tests/test_graceful_shutdown_signal_3O2.py tests/test_graceful_shutdown_supervisor_3O2.py
→ 8 passed in 40.07s
```

### Pytest Completo

```
python -m pytest -q
→ 737 passed, 11 skipped in 198.69s
```

## Artefactos

- [AG-H1-2-1_return.md](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/report/AG-H1-2-1_return.md)
- [pytest_H1_2_1_focus.txt](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/report/pytest_H1_2_1_focus.txt)
- [pytest_H1_2_1_full.txt](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/report/pytest_H1_2_1_full.txt)

## AUDIT_SUMMARY

**Ficheros modificados**:

- `tools/run_live_3E.py` (exit code semantics)

**Ficheros creados**:

- `tests/test_exit_codes_h1.py` (5 tests nuevos)
- `report/pytest_H1_2_1_focus.txt`
- `report/pytest_H1_2_1_full.txt`
- `report/AG-H1-2-1_return.md`

**Cambios funcionales**: Exit code explícito (0=success/shutdown, 2=error)

**Riesgos**: Ninguno - backward compatible con tests existentes
