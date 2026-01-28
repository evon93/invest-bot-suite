# Bridge Report: H4 → Next Phase

**Desde:** H4 (Coverage CI Verification)  
**Hacia:** Siguiente fase  
**Fecha:** 2026-01-28  

---

## Estado del Repositorio

| Campo | Valor |
|-------|-------|
| Branch | main |
| HEAD | `5afabca` |
| Tests | 769 passed, 21 skipped |
| Coverage | 82.7% (fail-under: 70%) |

---

## Entregables H4

1. **Coverage toolchain** instalado y funcional
2. **`.coveragerc`** con excludes CLI-only
3. **33 tests nuevos** (validate_risk_config + run_metrics edge cases)
4. **Coverage gate** configurado (70% threshold)
5. **Fix CI flakiness** (datetime64 ns/us)

---

## Dependencias para Próxima Fase

### Archivos Críticos

| Archivo | Status |
|---------|--------|
| `requirements-dev.txt` | ✅ Estable |
| `.coveragerc` | ✅ Estable |
| `pytest.ini` | ✅ Sin cambios |

### Comandos Verificados

```bash
# Pytest básico
pytest -q

# Coverage gate
pytest -q --cov=engine --cov=tools --cov-fail-under=70
```

---

## Gaps Pendientes (de H4.2 análisis)

Los siguientes archivos tienen 0% coverage pero están excluidos intencionalmente:

- CLI entry points (`tools/run_*.py`)
- Smoke tests (`tools/smoke_*.py`)
- Demos (`tools/*_demo.py`)

**Estrategia:** No testear directamente; son entry points, no módulos.

---

## Sugerencias para Próxima Fase

### Opción A: CI Integration (H5)

Añadir coverage gate al workflow de GitHub Actions:

```yaml
- name: Coverage Gate
  run: |
    pip install -r requirements-dev.txt
    pytest --cov=engine --cov=tools --cov-fail-under=70
```

### Opción B: Incremento Gradual (H6)

Subir fail-under de 70% → 75% → 80% en fases sucesivas.

### Opción C: Tests Adicionales (H7)

Añadir tests para módulos con cobertura parcial:

- `tools/apply_calibration_topk.py`
- `tools/build_best_params_2C.py`

---

## Verificación Pre-Handoff

| Check | Status |
|-------|--------|
| pytest -q | ✅ PASS |
| coverage gate | ✅ 82.7% > 70% |
| main up-to-date | ✅ |
| Sin archivos sin trackear críticos | ✅ |
