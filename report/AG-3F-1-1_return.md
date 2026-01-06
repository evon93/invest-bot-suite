# AG-3F-1-1: Runtime Config Fail-Fast — Return Packet

**Ticket**: AG-3F-1-1  
**Rama**: `feature/3F_1_runtime_config`  
**Fecha**: 2026-01-06

---

## Resumen de Cambios

Implementación de validación fail-fast de configuración runtime para proteger contra ejecución en modo real/live sin credentials configurados.

### Archivos Nuevos

- [engine/runtime_config.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/engine/runtime_config.py) — `RuntimeConfig` dataclass con `from_env()` y `validate_for()`
- [.env.example](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/.env.example) — Template de variables de entorno
- [tests/test_runtime_config_failfast.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_runtime_config_failfast.py) — 14 tests cubriendo casos A-E

### Archivos Modificados

- [tools/run_live_3E.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/run_live_3E.py) — Integración de RuntimeConfig con validación antes de setup

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_runtime_config_failfast.py -v` | 14 passed |
| `pytest -q` | 386 passed, 7 skipped, 7 warnings |

---

## DoD Verificado

- [x] `pytest -q tests/test_runtime_config_failfast.py` PASS
- [x] `pytest -q` PASS (sin regresiones)
- [x] No deps nuevas
- [x] Mensajes de error no filtran secretos

---

## Notas de Seguridad

- Los mensajes de error nunca incluyen valores de secrets (solo nombres de keys faltantes)
- Variables de entorno con espacios en blanco se tratan como missing
- `paper` y `stub` exchanges funcionan sin env vars (CI-compatible)

---

## Artefactos Generados

- `report/pytest_3F1_runtime_config.txt`
- `report/AG-3F-1-1_pytest.txt`
- `report/AG-3F-1-1_diff.patch`
- `report/AG-3F-1-1_return.md` (este archivo)
