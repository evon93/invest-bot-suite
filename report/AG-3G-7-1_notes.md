# AG-3G-7-1 Notes

## Cierre de Fase 3G

### Resumen

La fase 3G se ha centrado en robustecer la infraestructura subyacente del bot, preparándolo para operaciones reales más serias y monitorizadas.

### Logros Principales

1. **SQLite Idempotency**: Se ha migrado de un archivo plano JSONL a una base de datos SQLite con modo WAL. Esto permite concurrencia y atomicidad real, crítico para evitar duplicados en reinicios rápidos o crashes.
2. **Observability v0**: Se ha implementado un sistema de métricas agnóstico (`MetricsCollector`) que persiste a disco (`file-first`). Esto es el primer paso hacia dashboards en tiempo real sin introducir dependencias pesadas como Prometheus aun.
3. **CCXT Sandbox**: Se ha integrado la librería CCXT de forma segura, con lazy loading y fail-fast, permitiendo usar drivers reales de exchange sin romper el entorno de simulación si la librería falta.
4. **CI Hardening**: Se ha añadido un smoke test específico (`smoke_3G.yml`) que valida estas nuevas capacidades en cada PR.

### Estado Final

- El sistema es funcional y pasa todos los tests (482 passed).
- La configuración por defecto sigue siendo conservadora (idempotency=file, metrics=disabled) para no romper flujos existentes.
- La documentación de traspaso (`ORCH_HANDOFF`) y puente (`bridge`) está lista para la siguiente fase.
