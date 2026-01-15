# AG-H0-5-4S: Notes - EOL Renormalize Recommendation

## Por Qué Se Necesita Renormalize

El repo tiene `.gitattributes` con `* text eol=lf`, pero archivos antiguos fueron committed con CRLF.
Esto causa:

1. **"Cambios fantasma"**: Al checkout, git convierte CRLF→LF, creando diffs que no son reales.
2. **Loops de checkout**: No puedes switch branches porque hay "local changes".
3. **Stashes de ruido**: Los stashes capturan estos cambios EOL en vez de cambios reales.

## Comando de Renormalización

```bash
# Desde main limpio
git add --renormalize .
git status  # Verificar archivos afectados
git commit -m "chore: normalize line endings (CRLF → LF)"
git push origin main
```

## Archivos Probablemente Afectados

Basado en stash@{0}:
- `report/validate_risk_config_2A_after.txt`
- `report/validate_risk_config_2B_post_2_2.txt`
- `tests/test_risk_v0_5_extended.py`
- Otros archivos report/*.md

## Riesgo

**Bajo**. Solo cambia bytes de line ending (0x0D 0x0A → 0x0A).
No afecta lógica ni funcionalidad.

## Decision

Pendiente confirmación del usuario para ejecutar renormalize.
