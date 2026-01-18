# AG-3I-4-1 Notes - Audit Window Findings

## Seguridad/XSS

Verificado que:

- El `run_id` se escapa con `html.escape()` antes de insertar en el HTML
- El `generated_at_str` es ISO-8601 puro de datetime, sin input de usuario
- Los stage names en "Top Stages" se escapan correctamente

## Comportamiento del Refresh JS

- El script lee `?refresh=N` del querystring
- Solo activa el meta refresh si N > 0
- El indicador visual aparece solo cuando refresh está activo
- No hay interacción con servidor - es puramente client-side

## Out-of-Scope Findings

1. **Auto-save timestamp en summary**: Podría guardarse `generated_at` en el JSON summary para trazabilidad. No implementado.

2. **Countdown visual**: El refresh indicator muestra "auto-refresh: 5s" pero no hace countdown. Podría añadirse JS para mostrar segundos restantes.

Ninguna acción requerida para este ticket.
