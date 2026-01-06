# Bridge Report: 3E to 3F

**Origen**: Phase 3E (Unified Runner & Determinism)
**Destino**: Phase 3F (Live Execution Readiness / Pre-Production)

## Estado Actual (Post-3E)

El sistema cuenta ahora con un runner robusto (`run_live_3E.py`) capaz de operar en modo simulación determinista o en modo real (aunque el `RealTimeProvider` es básico y los `ExchangeAdapter` reales están pendientes/mocked). La infraestructura de CI garantiza que la lógica de simulación no se rompa silenciosamente.

## Next Steps (Phase 3F)

### Objetivos Sugeridos

1. **Conector Real (Stub Avanzado/CCXT)**: Implementar un `ExchangeAdapter` que conecte realmente (o simule con mayor fidelidad via CCXT sandbox) para validar flujo de órdenes real.
2. **Gestión de Secretos**: Integrar manejo seguro de API Keys para el modo `real`.
3. **Robustez en Vivo**: Manejo de errores de red, reconexión de websockets (si aplica), y persistencia de estado ante crashes en modo `real`.
4. **Dashboard en Tiempo Real**: Visualización básica del estado del bot mientras corre (consumiendo `state.db` o `events.ndjson` en caliente).

### Merge Strategy

- **Rama Actual**: `feature/3E_6_closeout` (contiene todo 3E).
- **Destino**: `develop` (o `main` si se sigue trunk-based estricto).
- **Gate**: CI Green (`smoke_3E.yml` passing).

## Notas para el Desarrollador 3F

- El `RealTimeProvider` actual es un wrapper de `time.time()`. Revisar si se necesita `ntplib` o sincronización precisa.
- `run_live_3E.py` ya acepta `--clock real`. Al activarlo, el determinismo NO está garantizado (y el gate de determinismo fallará si se corre en ese modo, lo cual es esperado).
