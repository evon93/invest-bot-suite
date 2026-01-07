# AG-3F-3-2: Registrar pytest mark integration — Return Packet

**Ticket**: AG-3F-3-2  
**Rama**: `feature/3F_3_realish_adapter_gated`  
**Fecha**: 2026-01-07

---

## Resumen

Registrado `pytest.mark.integration` en `pytest.ini` para eliminar `PytestUnknownMarkWarning`.

---

## Ubicación del Cambio

**Archivo**: [pytest.ini](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/pytest.ini)

**Línea añadida**:

```ini
markers =
    realdata: tests that require INVESTBOT_REALDATA_PATH environment variable
    integration: integration tests requiring env flags (SKIP in CI by default)  # ← NEW
```

---

## Evidencia: Warning Eliminado

**Antes** (AG-3F-3-1):

```
419 passed, 10 skipped, 8 warnings
```

**Después** (AG-3F-3-2):

```
419 passed, 10 skipped, 7 warnings
```

El warning `PytestUnknownMarkWarning: Unknown pytest.mark.integration` ya no aparece.

---

## Comandos Ejecutados

| Comando | Resultado |
|---------|-----------|
| `pytest tests/test_realish_adapter_integration_3F3.py -q` | 3 skipped (sin warning) |
| `pytest -q` | 419 passed, 10 skipped, **7 warnings** |

---

## DoD Verificado

- [x] Warning eliminado (8 → 7 warnings)
- [x] `pytest -q` PASS
- [x] Cambios mínimos (1 línea)

---

## Artefactos

- `report/pytest_3F3_integration_mark.txt`
- `report/AG-3F-3-2_pytest.txt`
- `report/AG-3F-3-2_diff.patch`
- `report/AG-3F-3-2_return.md` (este archivo)
