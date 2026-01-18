# Return Packet: AG-3E-5-1 — Position Changed Event

## Resumen

Se ha implementado la emisión del evento interno `position_changed` en `PositionStoreWorker`. Este evento cierra el gap de observabilidad permitiendo trazar el estado de la posición (net quantity, avg price) después de cada fill.

- **Módulo modificado**: `engine/bus_workers.py`
  - Método `PositionStoreWorker._process_one`
  - Emite `position_changed` usando `jsonl_logger` si está configurado.
  - Payload: `symbol`, `qty`, `avg_px`, `step_id`.
  - Determinismo: Usa `step_id` del worker (`processed_count`).
- **Tests**: `tests/test_position_changed_emission.py` verifica la presencia del evento en el stream NDJSON.

## Verificación

- Smoke test específico pasó.
- Regresión completa (`pytest -q`) pasó.
- Determinismo mantenido (verificado por `run_live_3E` execution).

## Artefactos

- [AG-3E-5-1_diff.patch](report/AG-3E-5-1_diff.patch)
- [AG-3E-5-1_pytest_wsl.txt](report/AG-3E-5-1_pytest_wsl.txt) (Regresión)
- [AG-3E-5-1_smoke_pytest_wsl.txt](report/AG-3E-5-1_smoke_pytest_wsl.txt) (Smoke)
- [AG-3E-5-1_run.txt](report/AG-3E-5-1_run.txt) (Manual Run)
- [AG-3E-5-1_last_commit.txt](report/AG-3E-5-1_last_commit.txt)
