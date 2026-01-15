# ORCH_HANDOFF_post3F_close_20260108.md

**Fase**: 3F — Live Execution Readiness  
**Estado**: ✅ COMPLETADO  
**Fecha**: 2026-01-08  
**HEAD**: `2528afd`

---

## Resumen Ejecutivo

Phase 3F implementó la infraestructura de producción para ejecución en vivo: configuración de runtime con fail-fast, reintentos con backoff determinista, idempotencia para prevenir duplicados, adapter "real-ish" gated, crash recovery con checkpoint atómico, y gates CI para verificar determinismo.

---

## Objetivos Implementados

### 3F.1: Runtime Config Fail-Fast

- `engine/runtime_config.py`: `RuntimeConfig.from_env()` + `validate_for()`
- Fail-fast si faltan secrets para modos no-paper
- `.env.example` como template

### 3F.2: Retry/Backoff + Idempotency

- `engine/retry_policy.py`: `RetryPolicy` con jitter determinista (hash-based)
- `engine/idempotency.py`: `InMemoryIdempotencyStore` con TTL
- Integrado en `ExecWorker._process_one()` para prevenir duplicados

### 3F.3: Real-ish Adapter Gated

- `SimulatedRealtimeAdapter`: Fallos transitorios deterministas, latencias inyectables
- `TransientNetworkError`: Excepción retryable
- Gating: `--exchange realish` o `INVESTBOT_EXCHANGE_KIND=realish`
- Integration tests SKIP en CI por defecto

### 3F.4: Crash Recovery v0

- `engine/checkpoint.py`: `Checkpoint.save_atomic()` (tmp+rename)
- `engine/idempotency.py`: +`FileIdempotencyStore` (JSONL append-only)
- CLI: `--run-dir` para nueva ejecución, `--resume` para continuar
- Checkpoint se actualiza durante el loop

### 3F.5: CI Gates

- `.github/workflows/smoke_3F.yml`: pytest + determinism gate
- Python 3.12, triggers push/PR
- Integration tests SKIP por defecto

---

## Commits Relevantes

| Commit | Mensaje |
|--------|---------|
| `afa1ca4` | 3F.1: runtime config fail-fast + env example + tests |
| `6aca88d` | 3F.2: retry/backoff + idempotency (deterministic) + tests |
| `c569017` | 3F.3: real-ish adapter gated + tests |
| `06ddd92` | 3F.3.2: register pytest.mark.integration |
| `7bb752b` | 3F.4: crash recovery v0 (checkpoint + file idempotency) |
| `47f23fe` | 3F.4.3: update checkpoint during loop |
| `e3132dc` | 3F.5: add smoke_3F CI workflow |

---

## Evidencias de Verificación

| Gate | Archivo | Resultado |
|------|---------|-----------|
| Pytest | `report/pytest_3F6_close.txt` | 432 passed, 10 skipped |
| Determinism | `report/determinism_3F6_close.txt` | MATCH |
| HEAD | `report/head_3F6_close.txt` | `2528afd` |

---

## Notas de Operación

### Flags CLI

```bash
# Crash recovery
--run-dir <path>   # Crear nuevo run con checkpoint
--resume <path>    # Reanudar desde checkpoint existente

# Exchange adapter
--exchange paper   # Default, determinista
--exchange stub    # Latencia simulada
--exchange realish # Fallos transitorios + latencia
```

### Archivos de Run Directory

```
<run-dir>/
├── checkpoint.json         # Progreso atómico
└── idempotency_keys.jsonl  # Keys procesadas
```

---

## Riesgos y Limitaciones

1. **Checkpoint granularity**: Se actualiza por bar, no por mensaje individual
2. **FileIdempotencyStore**: Carga todo en memoria (OK para runs cortos)
3. **No real network adapter**: Solo simulación local, sin CCXT aún

---

## Next Steps para 3G

1. **CCXT integration**: Adapter real para sandbox exchanges
2. **Distributed idempotency**: Redis/DB-backed store
3. **Checkpoint offsets**: Usar offsets de bus real si se migra a Kafka
4. **Alerting**: Integración con Slack/Discord para fallos
