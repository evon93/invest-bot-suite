# AG-2E-3-4-yaml-profiles: Gate Profiles (full_demo vs full)

**Branch**: `feature/2E_full_demo_profile`  
**Timestamp**: 2025-12-28T16:38

---

## Cambios

| Archivo | Cambio |
|---------|--------|
| `configs/risk_calibration_2B.yaml` | +perfil `full_demo` con thresholds compatibles (~33% actividad) |
| `tools/run_calibration_2B.py` | +`--profile` flag, mapeo mode→profile, `gate_profile` en run_meta |
| `tests/test_calibration_runner_2B.py` | +3 tests nuevos, actualizados 3 existentes para usar `--profile full` |

### Nuevo comportamiento

| Comando | Profile usado | Gate esperado |
|---------|--------------|---------------|
| `--mode full` | full_demo | PASS (~33% > 30%) |
| `--mode full --profile full` | full | FAIL (~33% < 60%) |
| `--mode full --profile full --strict-gate` | full | exit 1 |

---

## Verificación (2025-12-28T16:38)

| Check | Resultado |
|-------|-----------|
| pytest | 124 passed ✓ |
| mode=full (→full_demo) | PASS, gate_profile="full_demo" ✓ |
| --profile full --strict-gate | exit 1, gate_profile="full" ✓ |

### run_meta.json (full_demo)

```json
{
  "gate_profile": "full_demo",
  "gate_passed": true,
  "active_rate": 0.325,
  "gate_fail_reasons": []
}
```

### run_meta.json (full strict)

```json
{
  "gate_profile": "full",
  "gate_passed": false,
  "active_rate": 0.325,
  "gate_fail_reasons": ["active_n_below_min", "active_rate_below_min", "inactive_rate_above_max"]
}
```

---

## Artefactos

- `report/AG-2E-3-4-yaml-profiles_return.md` (este archivo)
- `report/AG-2E-3-4-yaml-profiles_pytest.txt`
- `report/AG-2E-3-4-yaml-profiles_run.txt`
- `report/AG-2E-3-4-yaml-profiles_diff.patch`
- `report/AG-2E-3-4-yaml-profiles_last_commit.txt`
- `report/out_2E_3_4_full_demo_smoke/`
- `report/out_2E_3_4_full_strict_smoke/`

---

## Commit

```
0786c1a 2E: add full_demo gate profile; map mode=full to demo thresholds
```

## PR

Crear: https://github.com/evon93/invest-bot-suite/compare/main...feature/2E_full_demo_profile
