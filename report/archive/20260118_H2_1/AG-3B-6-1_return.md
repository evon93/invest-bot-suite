# AG-3B-6-1 Return Packet — CI Smoke 3B

## Resumen

Se ha añadido el workflow `.github/workflows/smoke_3B.yml` para validar la integración de la fase 3B en cada push/PR.

## Detalles del Workflow

- **Trigger**: Push/PR a main.
- **Entorno**: Ubuntu Latest, Python 3.12 (standard CI).
- **Pasos**:
  1. Setup Python 3.12 & Install requirements.
  2. **Pytest Gate**: Ejecuta tests unitarios y de integración (`tests/test_run_live_integration_3B.py`).
  3. **Data Gen**: Genera datos sintéticos OHLCV en vivo (via python one-liner).
  4. **Integrated Runner**: Ejecuta `tools/run_live_integration_3B.py` (Loader->Strat->Risk->Exec).
  5. **Verification**: Asegura que se genere `events.ndjson`.
  6. **Artifacts**: Sube el log de eventos generado.

## Por qué Ubuntu

Se eligió `ubuntu-latest` como entorno de ejecución por ser el estándar más rápido y predecible en GitHub Actions, evitando la sobrecarga de windows-latest, dado que el código es agnóstico del SO (paths manipulados con `pathlib`).

## Reproducción Local

Para simular lo que hace el CI localmente:

1. `pip install -r requirements.txt`
2. `python -m pytest tests/test_run_live_integration_3B.py -q`
3. Ejecutar comando manual del runner (ver `AG-3B-6-1_run.txt` o step del workflow).

## Archivos Entregados

- `.github/workflows/smoke_3B.yml`: Definición del workflow.
- `report/AG-3B-6-1_diff.patch`: Patch incluye el workflow.
