# AG-3B-1-1 Return Packet — Runner 2J Modes

## Resumen

Se ha implementado la funcionalidad `--mode quick|full` en el runner sintético `tools/run_e2e_2J.py`.

- **Mode Quick** (default): Ejecuta una calibración rápida (smoke) mapeando a `run_calibration_2B.py --mode quick`.
- **Mode Full**: Ejecuta la suite completa mapeanda a `run_calibration_2B.py --mode full_demo`.
- **Tests**: Se añadió `tests/test_e2e_runner_2J.py` para verificar el mapeo de argumentos y la integridad del CLI.

## Cambios

- `tools/run_e2e_2J.py`: Añadido argumento `--mode` y lógica de selección de paso de calibración.
- `tests/test_e2e_runner_2J.py`: Nueva suite de tests para el runner (cubre help y dry-runs de ambos modos).

## Verificación

- **Pytest**: `tests/test_e2e_runner_2J.py` pasó exitosamente (3 tests).
- **Manual**: Dry-run verificado en logs.

## Archivos

- `report/AG-3B-1-1_diff.patch`: Diff de los cambios.
- `report/AG-3B-1-1_pytest.txt`: Salida de pytest.
- `report/AG-3B-1-1_run.txt`: Log de comandos.
