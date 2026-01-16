# AG-H1-1-1 Return Packet

**Status**: ✅ PASS  
**Timestamp**: 2026-01-16T18:16:00+01:00

## Objetivo

Definir e implementar Artifact Storage Policy para report/.

## Cambios Realizados

### [.gitignore](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/.gitignore) [MODIFY]

- Corregido: ahora trackea `*_return.md`, `*_last_commit.txt`, `*_notes.md`
- Corregido: ahora trackea `ORCH_HANDOFF_*.md`, `bridge_*_report.md`
- Mantiene ignorados: `*_diff.patch`, `*_run.txt`, `pytest_*.txt`

### [tools/report_artifact_policy.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tools/report_artifact_policy.py) [NEW]

~190 líneas. Features:

- Scan por archivos >threshold (1MB warn, 5MB block)
- Allowlist para docs esenciales
- Generación de SHA256 digest
- Exit code para CI gate

### [docs/policy_report_artifacts.md](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/docs/policy_report_artifacts.md) [NEW]

Documentación de policy: categorías A/B, thresholds, uso de tools.

### [tests/test_report_policy_h1_1.py](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/tests/test_report_policy_h1_1.py) [NEW]

7 tests unitarios para report_artifact_policy.py.

## Verificación

```
python -m pytest -q
→ 745 passed, 11 skipped in 202.97s
```

## Policy Summary

| Categoría | Track Git | Ejemplos |
|-----------|-----------|----------|
| A (docs) | ✓ | `*_return.md`, `ORCH_HANDOFF_*.md` |
| B (ephemeral) | ✗ | `*_diff.patch`, `runs/**` |

## AUDIT_SUMMARY

**Ficheros modificados**: `.gitignore`

**Ficheros creados**:

- `tools/report_artifact_policy.py`
- `docs/policy_report_artifacts.md`
- `tests/test_report_policy_h1_1.py`

**Riesgos**: Ninguno - backward compatible
