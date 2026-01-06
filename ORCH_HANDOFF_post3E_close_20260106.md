# Handoff Report: Phase 3E (Unified Live Runner)

**Fecha**: 2026-01-06
**Versión**: 1.0
**Estado**: RELEASE CANDIDATE

## 1. Contexto y Objetivos

La **Fase 3E** tuvo como objetivo consolidar la ejecución del bot en un entorno "live-like" determinista. Se buscaba eliminar la fragmentación de scripts de arranque y establecer una base sólida para la ejecución en real (Phase 3F) mediante la inyección de dependencias (`TimeProvider`, `ExchangeAdapter`).

**Principales Logros**:

- **Unified Runner**: `tools/run_live_3E.py` que soporta modos `simulated` y `real` via flags.
- **Determinismo**: Gate automático (`tools/check_determinism_3E.py`) que asegura que re-runs con la misma seed produzcan artefactos idénticos.
- **Abstracción de Exchange**: `ExchangeAdapter` (Paper/Stub) permite simular latencia de red controlada.
- **Observabilidad**: Evento interno `position_changed` para trazar el estado de la posición tras cada fill.
- **CI**: Workflow `smoke_3E.yml` integrado para validar determinismo en cada push.

## 2. Cambios Realizados

| Ticket | Componente | Descripción |
|---|---|---|
| **3E.1** | `TimeProvider` | Interfaces `SimulatedTimeProvider` y `RealTimeProvider` inyectadas en `LoopStepper`. |
| **3E.2** | `ExchangeAdapter` | Protocolo `ExchangeAdapter` y implementaciones `Paper` (instant fill) y `StubNetwork` (latency). Refactor de `ExecWorker` para usar adaptador. |
| **3E.3** | `run_live_3E.py` | Script unificado que orquesta la simulación. Genera artifacts (`events.ndjson`, `results.csv`, `state.db`). Docs y Smoke Tests incluidos. |
| **3E.3 (Fix)** | Smoke Test | Ajuste de expectativas de columnas en `results.csv` para mayor robustez. |
| **3E.4** | Determinism Gate | `check_determinism_3E.py` compara dos corridas y valida hash SHA256 de outputs (ignorando timestamps volátiles). Integrado en CI. |
| **3E.5** | `PositionStore` | Emisión del evento `position_changed` (internal logic) para cerrar gap de observabilidad. |

## 3. Evidencias de Calidad (DoD)

- **Unit & Regression Tests**: `pytest` suite passing (incluyendo tests de workers y determinismo).
- **Determinism Gate**: Validado manual y automáticamente que `run_live_3E` es determinista bajo `--clock simulated --seed 42`.
- **Smoke Tests**: El runner genera todos los artefactos esperados (`events.ndjson`, `results.csv`, `run_meta.json`, `state.db`).
- **CI**: Workflow configurado para proteger la integridad del runner ante futuros cambios.

## 4. Riesgos y Deuda Técnica

- **Librerías**: Warnings de depreciación en `numpy` y `pandas` (observados en logs de pytest) deben ser limpiados en tareas de mantenimiento.
- **Performance**: El modo `simulated` es rápido, pero `StubNetworkExchangeAdapter` con latencia alta podría ralentizar tests si se usa indiscriminadamente.
- **Logging**: El volumen de logs en `trace` puede crecer rápidamente; evaluar rotación o filtrado para corridas largas (Phase 3F).

## 5. Instrucciones para Orchestrator

1. **Ejecución Standard**:

   ```bash
   python tools/run_live_3E.py --outdir report/live_sim --clock simulated --exchange paper --seed 42
   ```

2. **Verificación Determinismo**:

   ```bash
   python tools/check_determinism_3E.py --outdir-a report/det_a --outdir-b report/det_b --seed 123
   ```
