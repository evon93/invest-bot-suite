# AG-3C-6-1 Return Packet — CI Smoke Workflow 3C

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-6-1 (WSL + venv)  
**Rama:** `feature/3C_6_ci_smoke`  
**Estado:** ✅ COMPLETADO

---

## 1. Archivos Añadidos

| Archivo | Descripción |
|---------|-------------|
| `data/ci_smoke.csv` | Dataset dummy (20 filas) para determinismo en CI |
| `.github/workflows/smoke_3C.yml` | Workflow GitHub Actions (smoke test Runner 3C) |

---

## 2. CI Workflow (`smoke_3C.yml`)

Triggers:

- `pull_request` (main)
- `workflow_dispatch`

Pasos:

1. **Checkout** code
2. **Setup Python 3.12**
3. **Install dependencies** (pip install -r requirements.txt + pytest)
4. **Run pytest -q** (Unit tests)
5. **Run Runner 3C**:

   ```bash
   python tools/run_live_integration_3C.py \
     --data data/ci_smoke.csv \
     --out report/out_ci_smoke_3C \
     --seed 42 \
     --max-bars 10 \
     --risk-version v0.6
   ```

6. **Upload Artifacts**:
   - `events.ndjson`
   - `run_meta.json`
   - `state.db`

---

## 3. Dataset Dummy (`data/ci_smoke.csv`)

Creado específicamente para evitar dependencias externas o descargas en CI.

- **Filas:** 20
- **Patrón:** Subida lineal hasta t=10, luego bajada brusca.
- **Propósito:** Forzar cruces de SMA (Strategy v0.7) para generar `OrderIntent` y eventos.

---

## 4. Verificación Local

1. **Runner 3C:**
   - Comando ejecutado con éxito.
   - Metrics: `{'steps': 10, 'events': 6, 'fills': 2, 'rejected': 0}`
   - Archivos generados correctamente.

2. **pytest:**
   - 308 passed, 7 skipped.

---

## 5. Commit

```
5dbf31f 3C.6: add CI smoke workflow for 3C runner + artifacts
```

---

## 6. Artefactos

- [AG-3C-6-1_pytest.txt](AG-3C-6-1_pytest.txt)
- [AG-3C-6-1_run.txt](AG-3C-6-1_run.txt)
- [AG-3C-6-1_diff.patch](AG-3C-6-1_diff.patch)
- [AG-3C-6-1_last_commit.txt](AG-3C-6-1_last_commit.txt)
