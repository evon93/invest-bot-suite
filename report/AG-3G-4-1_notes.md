# AG-3G-4-1 Notes

## CI Smoke Gate for 3G

### Objetivo

Asegurar que las nuevas features de 3G (SQLite wiring opcional, Metrics wiring opcional) no rompen la funcionalidad básica y que las métricas se generan correctamente cuando se solicitan.

### Implementación

Se ha creado `.github/workflows/smoke_3G.yml` siguiendo el patrón de los workflows de humo existentes (como `smoke_3F.yml`).

**Pasos clave:**

1. **Setup**: Python 3.12 y dependencias.
2. **Unit Tests**: `pytest -q` (excluye integración/ccxt por defecto).
3. **Smoke Test Live**:
   - Ejecuta `tools/run_live_3E.py` en modo simulado.
   - Habilita métricas explícitamente (`--enable-metrics`).
   - Usa `--run-dir` para activar el path de persistencia.
   - Verifica la existencia de `metrics_summary.json` post-ejecución.

### Consideraciones

- No requiere credenciales ni red (Paper Exchange).
- Valida el wiring de `MetricsCollector` y `MetricsWriter` en un entorno limpio.
- Valida que el `run_live_3E.py` no crashea con estas opciones.
