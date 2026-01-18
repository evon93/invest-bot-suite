# AG-3I-1-2 Notes

## Out-of-Scope Findings

No out-of-scope findings. El código existente de AG-3I-1-1 ya implementaba correctamente el contrato de batch latency:

```python
# risk/exec/position multiplican por processed:
self.time_provider.advance_ns(STAGE_LATENCY_NS["risk"] * risk_processed)
self.time_provider.advance_ns(STAGE_LATENCY_NS["exec"] * exec_processed)
self.time_provider.advance_ns(STAGE_LATENCY_NS["position"] * pos_processed)
```

## Coherencia Semántica Verificada

- `processed` = número de items procesados en esa iteración de drain
- Es el multiplicador correcto (no items totales acumulados)
- La suma de latencias es consistente con `stage_events_count` en `metrics_summary`

## Posibles Mejoras Futuras (no implementadas)

1. **Configurable latency per stage**: Actualmente las latencias son constantes. Podría ser útil permitir configuración externa.
2. **Per-item trace IDs**: Actualmente risk/exec/position registran un stage event por batch. Podría ser más granular.

Ninguna acción requerida para este ticket.
