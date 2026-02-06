# Validation Gates

Reference for all test validation gates of invest-bot-suite.

---

## Quick Reference

| Gate | Command | Threshold | Env Var |
|------|---------|-----------|---------|
| **Unit tests** | `pytest -q` | — | — |
| **Coverage gate** | `pytest --cov=engine --cov=tools --cov-fail-under=80` | 80% | — |
| **Warning-free** | `pytest -W error::RuntimeWarning` | 0 warnings | — |
| **Integration offline** | `pytest tests/test_integration_offline_H3.py` | — | `INVESTBOT_TEST_INTEGRATION_OFFLINE=1` |
| **Realdata smoke** | `pytest -m realdata` | — | `INVESTBOT_REALDATA_PATH=/path` |

---

## Local Harness: validate_local.py

Ejecuta múltiples gates en un solo comando con evidencias estructuradas.

### Uso

```bash
# Preset CI estándar (coverage + offline)
python tools/validate_local.py --preset ci

# Solo pytest rápido
python tools/validate_local.py --preset quick

# Validación completa (CI + robustness + repo check)
python tools/validate_local.py --preset full

# Override de umbral de coverage
python tools/validate_local.py --preset ci --cov-fail-under 85
```

### Presets

| Preset | Gates | Coverage | Uso |
|--------|-------|----------|-----|
| `ci` | pytest_full, coverage_gate, offline_integration | 80% | CI/PR gates |
| `quick` | pytest_full | 80% | Dev rápido |
| `full` | ci + robustness_quick + repo_check | 80% | Pre-release / auditoría |

**Detalle preset `full`:**

- Todos los gates de `ci`
- `robustness_quick`: valida configs robustness 2D
- `repo_check`: verifica estructura del repo

### Outputs

| Archivo | Descripción |
|---------|-------------|
| `report/<prefix>.txt` | Log humano con resultados |
| `report/<prefix>_run_meta.json` | Metadata JSON estructurada |
| `report/<prefix>_logs/<gate>.log` | Log individual de cada gate |
| `report/coverage.xml` | Coverage XML (generado por coverage_gate) |

### Exit Codes

| Code | Significado |
|------|-------------|
| 0 | Todos los gates PASS |
| 1 | Algún gate FAIL |
| 2 | Error interno (argumentos, I/O) |

---

## Packaging: pack_handoff.py

Empaqueta evidencias en un ZIP determinista con manifest SHA256.

### Uso

```bash
# Dry-run (ver qué incluiría)
python tools/pack_handoff.py --dry-run

# Generar ZIP + manifest
python tools/pack_handoff.py \
    --out report/archive/YYYYMMDD_handoff/pack.zip \
    --manifest report/archive/YYYYMMDD_handoff/manifest.json \
    --date YYYYMMDD
```

### Características

- **Determinismo**: timestamp fijo (1980-01-01), orden lexicográfico
- **Manifest**: JSON con SHA256 y tamaño por archivo
- **Exclusiones**: `*.env`, `**/secrets*`, `credentials*`, `__pycache__`, etc.

### Outputs

| Archivo | Descripción |
|---------|-------------|
| `<out>.zip` | ZIP comprimido con evidencias |
| `<manifest>.json` | Manifest con hashes SHA256 |
| `report/pack_handoff_*.txt` | Log humano del empaquetado |

---

## CI Integration

### Job: validate-local

El workflow `.github/workflows/ci.yml` incluye un job `validate-local` que:

1. Ejecuta `python tools/validate_local.py --preset ci`
2. Coverage gate con umbral **80%**
3. Offline integration tests (con `INVESTBOT_TEST_INTEGRATION_OFFLINE=1`)
4. Sube artifacts automáticamente

### Triggers

| Evento | Branches | Job validate-local |
|--------|----------|-------------------|
| `push` | main, orchestrator-v2, feature/** | ✓ |
| `pull_request` | main, orchestrator-v2 | ✓ |
| `workflow_dispatch` | — | ✓ |

### Artifacts Subidos

| Artifact | Path |
|----------|------|
| Log humano | `report/validate_local_ci.txt` |
| Metadata JSON | `report/validate_local_ci_run_meta.json` |
| Gate logs | `report/validate_local_ci_logs/` |
| Coverage XML | `report/coverage.xml` |

---

## Skipped Tests Categories

| Category | Count | Reason |
|----------|-------|--------|
| Env gated (realdata/integration) | 7 | Missing env vars |
| Optional deps (ccxt, pyarrow) | 3 | Not installed |
| Offline integration | 3 | `INVESTBOT_TEST_INTEGRATION_OFFLINE` not set |
| Test tuning | 1 | Scenario-specific |

---

## Additional Tools

### Skip Inventory

```bash
bash tools/list_skips.sh <TAG>
```

Genera `report/skips_inventory_<TAG>.md` con tabla de tests saltados.

### Bridge Headers

```bash
bash tools/bridge_headers.sh <TAG>
```

Genera headers SESSION/DELTA para handoffs de Orchestrator.

See: [docs/bridge_io.md](bridge_io.md)

---

*Updated for H5.5 (AG-H5-5-1)*

---

## Report Artifacts Policy

> Added in AG-H0-2-1

### Volatile vs Permanent Artifacts

| Category | Pattern | Git Status | Purpose |
|----------|---------|------------|---------|
| **Volatile** | `out_*/**`, `calibration_*/*.csv`, `pytest_*.txt`, `runs/**` | Ignored | Ephemeral execution outputs |
| **Permanent** | `ORCH_HANDOFF_*.md`, `bridge_*.md`, `archive/**` | Tracked | Handoff documentation, historical records |

### Guidelines

1. **Do NOT commit** outputs from local executions (validate_local, calibration, smokes)
2. Volatile patterns are defined in `.gitignore` and `tools/check_repo.py::VOLATILE_PATTERNS`
3. `tools/check_repo.py` emits **WARN** if it detects volatile files that are tracked and modified
4. Use `git rm --cached <file>` to untrack files that should be volatile

### Volatile Patterns Reference

```
report/out_*/**
report/calibration_2B/*.csv
report/calibration_2B/run_*.txt
report/calibration_results_2B.csv
report/pytest_*.txt
report/git_status_*.txt
report/runs/**
```

### Permanent (Tracked) Artifacts

- `report/ORCH_HANDOFF_*.md` — Phase handoff reports
- `report/bridge_*.md` — Bridge reports between phases
- `report/archive/**` — Historical snapshots
- `report/external_ai/*.md` — External AI audit results (except inbox_external/)
