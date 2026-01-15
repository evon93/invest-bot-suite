# AG-3G-3-2 Return Packet

**Ticket**: AG-3G-3-2 — Wire MetricsCollector into run_live_3E  
**Status**: ✅ PASS  
**Branch**: `feature/AG-3G-3-2_wire_metrics_loop`  
**Commit**: `57feb13`

---

## Baseline

| Campo | Valor |
|-------|-------|
| Branch base | `feature/AG-3G-3-1_observability_v0` |
| HEAD base | `5abb647` |

---

## Implementación

### tools/run_live_3E.py

| Cambio | Descripción |
|--------|-------------|
| Import | +`MetricsCollector, MetricsWriter, NoOpMetricsCollector` |
| CLI arg | `--enable-metrics` (store_true, default=False) |
| Helper | `build_metrics(run_dir, enabled)` → (collector, writer) |
| Wiring | start/end en try/except + write_summary en finally |

### Archivos Nuevos

| Archivo | Descripción |
|---------|-------------|
| `tests/test_run_live_metrics_wiring.py` | 7 tests de wiring |

---

## Uso

```bash
# Con metrics enabled
python tools/run_live_3E.py \
  --outdir /tmp/out \
  --run-dir /tmp/run1 \
  --enable-metrics \
  --max-steps 10

# Resultado: /tmp/run1/metrics_summary.json
```

---

## Tests

| Suite | Estado |
|-------|--------|
| pytest WSL global | 482 passed, 10 skipped ✅ |
| wiring tests | 7 passed ✅ |

---

## Smoke Test

No ejecutado. Instrucciones de reproducción en `report/AG-3G-3-2_smoke.txt`.

---

## AUDIT_SUMMARY

**Paths tocados**:

- `tools/run_live_3E.py` (M: +40 líneas)
- `tests/test_run_live_metrics_wiring.py` (A)
- `report/AG-3G-3-2_*.{md,txt,patch}` (A)

**Cambios clave**: CLI --enable-metrics + helper + wiring try/except/finally.

**Resultado**: PASS.
