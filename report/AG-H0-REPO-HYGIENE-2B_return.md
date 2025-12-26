# Return Packet — AG-H0-REPO-HYGIENE-2B

**Ticket**: AG-H0-REPO-HYGIENE-2B — Repository Hygiene  
**Fecha**: 2025-12-24T16:39

---

## Cambios Realizados

### A) EOL Hardening

- **Creado**: `.gitattributes`
  - LF para: `*.py *.md *.yaml *.yml *.json *.txt *.patch *.sh *.ini`
  - CRLF para: `*.ps1 *.bat *.cmd`
  - Binary para: imágenes, archivos comprimidos

**Configuración recomendada** (ver `report/AG-H0-REPO-HYGIENE-2B_notes.md`):
```bash
git config --global core.autocrlf false
git config --global core.eol lf
```

### B) Script de Verificación

- **Creado**: `tools/check_repo.py`
  - Ejecuta pytest, validate_risk_config, calibration_2B
  - Exit code 0 = todo OK, 1 = algo falló

**Uso**:
```bash
python tools/check_repo.py
```

### C) CI GitHub Actions

- **Creado**: `.github/workflows/ci.yml`
  - Trigger: push/PR a main, orchestrator-v2, feature/**
  - Python 3.12 con cache pip
  - Ejecuta `python tools/check_repo.py`

---

## Verificación DoD

| Check | Resultado |
|-------|-----------|
| `pytest -q` | **57 passed** ✅ |
| `validate_risk_config` | **Errors: 0** ✅ |
| `calibration_2B` | **3 ok, 0 errors** ✅ |
| Artefactos en output.dir | ✅ |

---

## Renormalización EOL

Después del commit, ejecutar:
```bash
git add --renormalize .
git status
# Si hay cambios, commit:
git commit -m "Normalize EOL per .gitattributes"
```

---

## Artefactos

- `.gitattributes`
- `tools/check_repo.py`
- `.github/workflows/ci.yml`
- `report/AG-H0-REPO-HYGIENE-2B_notes.md`
- `report/AG-H0-REPO-HYGIENE-2B_return.md`
- `report/AG-H0-REPO-HYGIENE-2B_pytest.txt`
- `report/AG-H0-REPO-HYGIENE-2B_run.txt`
