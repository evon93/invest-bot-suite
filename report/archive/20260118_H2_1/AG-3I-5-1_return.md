# AG-3I-5-1: CI Workflow Smoke 3I - Return Packet

## Resumen

Creado workflow de GitHub Actions `smoke_3I.yml` para validar end-to-end las nuevas funcionalidades de la fase 3I:

- Ejecución con métricas habilitadas y rotación (keep=2).
- Generación de Dashboard v1.
- Verificación de existencia de artefactos y rotación correcta.

## Workflow Detalles

**Archivo:** `.github/workflows/smoke_3I.yml`
**Trigger:** Push/PR en main/develop/feature/*
**Pasos:**

1. Setup Python 3.12
2. Install deps (pytest, etc.)
3. `pytest -q`
4. `tools/run_live_3E.py` con:
   - `--enable-metrics`
   - `--metrics-rotate-max-lines 5`
   - `--metrics-rotate-keep 2`
   - `--max-steps 25`
   - `--seed 42`
5. `tools/render_metrics_dashboard_3H.py`
6. Verificación de artefactos (existencia de dashboard.html, metrics_summary.json, rotated ndjson).
7. Upload Artifacts.

## Verificación Local

No se puede ejecutar GHA localmente sin herramientas externas, pero se ha verificado:

- Sintaxis YAML válida (inspección visual vs `smoke_3H.yml`).
- Argumentos CLI de `run_live_3E.py` y `render_metrics_dashboard_3H.py` coinciden con `help`.

## Instrucciones para User

1. Push de la rama `feature/AG-3I-5-1_smoke_ci_3I`.
2. Verificar en GitHub Actions que el job `smoke-3i` aparece y termina en verde.
3. Verificar duración < 5 min (debería ser muy rápido, ~1-2 min).

## Baseline

- Branch: `feature/AG-3I-5-1_smoke_ci_3I`
