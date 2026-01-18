# AG-3I-2-1 Notes - Audit Window Findings

## Coherencia del Supervisor

### Puntos Revisados

1. **Sleep/Backoff colgado**: El supervisor ahora chequea `is_stop_requested` antes del backoff sleep, evitando que quede colgado.

2. **Restart pese a stop**: Se añadieron 3 puntos de chequeo:
   - Antes de iniciar nuevo ciclo
   - Después de que el child termina (antes de decidir restart)
   - Antes del backoff sleep

   Esto garantiza que si llega SIGINT/SIGTERM en cualquier momento, el supervisor saldrá limpiamente.

3. **Flush/cierre de ficheros**: El método `_finalize()` llama a `_save_state()` y `_log()` antes de salir. Los archivos se abren/cierran en cada escritura (append mode) así que no hay buffers pendientes.

## Out-of-Scope Findings

Ninguno crítico identificado durante esta implementación.

### Mejoras Menores (no implementadas)

1. **Timeout en subprocess**: El `subprocess.run()` no tiene timeout. Si el child se cuelga, el supervisor también. Esto es comportamiento esperado pero podría añadirse un `--child-timeout` opcional.

2. **Logging a stderr**: Actualmente los mensajes de print van a stdout pero los logs van a archivo. Podría unificarse con logging module.

Ninguna acción requerida para este ticket.
