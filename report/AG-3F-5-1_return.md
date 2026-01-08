# AG-3F-5-1: CI Gates Smoke 3F — Return Packet

**Ticket**: AG-3F-5-1  
**Rama**: `feature/3F_5_ci_gates`  
**Fecha**: 2026-01-08

---

## Resumen

Creado workflow CI `smoke_3F.yml` con pytest + determinism gate.

### Nuevo Archivo

| Archivo | Descripción |
|---------|-------------|
| [.github/workflows/smoke_3F.yml](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/.github/workflows/smoke_3F.yml) | CI workflow para Phase 3F |

---

## Workflow: smoke_3F.yml

**Nombre**: `Smoke Test 3F (Pytest + Determinism)`

**Triggers**:

- `push`: branches `main`, `develop`, `feature/*`
- `pull_request`: branches `main`, `develop`
- `workflow_dispatch`: manual

**Python version**: `3.12` (copiada de smoke_3E.yml)

---

## Gates

| Gate | Comando |
|------|---------|
| Pytest | `python -m pytest -q` |
| Determinism | `python tools/check_determinism_3E.py --seed 42 --clock simulated --exchange paper` |

---

## Verificación Local

### Pytest

```
432 passed, 10 skipped, 7 warnings in 34.60s
```

### Determinism

```
Running A -> report\det_a
Running B -> report\det_b
Determinism Verified: MATCH
```

---

## Integration Tests SKIP

Los tests marcados con `@pytest.mark.integration` quedan **SKIP por defecto** en CI porque:

- No se establece `INVESTBOT_TEST_INTEGRATION=1`
- Esto es intencional para evitar tests que requieren env vars especiales

---

## DoD Verificado

- [x] Existe `smoke_3F.yml` con los 2 gates
- [x] `pytest -q` PASS local (432 passed, 10 skipped)
- [x] Determinism gate PASS local (MATCH)
- [x] No se modificó `smoke_3E.yml`
- [x] Integration tests SKIP por defecto

---

## Artefactos

- `report/pytest_3F5_ci_local.txt`
- `report/determinism_3F5_ci_local.txt`
- `report/AG-3F-5-1_diff.patch`
- `report/AG-3F-5-1_return.md` (este archivo)
