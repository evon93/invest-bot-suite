# AG-3H-4-1 Return Packet

## Objetivo

Supervisor 24/7 como wrapper de run_live_3E.py con reinicio automático y backoff determinista.

## Baseline

- **Branch**: main
- **HEAD antes**: cdc4e88
- **Fecha**: 2026-01-10

## Implementación

### Script: `tools/supervisor_live_3E_3H.py`

**CLI:**

```
--run-dir <path>         # Directorio para state/logs
--max-restarts <int>     # Máximo restarts (default: unlimited)
--backoff-base-s <float> # Base backoff (default: 0.5)
--backoff-cap-s <float>  # Cap backoff (default: 30)
--log-file <path>        # Log file (default: run-dir/supervisor.log)
-- <child command>       # Comando a supervisar
```

**Backoff determinista:**

```
delay = min(cap, base * 2^attempt)
```

Sin jitter para determinismo.

**State persistido:** `supervisor_state.json`

- attempt, last_exit_code, last_exit_ts, next_delay_s, cmdline, config

**Log append-only:** `supervisor.log`

- Timestamps UTC ISO
- Start/restart/exit events

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `tools/supervisor_live_3E_3H.py` | [NEW] Supervisor class con restart loop |
| `tests/test_supervisor_3H.py` | [NEW] 11 tests con mock subprocess/sleep |

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest -q | **PASS** (520 passed, 10 skipped) |
| tests supervisor | **11/11 PASS** |
| smoke | **OK** (1 fail + restart + success) |

## Artefactos Smoke (report/out_3H4_supervisor_smoke/)

```
supervisor_state.json  - attempt=2, last_exit_code=0
supervisor.log         - 7 líneas de log
_ran_once              - marker file del child
```

**Evidencia de reinicio:**

```
[...] Starting child (attempt 1)...
[...] Child exited with code 1. Restarting in 0.10s...
[...] Starting child (attempt 2)...
[...] Child exited cleanly (code 0). Supervisor stopping.
```

## DOD Status: **PASS**

- [x] pytest -q PASS
- [x] Script supervisor operativo
- [x] Evidencia smoke (state+log)
- [x] Sin cambios fuera de scope
