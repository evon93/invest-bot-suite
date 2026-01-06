# Orchestrator Handoff Report — Phase 3D: Traceable Bus & Workers

**Fecha**: 2026-01-05  
**Estado**: ✅ COMPLETADO  
**Rama**: `feature/3C_7_close` (incluye 3D) -> `main`  
**Autor**: Antigravity (Agent)

---

## 1. Contexto y Baseline

La Fase 3D ha transformado el sistema de un bucle monolítico a una arquitectura **Event-Driven Bus Mode**. Se han introducido Workers desacoplados (`RiskWorker`, `ExecWorker`, `PositionStoreWorker`) que se comunican exclusivamente vía `InMemoryBus`.

Objetivos clave logrados:

- **Traceability**: Cada evento tiene `trace_id` y `ref_event_id`, permitiendo traza completa (Intent -> Decision -> Report -> Fill).
- **Log Estructurado (JSONL)**: Logs deterministas sin timestamps, parseables automáticamente.
- **Fail-Fast**: Configuración estricta de riesgo y manejo de cache misses en ejecución.

---

## 2. Entregables por Ticket (3D.1 – 3D.6)

| Ticket | Commit | Descripción | Artefactos Clave |
|--------|--------|-------------|------------------|
| **3D.6** | `edf0f45` | **Canonical CI Runner** + Smoke Test. Consolidación del flujo 3D. | `tools/run_3D_canonical.py`<br>`tests/test_3D_canonical_smoke.py` |
| **3D.5** | `a6c10e5` | **Deterministic Metrics**. Recolección de métricas desde logs JSONL. | `engine/run_metrics_3D5.py`<br>`report/out_3D5_metrics/trace.jsonl` |
| **3D.4** | `e120a20` | **JSONL Logging + Fail-Fast**. Logs estructurados y fix de defaults peligrosos en Exec. | `engine/structured_jsonl_logger.py`<br>`engine/bus_workers.py` |
| **3D.3** | `47876c9` | **Workers & Stepper**. Implementación de workers y modo bus en LoopStepper. | `engine/bus_workers.py`<br>`engine/loop_stepper.py` |
| **3D.2** | `43e6e01` | **In-Memory Bus**. Abstracción de bus síncrono para tests/simulación. | `bus/inmemory_bus.py`<br>`bus/base.py` |
| **3D.1** | `fed004c` | **Risk Rules Loader**. Carga estricta y validación de `risk_rules.yaml`. | `risk_rules_loader.py`<br>`tests/test_risk_rules_loader.py` |

---

## 3. Guía de Ejecución

Todos los comandos asumen:

- WSL Ubuntu
- `.venv` activo (`source .venv/bin/activate`)
- CWD: raíz del repositorio

### 3.1. Tests Automáticos (Deterministas)

Ejecutar la suite completa (incluye smoke tests 3D):

```bash
python -m pytest -q
```

*Expected: > 350 tests passed.*

### 3.2. Runner Canónico 3D

Ejecución manual para generar artefactos de trazabilidad:

```bash
python tools/run_3D_canonical.py \
  --outdir report/out_handover_3D \
  --seed 42 \
  --max-steps 100 \
  --num-signals 5
```

**Salida Generada (`report/out_handover_3D/`)**:

- `trace.jsonl`: Log estructurado evento a evento.
- `run_metrics.json`: Métricas de ejecución (conteos, fills, etc.).
- `run_meta.json`: Metadatos del entorno y configuración.
- `state.db`: Base de datos SQLite (posiciones).

---

## 4. Invariantes & Guardrails

1. **Determinismo Absoluto**: El runner 3D y los logs JSONL **NO** contienen timestamps reales ni dependen del reloj del sistema. Todo se basa en pasos (`step_id`) y semillas fijas.
2. **Fail-Fast en Riesgo**: `risk_rules_loader` lanza excepción si `risk_rules.yaml` es inválido o falta (con `strict=True`).
3. **Atomicidad de Datos**: `ExecWorker` falla (`ValueError`) si intenta procesar una orden sin tener los datos originales en caché (no inventa precios/cantidades).

---

## 5. Deuda Técnica & Riesgos Abiertos

1. **Dualidad de Runners**: Existen `tools/run_live_integration_3B.py` (antiguo) y `tools/run_3D_canonical.py` (nuevo). Fase 3E debe unificarlos o migrar 3B al bus.
2. **Logs de Rebalanceo**: En 3D, el rebalanceo mensual de `Strategy` aún no emite eventos al bus, solo las señales de trading normales.
3. **PositionStore Limitado**: `PositionStoreWorker` solo escribe en SQLite. No publica eventos `PositionChanged` al bus (futuro: para UI/monitoring en tiempo real).
4. **Risk Shim**: Se sigue usando `RiskManagerV0_4_Shim`. Versiones futuras deberían usar RiskManager v0.6 nativo si está listo.

---

## 6. Recomendaciones para Fase 3E (Live Integration)

Prioridad sugerida para la siguiente fase:

1. **3E.1: Live Clock Adapter**. Crear un `TimeProvider` que pueda ser "Simulated" (para tests/3D) o "Real" (para 3E).
2. **3E.2: Exchange Adapter (IBKR/Paper)**. Implementar un `ExecWorker` que hable con la API real (o stub de red) en lugar de simulación inmediata.
3. **3E.3: Unified Live Runner**. Crear `tools/run_live_3E.py` que inyecte reloj real y adaptador de exchange, reutilizando el mismo `LoopStepper` y Bus.
