# Return Packet: AG-3E-4-1 — Determinism Gate 3E

## Resumen

Se ha implementado un gate de determinismo para el runner 3E (`tools/run_live_3E.py`) que ejecuta el simulador dos veces y compara los artefactos generados.

- **Herramienta**: `tools/check_determinism_3E.py`
  - Compara `results.csv` y `events.ndjson` mediante hash SHA256.
  - Compara `run_meta.json` ignorando campos volátiles (`timestamp_start`).
- **Tests**: `tests/test_3E_determinism_gate.py` envuelve el checker para ejecución automática en CI.

## Verificación

El test ha confirmado que configuraciones idénticas producen salidas binarias idénticas (salvo timestamps ignorados).

## Artefactos

- [AG-3E-4-1_diff.patch](report/AG-3E-4-1_diff.patch)
- [AG-3E-4-1_pytest_wsl.txt](report/AG-3E-4-1_pytest_wsl.txt)
- [AG-3E-4-1_last_commit.txt](report/AG-3E-4-1_last_commit.txt)
- [AG-3E-4-1_run.txt](report/AG-3E-4-1_run.txt)
