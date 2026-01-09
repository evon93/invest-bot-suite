# AG-3G-3-2 Notes

## Diseño de Wiring

### Nivel de Instrumentación

- **Run-level**: start("run_main") al inicio, end("run_main", status) al final
- **Per-message**: Requeriría modificar `engine/loop_stepper.py` (fuera de scope)

### Decision sobre Per-Message

El loop está encapsulado en `stepper.run_bus_mode()`. Para instrumentación per-message
sería necesario:

1. Pasar el collector al stepper
2. Modificar el bucle interno para llamar start/end

Esto está fuera de scope de este ticket pero queda documentado para futuro enhancement.

### CLI

- `--enable-metrics`: store_true, default=False
- Alternativa considerada: "auto on" cuando --run-dir presente
- Decision: explícito es mejor, evita generar archivos inesperados

### Puntos de Instrumentación Implementados

1. **Pre-run**: `collector.start("run_main")`
2. **Post-run success**: `collector.end("run_main", status="FILLED")`
3. **Post-run error**: `collector.end("run_main", status="ERROR", reason=<exc>)`
4. **Finally**: `writer.write_summary()` + `writer.close()`

## Smoke Test

El smoke test requiere un entorno con --run-dir. Ejemplo reproducible:

```bash
python tools/run_live_3E.py --outdir /tmp/out --run-dir /tmp/run1 --enable-metrics --max-steps 10
ls -la /tmp/run1/
# Esperado: metrics_summary.json
```

No se ejecutó smoke automatizado porque requiere entorno limpio y no hay modo "quick" sin efectos.
