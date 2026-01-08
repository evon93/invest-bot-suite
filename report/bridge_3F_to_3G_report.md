# Bridge Report: 3F → 3G

**Origen**: Phase 3F — Live Execution Readiness  
**Destino**: Phase 3G — [Pending Definition]  
**Fecha**: 2026-01-08

---

## Estado Final 3F

| Criterio | Estado |
|----------|--------|
| Runtime config fail-fast | ✅ PASS |
| Retry/backoff determinista | ✅ PASS |
| Idempotencia (in-memory + file) | ✅ PASS |
| Real-ish adapter gated | ✅ PASS |
| Crash recovery checkpoint | ✅ PASS |
| CI gates smoke_3F | ✅ PASS |
| Pytest | 432 passed, 10 skipped |
| Determinism | MATCH |

---

## Pendientes Recomendados para 3G

### Alta Prioridad

1. **CCXT Sandbox Integration**
   - Implementar `CcxtSandboxAdapter` para pruebas con exchange real
   - Requiere manejo de rate limits y errores de API

2. **Distributed Idempotency Store**
   - Migrar de `FileIdempotencyStore` a Redis/DB para escalabilidad
   - Necesario si se ejecutan múltiples workers

### Media Prioridad

1. **Observability**
   - Métricas Prometheus para latencia, errores, retries
   - Dashboard Grafana para monitoreo

2. **Alerting**
   - Notificaciones Slack/Discord en fallos críticos
   - Alertas por exhaustion de retries

### Baja Prioridad

1. **Multi-symbol Support**
   - Paralelizar ejecución por símbolo
   - Requiere refactor del bus

---

## Archivos Clave Heredados

| Archivo | Función |
|---------|---------|
| `engine/runtime_config.py` | Configuración y validación |
| `engine/retry_policy.py` | Política de reintentos |
| `engine/idempotency.py` | Stores de idempotencia |
| `engine/checkpoint.py` | Checkpoint atómico |
| `engine/exchange_adapter.py` | Adapters (Paper, Stub, Realish) |
| `tools/run_live_3E.py` | Runner principal |

---

## Notas de Transición

- Los contracts V1 (`OrderIntentV1`, `RiskDecisionV1`, `ExecutionReportV1`) no fueron modificados
- El `RiskManager` y sizing/stops permanecen intactos
- CI gates `smoke_3E.yml` y `smoke_3F.yml` coexisten
