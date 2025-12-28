# AG-2E-2-4-conflicts: Resolución de Conflictos PR#4

**Branch**: `feature/2E_full_gate_useful`  
**Merge de**: `origin/main`  
**Timestamp**: 2025-12-28T15:00

---

## Resumen de Resolución

| Archivo | Resolución |
|---------|------------|
| `.ai/active_context.md` | theirs (main) |
| `registro_de_estado_invest_bot.md` | theirs (main) |
| `tools/run_calibration_2B.py` | **ours (2E)** - restaurado post-merge |
| `tests/test_calibration_runner_2B.py` | **ours (2E)** - restaurado post-merge |
| `configs/risk_calibration_2B.yaml` | **ours (2E)** - restaurado post-merge |

**Estrategia aplicada:**
1. Merge con `-X theirs` para resolver conflictos en docs automáticamente
2. Restaurado código 2E crítico con `git checkout 0611785 -- <files>`

---

## Funcionalidad 2E Preservada

| Feature | Status |
|---------|--------|
| `--strict-gate` flag | ✓ Presente |
| `gate_passed` en meta | ✓ Presente |
| `insufficient_activity` en meta | ✓ Presente |
| `gate_fail_reasons` en meta | ✓ Presente |
| `suggested_exit_code` en meta | ✓ Presente |
| `is_active` columna CSV | ✓ Presente |
| `rejection_*` columnas CSV | ✓ Presente |

---

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest | 118 passed ✓ |
| quick smoke | 12 combos OK ✓ |
| full smoke (40) | gate FAIL (expected) ✓ |
| full --strict-gate | exit 1 (expected) ✓ |

---

## PR#4 Status

**Ahora mergeable**: Sí (sin conflictos tras push)

---

## Artefactos

- `report/AG-2E-2-4-conflicts_return.md`
- `report/AG-2E-2-4-conflicts_pytest.txt`
- `report/AG-2E-2-4-conflicts_run.txt`
- `report/AG-2E-2-4-conflicts_last_commit.txt`
- `report/out_2E_2_4_quick_smoke/`
- `report/out_2E_2_4_full_smoke/`
- `report/out_2E_2_4_full_strict_smoke/`
