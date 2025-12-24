# Repository Hygiene Notes — AG-H0-REPO-HYGIENE-2B

**Fecha**: 2025-12-24

---

## EOL Settings Recomendados

### Windows + WSL en repo montado

**Configuración recomendada**:

```bash
# Global (usuario)
git config --global core.autocrlf false
git config --global core.eol lf
```

**Razón**: El `.gitattributes` fuerza EOL por tipo de archivo. Con `autocrlf=false`, git respeta el `.gitattributes` sin conversiones adicionales.

### .gitattributes

Fuerza:
- **LF**: `*.py *.md *.yaml *.yml *.json *.txt *.patch *.sh *.ini *.cfg *.toml`
- **CRLF**: `*.ps1 *.bat *.cmd`
- **Binary**: `*.png *.jpg *.jpeg *.gif *.ico *.zip *.gz *.tar`

---

## Renormalización

Después de añadir `.gitattributes`, ejecutar:

```bash
git add --renormalize .
git status
```

Esto convierte todos los archivos al EOL correcto según `.gitattributes`.

**Expectativa**: El diff debería ser "solo EOL" — sin cambios de contenido.

---

## Script de Verificación

`tools/check_repo.py` ejecuta:

1. `pytest -q` — tests unitarios
2. `validate_risk_config.py` — validación de configuración de riesgo
3. `run_calibration_2B.py --mode quick` — smoke test del calibrador

Exit code:
- `0` — todo OK
- `1` — algún check falló

---

## CI (GitHub Actions)

`.github/workflows/ci.yml`:
- Trigger: push/PR a main, orchestrator-v2, feature/**
- Python 3.12 con cache pip
- Ejecuta `python tools/check_repo.py`

---

## Troubleshooting

### "LF will be replaced by CRLF" warnings

Son informativos, no errores. Después de renormalizar, desaparecen.

### git status muestra archivos "modificados" sin cambios

Ejecutar:
```bash
git add --renormalize .
git commit -m "Normalize EOL per .gitattributes"
```

### WSL vs Windows diffs

Siempre editar desde el mismo entorno (preferir WSL) o usar VS Code con "End of Line Sequence: LF".
