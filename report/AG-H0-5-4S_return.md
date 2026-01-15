# AG-H0-5-4S: Stash Triage + EOL Renormalize Recommendation

**Timestamp**: 2025-12-29T18:18

---

## Stash List

| Index | Branch | Message | Status |
|-------|--------|---------|--------|
| stash@{0} | main | temp: before merge | Analizado |
| stash@{1} | feature/2B_risk_calibration | AG-2C-1-2A: WIP pre-2C | Analizado |

---

## Análisis por Stash

### stash@{0}: "temp: before merge"

| Métrica | Valor |
|---------|-------|
| Archivos | 10 |
| Insertions | 1302 |
| Deletions | 1302 |
| Diagnóstico | **EOL-noise** (ins = del) |

**Archivos afectados**:
- report/validate_risk_config_*.txt
- tests/test_risk_v0_5_extended.py
- otros reports

**Recomendación**: **DROP** ❌

---

### stash@{1}: "AG-2C-1-2A: WIP pre-2C"

| Métrica | Valor |
|---------|-------|
| Archivos | 0 (vacío) |
| Diagnóstico | Stash de índice vacío |

**Recomendación**: **DROP** ❌

---

## Clasificación Final

| Stash | Acción | Motivo |
|-------|--------|--------|
| stash@{0} | DROP | Solo EOL-noise (1302 = 1302) |
| stash@{1} | DROP | Vacío, sin contenido |

**Total KEEP**: 0
**Total DROP**: 2

---

## Config EOL

| Setting | Valor | Estado |
|---------|-------|--------|
| core.autocrlf | false | ✓ Correcto |
| core.eol | lf | ✓ Correcto |
| .gitattributes | Presente | ✓ Bien configurado |

---

## Problema Raíz

Archivos fueron committed con CRLF **antes** de que `.gitattributes` existiera o se configurara `core.eol=lf`. Aunque la config es correcta ahora, los archivos en el índice aún tienen CRLF hardcoded.

**Síntoma**: Al checkout, git convierte CRLF→LF (por .gitattributes), generando "cambios fantasma" que bloquean switches.

---

## Recomendación: PR de Renormalización

**Propuesta**: Un commit único que renormalice todos los EOL:

```bash
# Ejecutar desde main limpio
git add --renormalize .
git commit -m "chore: normalize line endings (CRLF → LF)"
git push origin main
```

**Beneficios**:
1. Elimina "cambios fantasma" de EOL permanentemente
2. Previene loops de checkout en el futuro
3. Consistencia entre Windows/WSL/Linux

**Riesgo**: Bajo. Solo cambia line endings, no lógica.

---

## Comandos para Dropear Stashes

```bash
git stash drop "stash@{1}"
git stash drop "stash@{0}"
```

Ejecutar si se confirma DROP.
