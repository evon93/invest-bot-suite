# AG-3G-3-1 Return Packet

**Ticket**: AG-3G-3-1 — Observability v0 File-First Metrics  
**Status**: ✅ PASS  
**Branch**: `feature/AG-3G-3-1_observability_v0`  
**Commit**: `65538ad`

---

## Baseline

| Campo | Valor |
|-------|-------|
| Branch base | `feature/AG-3G-2-2_wire_sqlite_backend` |
| HEAD base | `b0a4e8d` |

---

## Implementación

### engine/metrics_collector.py

| Clase | API |
|-------|-----|
| `MetricsCollector` | `start(msg_id)`, `end(msg_id, status, reason, retry_count, dupe)`, `snapshot_summary()` |
| `MetricsWriter` | `append_event(payload)`, `write_summary(summary)`, `close()` |
| `NoOpMetricsCollector` | Zero-overhead fallback |

### Features

- Clock inyectable para tests deterministas
- Contadores: processed, allowed, rejected, filled, errors, retries, dupes_filtered
- Latencias: p50, p95 con empty-set safety (return None)
- Error/reject breakdown por reason
- File-first: `metrics.ndjson` (append) + `metrics_summary.json`

---

## Tests

| Suite | Estado |
|-------|--------|
| pytest WSL global | 475 passed, 10 skipped ✅ |
| test_metrics_collector_v0.py | 16 passed ✅ |
| test_metrics_writer_filefirst.py | 9 passed ✅ |

---

## Ejemplo Output

```json
// metrics_summary.json
{
  "allowed": 42,
  "dupes_filtered": 0,
  "errors": 2,
  "errors_by_reason": {"timeout": 2},
  "filled": 40,
  "latency_count": 44,
  "latency_p50_ms": 15.5,
  "latency_p95_ms": 45.2,
  "processed": 50,
  "rejected": 6,
  "rejects_by_reason": {"max_position": 4, "dd_guardrail": 2},
  "retries": 5
}
```

---

## AUDIT_SUMMARY

**Paths tocados**:

- `engine/metrics_collector.py` (A)
- `tests/test_metrics_collector_v0.py` (A)
- `tests/test_metrics_writer_filefirst.py` (A)
- `report/AG-3G-3-1_*.{md,txt,patch}` (A)

**Cambios clave**: MetricsCollector + MetricsWriter file-first.

**Resultado**: PASS.
