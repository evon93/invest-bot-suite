# EOL Noise Runbook

> Guía para diagnosticar y resolver problemas de line endings (CRLF/LF) en el repo.

---

## 🚨 Síntomas

```
error: Your local changes to the following files would be overwritten by checkout:
    <archivo1>
    <archivo2>
...
warning: in the working copy of '<archivo>', CRLF will be replaced by LF
```

**Causa**: Archivos en el índice tienen CRLF pero el working tree espera LF (o viceversa). Git interpreta la conversión de line endings como "cambios locales".

---

## 🔍 Checklist de Diagnóstico

### 1. Verificar si hay cambios reales (ignorando EOL)

```bash
git diff --ignore-cr-at-eol --name-only
```

- **Vacío** → Solo cambios de EOL (ruido)
- **Con archivos** → Hay cambios reales que revisar

### 2. Ver estado detallado

```bash
git status -sb
git diff --stat
```

### 3. Listar archivos con CRLF en índice

```bash
git ls-files --eol | Select-String "i/crlf"
# o en bash:
git ls-files --eol | grep "i/crlf"
```

### 4. Verificar configuración

```bash
git config --get core.autocrlf   # Esperado: false
git config --get core.eol        # Esperado: lf
```

---

## 🛠️ Remediación

### Caso A: Solo EOL-noise (sin cambios reales)

```bash
# 1. Reset forzado
git reset --hard HEAD
git clean -fd

# 2. Si aún hay "cambios", forzar switch
git switch -f main

# 3. Borrar ramas temporales problemáticas
git branch -D tmp/stash_triage  # si existe
```

### Caso B: Hay stashes de EOL-noise

```bash
# Listar stashes
git stash list

# Ver contenido de un stash
git stash show --stat "stash@{0}"

# Si insertions == deletions → es EOL-noise
# Ejemplo: "44 files, 4315 insertions(+), 4315 deletions(-)"

# Dropear stashes de ruido
git stash drop "stash@{0}"
```

### Caso C: Necesitas renormalizar archivos

```bash
# Solo si git add --renormalize GENERA cambios
git add --renormalize .
git diff --cached --stat

# Si hay cambios staged:
git commit -m "chore: normalize line endings (CRLF -> LF)"
git push origin main
```

> **NOTA**: Si `git add --renormalize .` no stagea nada, NO es necesario hacer commit.

---

## 📋 Configuración del Repo

### .gitattributes (actual)

| Patrón | EOL | Motivo |
|--------|-----|--------|
| `*.py` | LF | Código Python |
| `*.md` | LF | Documentación |
| `*.yaml` | LF | Configuración |
| `*.json` | LF | Datos |
| `*.txt` | LF | Texto |
| `*.ps1` | CRLF | PowerShell (Windows) |
| `*.bat` | CRLF | Batch scripts |

### Git Config (recomendada para Windows)

```bash
git config --global core.autocrlf false
git config --global core.eol lf
```

---

## ⚠️ Prevención

1. **No hacer stash de cambios EOL** - Si ves warnings CRLF, haz `git checkout -- .` primero.
2. **Verificar antes de commit** - `git diff --ignore-cr-at-eol` debe mostrar solo cambios reales.
3. **No crear PRs de renormalize** salvo que `git add --renormalize .` genere cambios reales.

---

## 📚 Referencias

- [Git Attributes - text](https://git-scm.com/docs/gitattributes#_text)
- [core.autocrlf](https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration)
