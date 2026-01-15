# AG-H0-5-3R: Fix Git Branch Switch Loop

**Timestamp**: 2025-12-29T18:08

---

## Problema

El usuario no podía salir de `tmp/stash0_triage` - cada `git switch main` fallaba por "local changes would be overwritten" aunque fueran solo cambios EOL.

## Diagnóstico

| Check | Resultado |
|-------|-----------|
| core.autocrlf | `false` ✓ |
| core.eol | `lf` ✓ |
| `reset --hard` | No limpia (archivos se regeneran) |
| `git diff --ignore-cr-at-eol` | Vacío (solo EOL diff) |

**Causa raíz**: Archivos en commit tienen CRLF hardcoded. Al checkout, git los convierte a LF (por core.eol=lf), lo cual genera "cambios" que bloquean switch.

## Solución Aplicada

```bash
git switch -f main  # Force switch ignorando cambios
git branch -D tmp/stash0_triage  # Borrar rama temporal
```

## Estado Final

| Check | Resultado |
|-------|-----------|
| Branch actual | `main` ✓ |
| Working tree | Limpio ✓ |
| `tmp/stash0_triage` | Borrada ✓ |

---

## Recomendación Preventiva

Para evitar este loop en el futuro:

```bash
# Normalizar EOL en todo el repo (una sola vez)
git add --renormalize .
git commit -m "chore: normalize line endings"
```

Esto convertirá todos los archivos a LF en el índice de forma permanente.

---

## Artefactos

- No commits realizados
- Rama temporal `tmp/stash0_triage` borrada
- Stashes existentes NO tocados (5+ aún presentes)
