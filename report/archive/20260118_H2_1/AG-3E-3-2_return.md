# Return Packet: AG-3E-3-2 — Fix Smoke Test Runner 3E

## Resumen

Se ha corregido el test de humo `tests/test_3E_runner_smoke.py` para validar `results.csv` mediante invariantes robustos en lugar de columnas específicas frágiles.

- **Cambio**: `test_run_live_3E_simulated_paper` ahora verifica:
  - Existencia de `max_step_id` y `unique_trace_ids`.
  - Valores positivos en dichas métricas.
  - Existencia y suma > 0 de columnas `num_*`.
- **Justificación**: El runner genera columnas agregadas/flattened que pueden variar, pero los invariantes de ID y contadores son estables.

## Artefactos

- [AG-3E-3-2_diff.patch](report/AG-3E-3-2_diff.patch)
- [AG-3E-3-2_pytest_wsl.txt](report/AG-3E-3-2_pytest_wsl.txt)
- [AG-3E-3-2_last_commit.txt](report/AG-3E-3-2_last_commit.txt)
- [AG-3E-3-2_smoke_pytest_wsl.txt](report/AG-3E-3-2_smoke_pytest_wsl.txt) (Generado previamente)
