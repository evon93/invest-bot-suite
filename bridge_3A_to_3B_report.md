# Bridge Report: Phase 3A to 3B

**Date**: 2026-01-03
**Status**: 3A COMPLETE
**Current Head**: `95745b2` (3A.3: harden rejection reason aggregation + alias)
**Branch**: `main`

## 1. Estado Actual (Phase 3A Complete)

La fase 3A ("Paper Trading Loop") ha establecido la infraestructura para la simulación de trading basada en eventos y la observabilidad básica.

### Adiciones Clave en 3A

1. **Contratos Event-Driven (v1)**:
    - `contracts/event_messages.py`: `OrderIntent`, `RiskDecision`, `ExecutionReport`, `ExecutionContext`.
    - Serialización estricta y validación de campos obligatorios.
2. **Paper Worker / Simulator**:
    - `tools/run_paper_loop_3A.py`: Simulador que consume señales NDJSON, valida riesgo (v0.4) y genera fills/rejects.
    - Soporta latencia simulada y slippage determinista (seed 42).
3. **Observabilidad Básica**:
    - Métricas financieras: `max_drawdown_pct`, `max_gross_exposure_pct`.
    - Métricas operativas: `active_rate`, `latency_ms_p95`.
    - Razones de rechazo normalizadas y aliased (`rejected_by_reason`).
    - `trace_id` propagado end-to-end.

## 2. Ejecución de Smoke Test (WSL)

El simulador se puede ejecutar localmente para validar la lógica y generar trazas.

```bash
# Smoke Test con señales de ejemplo
wsl -e bash -lc "cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite && source .venv/bin/activate && python tools/run_paper_loop_3A.py --signals examples/signals_3A.ndjson --risk-config configs/risk_rules_prod.yaml --outdir report/runs/3A_paper_smoke --max-events 20 --seed 42"
```

### Outputs Esperados

- `report/runs/3A_paper_smoke/events.ndjson`: Traza completa de eventos (Intent -> Decision -> Report).
- `report/runs/3A_paper_smoke/metrics.json`: Resumen de métricas de ejecución.

## 3. Checklist Previo a 3B (Live Integration)

La fase 3B conectará este loop con datos reales y sistemas de ejecución (simulados o reales).

- [ ] **Data Feeds**: Reemplazar NDJSON estático por feed de precios (histórico/live).
- [ ] **Strategy Integration**: Conectar `Strategy Engine` real para emitir `OrderIntent`.
- [ ] **Execution Adapter**: Implementar adaptador para broker real (o simulador de exchange más complejo).
- [ ] **Latencia Real**: Medir latencia real del sistema (no solo mock sleep).

## 4. Referencias

- **Contracts**: [contracts/event_messages.py](contracts/event_messages.py)
- **Runner**: [tools/run_paper_loop_3A.py](tools/run_paper_loop_3A.py)
- **Tests**: `tests/test_contracts_3A.py`, `tests/test_paper_loop_3A.py`
