# AG-3G-3-1 Notes

## Diseño

### MetricsCollector

- API: `start(msg_id)`, `end(msg_id, status, reason, retry_count, dupe)`
- Clock inyectable: `clock_fn` (default=time.monotonic)
- Contadores: processed, allowed, rejected, filled, errors, retries, dupes_filtered
- Latencias: lista con percentiles (p50, p95) calculados con empty-set safety
- Error/reject breakdown por reason

### MetricsWriter

- File-first: `metrics.ndjson` (append) + `metrics_summary.json` (final)
- No-op mode si run_dir=None
- Determinismo: JSON keys sorted

### NoOpMetricsCollector

- Fallback para cuando observability está deshabilitada
- Zero overhead

## Wiring Mínimo

El wiring en run_live_3E.py es opcional para este ticket. El core está implementado y testeado.

Para wiring futuro:

```python
from engine.metrics_collector import MetricsCollector, MetricsWriter

collector = MetricsCollector()
writer = MetricsWriter(run_dir=args.run_dir) if args.run_dir else MetricsWriter()

# En el loop:
collector.start(msg_id)
# ... procesar ...
collector.end(msg_id, status="FILLED")

# Al final:
writer.write_summary(collector.snapshot_summary())
```

## Tests

- test_metrics_collector_v0.py: 16 tests (counters, latency, percentiles, reset)
- test_metrics_writer_filefirst.py: 9 tests (ndjson, summary, no-op, persistence)
