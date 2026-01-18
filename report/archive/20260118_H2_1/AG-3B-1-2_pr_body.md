# PR Description: Release 2J/3A Sync & Runner Enhancements

## Resumen

Esta release consolida los avances recientes de las fases 2J (End-to-End Synth Runner), 3A (Paper Trading Loop) y 3B (Repo Hygiene & Runner CLI). Unifica el trabajo pendiente en `main` y añade capacidades críticas de ejecución para CI.

## Cambios Principales

### 🚀 Nuevas Funcionalidades

- **Runner 2J (`tools/run_e2e_2J.py`)**: Implementado soporte para `--mode quick` (smoke test para CI) y `--mode full` (suite completa).
- **Paper Trading Loop (3A)**: Simulador de bucle de papel (`tools/run_paper_loop_3A.py`) con métricas de observabilidad y manejo de eventos.
- **Event Contracts (3A)**: Definición formal de contratos de eventos y validación.

### 🛠️ Mantenimiento y Calidad

- **Hygiene (3B.0)**: Limpieza de repositorio, ignorando artefactos locales (`configs/best_params_2H.json`, `report/dashboard_2J/`, etc.) sin borrarlos.
- **Tests**: Nuevos tests de CLI para el runner (`tests/test_e2e_runner_2J.py`) y cobertura para 3A.
- **Observabilidad**: Normalización de razones de rechazo y métricas de latencia p95.

## Verificación

- **Tests**: `pytest -q` pasando (198 passed).
- **Manual**:
  - `python tools/run_e2e_2J.py --mode quick --dry-run` verificado.
  - `python tools/run_e2e_2J.py --mode full --dry-run` verificado.

## Riesgos y Notas
>
> [!CAUTION]
> **Entorno Python**: Se ha detectado un entorno dual (WSL Python 3.12 vs Windows Python 3.13). El runner canónico debe ejecutarse en WSL (3.12). Evitar ejecutar en Windows nativo para prevenir discrepancias en `multiprocessing` o pickling.

## Checklist

- [x] Rama de release creada y limpia.
- [x] Tests unitarios y de integración pasando.
- [x] Artefactos locales añadidos a `.gitignore`.
- [x] CLI de Runner validado con nuevos tests.
