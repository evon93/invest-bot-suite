# AG-2B-3-6: Kelly Floor Promoted to Baseline

**Branch**: `feature/2B_kelly_floor_promotion`  
**Timestamp**: 2025-12-29T16:30

---

## Cambios

| Archivo | Cambio |
|---------|--------|
| `configs/risk_calibration_2B.yaml` | `kelly.cap_factor` ahora `[0.70, 0.90, 1.10, 1.30]` (floor 0.70) |
| `configs/risk_calibration_2B_candidate_kelly05.yaml` | Config de control para tests (cap=0.50) |
| `tools/run_calibration_2B.py` | Añadido `--config` flag para configs alternativas |
| `tests/test_calibration_runner_2B.py` | Tests de gate failure usan `--config kelly05` |
| `.ai/decisions_log.md` | Añadida entrada 2B-3.5/3.6 |

---

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest | 127 passed ✓ |

---

## Artefactos

- `report/2B_3_6_kelly_floor_promoted.md`
- `report/AG-2B-3-6_pytest.txt`
- `report/AG-2B-3-6_diff.patch`
