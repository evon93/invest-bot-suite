# AG-H0-6-1E: EOL Hardening Audit

**Timestamp**: 2025-12-29T18:25

---

## Auditoría de Configuración EOL

| Setting | Valor | Estado |
|---------|-------|--------|
| core.autocrlf | false | ✓ Correcto |
| core.eol | lf | ✓ Correcto |
| core.safecrlf | (unset) | OK |
| .gitattributes | Presente | ✓ Bien configurado |

---

## .gitattributes (extracto)

```
*.py text eol=lf
*.md text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.txt text eol=lf
*.ps1 text eol=crlf  # Windows scripts
```

---

## Archivos con CRLF en Índice

| Tipo | Cantidad | Archivos |
|------|----------|----------|
| i/crlf | 18 | .gitattributes, .gitignore, requirements.lock, varios results.csv |

Estos son archivos históricos que fueron committed antes de .gitattributes o son generados automáticamente.

---

## Resultado de Renormalize

```bash
git add --renormalize .
git diff --cached --stat
# Output: vacío (0 cambios staged)
```

**Interpretación**: Los archivos con CRLF en índice ya tienen LF en working tree.
Git los convierte automáticamente por .gitattributes. No hay nada que renormalizar.

---

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest | 127 passed ✓ |
| Cambios staged | 0 |

---

## Decisión

### **Renormalize PR: NO NECESARIO**

**Justificación**:
1. `git add --renormalize .` no produce cambios
2. Los archivos con CRLF son:
   - Archivos históricos estáticos (results.csv de runs pasados)
   - Archivos de configuración raramente modificados
3. La conversión CRLF→LF ocurre automáticamente cuando se tocan
4. No hay "cambios fantasma" que bloqueen checkouts (problema ya resuelto)

### Recomendación

**Mantener configuración actual**. Si en el futuro hay problemas:

```bash
# Solo si hay nuevos archivos problemáticos
git add --renormalize <archivo-específico>
git commit -m "chore: normalize EOL for <archivo>"
```

---

## Artefactos

- No se creó branch (renormalize no necesario)
- No hay commits
- Config EOL verificada y correcta
