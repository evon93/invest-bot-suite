# AG-H0-6-1E: Notes - EOL Decision

## Decisión Final

**NO crear PR de renormalize**

## Por Qué

1. `git add --renormalize .` no stagea cambios
2. Los 18 archivos con i/crlf son archivos históricos:
   - results.csv de runs de calibración pasados
   - .gitattributes, .gitignore, requirements.lock
3. Estos archivos raramente se modifican
4. Cuando se modifiquen, Git los convertirá automáticamente a LF

## Config Actual (Correcta)

```
core.autocrlf=false
core.eol=lf
.gitattributes con reglas LF para código
```

## Si Hay Problemas Futuros

1. Identificar archivo problemático con `git ls-files --eol | grep crlf`
2. Renormalizar solo ese archivo:
   ```bash
   git add --renormalize <archivo>
   git commit -m "chore: normalize EOL for <archivo>"
   ```

## Problema de "Cambios Fantasma" (ya resuelto)

El problema anterior (no poder switch branches) ocurría porque:
- Archivos en rama `tmp/stash0_triage` tenían CRLF
- Pero en main tenían LF (o viceversa)
- La discrepancia causaba el "loop"

Ese problema se resolvió con `git switch -f main` y borrando la rama temporal.
No es un problema de configuración, sino de un stash corrupto que ya fue limpiado.
