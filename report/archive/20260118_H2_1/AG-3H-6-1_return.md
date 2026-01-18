# AG-3H-6-1 Return Packet

## Objetivo

Añadir CI smoke_3H (GitHub Actions) para validar wiring end-to-end de métricas, rotación y dashboard.

## Baseline

- **Branch**: main
- **HEAD antes**: 3e3a9ab
- **Fecha**: 2026-01-10

## Implementación

### Workflow: `.github/workflows/smoke_3H.yml`

**Triggers:**

- push: main, develop, feature/*
- pull_request: main, develop
- workflow_dispatch

**Jobs:**

1. Setup Python 3.12 con cache pip
2. Install dependencies
3. Run pytest -q (full suite)
4. **Smoke run_live_3E** con:
   - `--enable-metrics`
   - `--metrics-rotate-max-lines 5`
   - `--max-steps 25`
   - `--clock simulated --exchange paper --seed 42`
5. **Render dashboard** con:
   - `--run-dir ${RUN_DIR}`
   - `--tail-lines 500`
6. **Verify artifacts**:
   - metrics_summary.json exists
   - dashboard.html exists
7. **Upload artifacts** (always)

**Duración estimada:** < 2 min (25 steps + pytest)

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `.github/workflows/smoke_3H.yml` | [NEW] CI workflow smoke_3H |

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest 3H tests | **PASS** (38 passed) |
| workflow syntax | **OK** (YAML válido) |
| --max-steps | Ya existe en run_live_3E.py |

## Notas CI

No fue necesario añadir flag --max-steps porque ya existía en run_live_3E.py (usado en smoke_3G.yml).

El workflow usa:

- `metrics-rotate-max-lines 5` para forzar rotación con 25 steps
- `tail-lines 500` en dashboard (suficiente para smoke)
- seed 42 para determinismo

## DOD Status: **PASS**

- [x] Workflow smoke_3H creado
- [x] Genera artifacts (metrics + dashboard)
- [x] Upload artifacts configurado
- [x] pytest -q PASS
