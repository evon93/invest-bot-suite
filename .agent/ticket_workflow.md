# Ticket Workflow (InvestBot Suite)

Este documento define el flujo operativo mínimo para ejecutar tickets (AG / DS) con trazabilidad, reproducibilidad y "offline-first".

## 1) Roles y responsabilidades

- **ORCHESTRATOR**: diseña el plan (pasos, DoD, evidencias, riesgos).
- **EXECUTOR (humano)**: ejecuta comandos localmente, adjunta outputs, valida que DoD se cumple.
- **ANTIGRAVITY (implementer)**: implementa cambios en el repo según ticket, crea return packet + evidencias.
- **AUDITOR (DS)**: revisa invariantes, flakiness, compatibilidad, y coherencia del cambio.

## 2) Invariantes (NO negociables)

- No romper contracts existentes.
- CI y tests "offline-first" (sin red por defecto).
- Determinismo donde aplique (seed 42 si el módulo lo usa).
- No introducir dependencias externas obligatorias sin ticket explícito.
- No comandos destructivos sin confirmación (rm, reset --hard, force push, etc.).

## 3) Convención de tickets

Formato: `AG-<FASE>-<PASO>-<SUBPASO>` (ej: AG-H2-4-1).  
Cada ticket debe producir:

- 1 commit (ideal) con mensaje: `<fase>.<paso>: <resumen> (<ticket>)`
- 1 return packet en `report/`

## 4) Return Packet (mínimo)

Archivo: `report/<TICKET>_return.md`

Debe incluir:

- Metadata (ticket, fecha, status PASS/FAIL, objetivo)
- Baseline (branch + HEAD antes)
- Cambios (archivos tocados + resumen)
- Verificación (pytest u otras gates) + resultado
- Lista de artefactos generados

## 5) Evidencias (naming)

- `report/<TICKET>_last_commit.txt`
- `report/<TICKET>_diff.txt`  (nota: si `*.patch` está ignorado, usar `.diff.txt`)
- `report/<TICKET>_pytest_full.txt` (si aplica)
- `report/<TICKET>_git_status_after.txt`

Regla: toda evidencia que soporte un claim del return packet debe estar referenciada.

## 6) Comunicación y handoff

- El EXECUTOR puede pegar directamente outputs sin "delta".
- Si hay ambigüedad o trade-off, documentarlo como:
  - Hecho / Decisión / Alternativas descartadas / Riesgo.

## 7) Closeout de fase (cuando aplique)

Entregables típicos:

- `report/ORCH_HANDOFF_post<FASE>_close_<YYYYMMDD>.md`
- `report/bridge_<FASE>_to_next_report.md`
- `registro_de_estado_invest_bot.md` actualizado
- `report/pytest_<FASE>_closeout.txt`
