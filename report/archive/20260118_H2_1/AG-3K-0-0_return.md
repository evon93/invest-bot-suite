# AG-3K-0-0 Return Packet

**Ticket**: AG-3K-0-0 — Snapshot 3K.0 (git/python/pytest) desde repo (WSL)  
**Fecha**: 2026-01-13T18:10:19+01:00  
**Status**: ✅ PASS

---

## Comandos Ejecutados

```bash
cd /mnt/c/Users/ivn_b/Desktop/invest-bot-suite
git fetch -p
git status -sb | tee report/git_status_3K0.txt
git rev-parse HEAD | tee report/head_3K0.txt
git log -1 --oneline | tee report/head_3K0_oneline.txt
source .venv/bin/activate && python --version | tee report/python_3K0.txt
source .venv/bin/activate && pytest -q | tee report/pytest_3K0_snapshot.txt
git diff --stat
```

---

## Contenido Íntegro de Artefactos

### report/head_3K0.txt

```
cb0b6a8f822d596d26722f04293ac013b82a66d4
```

### report/head_3K0_oneline.txt

```
cb0b6a8 AG-3J-6-1: closeout Phase 3J (handoff + bridge + registro)
```

### report/pytest_3K0_snapshot.txt

```
.......................................s................................ [ 11%]
........................................................................ [ 23%]
...................................................s.................... [ 34%]
..............................................................s......... [ 46%]
....................................ssss.........sss.................... [ 57%]
........................................................................ [ 69%]
........................................................................ [ 80%]
........................................................................ [ 92%]
.................................................                        [100%]
=============================== warnings summary ===============================
tests/test_multiseed_spec_2G2.py::TestMultiSeedSpec::test_run_determinism
tests/test_multiseed_spec_2G2.py::TestMultiSeedSpec::test_run_determinism
  RuntimeWarning: invalid value encountered in divide (numpy)

tests/test_ohlcv_loader.py: (5 tests)
  DeprecationWarning: is_datetime64tz_dtype is deprecated

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
615 passed, 10 skipped, 7 warnings in 171.34s (0:02:51)
```

---

## Resumen

| Métrica          | Valor                                      |
|------------------|--------------------------------------------|
| **Status**       | PASS                                       |
| **Passed**       | 615                                        |
| **Skipped**      | 10                                         |
| **Warnings**     | 7                                          |
| **Tiempo**       | 171.34s (0:02:51)                          |
| **Branch**       | main                                       |
| **HEAD**         | cb0b6a8f822d596d26722f04293ac013b82a66d4   |
| **git diff**     | vacío (0 tracked files modificados)        |

---

## DoD Verificación

- ✅ `report/git_status_3K0.txt` existe
- ✅ `report/head_3K0.txt` existe
- ✅ `report/head_3K0_oneline.txt` existe
- ✅ `report/python_3K0.txt` existe
- ✅ `report/pytest_3K0_snapshot.txt` existe y muestra PASS
- ✅ `git diff --stat` vacío
