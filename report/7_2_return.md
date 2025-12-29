# 7.2: CLI UX Alias --mode full_demo

**Branch**: `feature/7_2_cli_full_demo_alias`  
**Timestamp**: 2025-12-29T19:08

---

## Cambios

| Archivo | Cambio |
|---------|--------|
| `tools/run_calibration_2B.py` | Añadida `normalize_args()` para alias, epilog con ejemplos |
| `tests/test_calibration_runner_2B.py` | +5 tests unitarios para normalize_args |

---

## Funcionalidad

### Alias --mode full_demo

```bash
# Ahora funciona:
python tools/run_calibration_2B.py --mode full_demo

# Equivale a:
python tools/run_calibration_2B.py --mode full --profile full_demo
```

### Validación de Conflictos

```bash
# Esto da error claro:
python tools/run_calibration_2B.py --mode full_demo --profile full
# Error: Conflicto: --mode full_demo implica --profile full_demo
```

---

## Verificación

| Check | Resultado |
|-------|-----------|
| pytest | 132 passed ✓ |
| Smoke alias | mode=full, gate_profile=full_demo ✓ |
| Smoke canon | mode=full, gate_profile=full_demo ✓ |

---

## Artefactos

- `report/7_2_pytest.txt`
- `report/out_7_2_smoke_alias/`
- `report/out_7_2_smoke_canon/`
