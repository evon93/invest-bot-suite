# AG-3I-4-1: Dashboard V1 - Return Packet

## Resumen

Implementado Dashboard v1 con:

- Timestamp de generación (UTC ISO-8601)
- run_id (de summary o fallback a dir name)
- Sección "Top Stages by P95" ordenada desc
- Auto-refresh opcional vía `?refresh=N` querystring

## Cambios Realizados

| Archivo | Cambio |
|---------|--------|
| `tools/render_metrics_dashboard_3H.py` | Añadido `now_fn` param, `generated_at`, `run_id`, sección Top Stages, JS refresh |
| `tests/test_metrics_dashboard_render.py` | 9 tests nuevos para AG-3I-4-1, 1 test actualizado para XSS |

## Nuevas Features

### Timestamp y Run ID

```html
<div class="meta-info">
  <p>Run: <strong>/path/to/run</strong></p>
  <p>Run ID: <strong>my_run_123</strong></p>
  <p>Generated at: <strong>2026-01-11T19:30:00+00:00</strong></p>
</div>
```

### Top Stages by P95 (nueva sección)

- Tabla ordenada por P95 descendente
- Stages con p95 más alto primero
- Fallback "N/A" si p95 falta

### Auto-Refresh

```
http://localhost/dashboard.html?refresh=5
```

- Activa meta refresh cada N segundos
- Muestra indicador visual "auto-refresh: 5s"

## Tests Nuevos

| Test | Descripción |
|------|-------------|
| `test_generated_at_with_injectable_now_fn` | Timestamp inyectable para determinismo |
| `test_run_id_from_summary` | run_id de summary metadata |
| `test_run_id_fallback_to_dir_name` | Fallback a run_dir.name |
| `test_top_stages_section_exists` | Sección Top Stages presente |
| `test_top_stages_sorted_descending` | Orden correcto por P95 |
| `test_top_stages_handles_missing_p95` | Fallback N/A para p95 vacío |
| `test_js_refresh_script_present` | JS refresh en HTML |
| `test_refresh_indicator_hidden_by_default` | Indicador oculto sin ?refresh |

## Verificación

### pytest -q

```
565 passed, 10 skipped in 30.25s
```

## Baseline

- Branch: `feature/AG-3I-4-1_dashboard_v1`
- Parent: `28db80db840a4f281183c962b89fc75c2a389d25` (main @ post PR#24)

## DoD

- [x] pytest -q PASS (565 passed)
- [x] Timestamp UTC ISO-8601 con now_fn inyectable
- [x] run_id robustamente determinado
- [x] Top stages por P95 ordenado desc
- [x] Refresh optional via querystring JS
- [x] Tests determinísticos
