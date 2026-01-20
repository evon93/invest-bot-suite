# Validation Gates

Reference for all test validation gates and standard commands.

## Quick Reference

| Gate | Command | Env Var | Skip Count (normal) |
|------|---------|---------|---------------------|
| **Unit tests** | `pytest -q` | — | 14 skipped |
| **Warning-free** | `pytest -W error::RuntimeWarning` | — | 0 |
| **Integration offline** | `pytest -m integration_offline` | `INVESTBOT_TEST_INTEGRATION_OFFLINE=1` | 0 |
| **Realdata smoke** | `pytest -m realdata` | `INVESTBOT_REALDATA_PATH=/path` | 0 |
| **CCXT live** | `pytest tests/test_ccxt_*.py` | `INVESTBOT_ALLOW_NETWORK=1` | 0 |

## Commands

### Full Suite (Default)

```bash
source .venv/bin/activate
python -m pytest -q
```

Expected: 751+ passed, 14 skipped

### Warning Gate

```bash
python -m pytest -W error::RuntimeWarning tests/test_multiseed_spec_2G2.py
```

Fails if any RuntimeWarning is raised.

### Integration Offline

```bash
INVESTBOT_TEST_INTEGRATION_OFFLINE=1 python -m pytest -m integration_offline
```

Runs adapter-mode, checkpoint/resume, idempotency tests without network.

### Skip Inventory

```bash
bash tools/list_skips.sh <TAG>
```

Generates:

- `report/pytest_rs_<TAG>.txt` — raw pytest -rs output
- `report/skips_inventory_<TAG>.md` — parsed table

### Bridge Headers

```bash
bash tools/bridge_headers.sh <TAG>
```

Generates reproducible SESSION/DELTA headers for Orchestrator handoffs.

See also: [docs/bridge_io.md](bridge_io.md)

## Skipped Tests Categories

| Category | Count | Reason |
|----------|-------|--------|
| Env gated (realdata/integration) | 7 | Missing env vars |
| Optional deps (ccxt, pyarrow) | 3 | Not installed |
| Offline integration | 3 | INVESTBOT_TEST_INTEGRATION_OFFLINE not set |
| Test tuning | 1 | Scenario-specific |

## CI Integration

Gates can be added to CI workflows:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: python -m pytest -q

- name: Warning gate
  run: python -m pytest -W error::RuntimeWarning tests/test_multiseed_spec_2G2.py
```

---

Generated for AG-H3-4-1
