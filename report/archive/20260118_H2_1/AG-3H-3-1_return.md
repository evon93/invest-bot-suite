# AG-3H-3-1 Return Packet

## Objetivo

Dashboard HTML file-first para inspeccionar rápidamente métricas sin deps nuevas.

## Baseline

- **Branch**: main
- **HEAD antes**: ec6db3a
- **Fecha**: 2026-01-10

## Implementación

### Script: `tools/render_metrics_dashboard_3H.py`

**CLI:**

```
--run-dir <path>     # Directorio con metrics_summary.json
--out <file>         # Output HTML (default: run-dir/dashboard.html)
--tail-lines <int>   # Max líneas NDJSON (default: 2000)
```

**Secciones del dashboard:**

1. **Overview**: processed, filled, allowed, rejected, errors, retries, dupes
2. **Latency**: P50, P95, samples count
3. **Stages**: tabla con count, P50/P95, outcomes por stage
4. **Errors & Rejections**: breakdown por razón
5. **Recent Events**: tail de los últimos eventos (rotación aware)

**Características:**

- CSS inline (self-contained)
- Sin deps externas (solo stdlib)
- Lee archivos rotados en orden correcto (.1, .2, ..., main)
- Escapa HTML para prevenir XSS
- Output determinista

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `tools/render_metrics_dashboard_3H.py` | [NEW] Script dashboard HTML |
| `tests/test_metrics_dashboard_render.py` | [NEW] 10 tests |

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest -q | **PASS** (509 passed, 10 skipped) |
| tests dashboard | **10/10 PASS** |
| smoke | **OK** (dashboard.html 5.4KB) |

## Artefactos

- `report/out_3H2_rotation_smoke/dashboard.html`

## DOD Status: **PASS**

- [x] pytest -q PASS
- [x] dashboard.html generado
- [x] sin deps nuevas
