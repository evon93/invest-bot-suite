# Return Packet: AG-3E-3-1 — Runner Unificado 3E

## Resumen

Se ha introducido el runner unificado `tools/run_live_3E.py` para estandarizar la ejecución "live-like" en Phase 3C/3E.

- **Herramienta**: `tools/run_live_3E.py`
  - Flags: `--clock (simulated|real)`, `--exchange (paper|stub)`, `--seed`, `--outdir`.
  - Default: Determinista (`simulated`, `paper`, `seed=42`).
  - Artefactos: `events.ndjson`, `run_meta.json`, `results.csv`, `state.db`.
- **Tests**:
  - `tests/test_3E_runner_smoke.py`: Verifica la ejecución end-to-end con defaults y modo stub.

## Artefactos

- [AG-3E-3-1_diff.patch](report/AG-3E-3-1_diff.patch)
- [AG-3E-3-1_pytest_wsl.txt](report/AG-3E-3-1_pytest_wsl.txt)
- [AG-3E-3-1_smoke_pytest_wsl.txt](report/AG-3E-3-1_smoke_pytest_wsl.txt)
- [AG-3E-3-1_run.txt](report/AG-3E-3-1_run.txt)
- [AG-3E-3-1_last_commit.txt](report/AG-3E-3-1_last_commit.txt)
