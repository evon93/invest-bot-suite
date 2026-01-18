# AG-3K-1-1 Return Packet

**Ticket**: AG-3K-1-1 — MarketDataAdapter + FixtureMarketDataAdapter + runner wiring  
**Fecha**: 2026-01-13T18:34:00+01:00  
**Status**: ✅ PASS

---

## Paths Tocados

| Archivo | Acción |
|---------|--------|
| `engine/market_data/__init__.py` | NEW |
| `engine/market_data/market_data_adapter.py` | NEW |
| `engine/market_data/fixture_adapter.py` | NEW |
| `tests/fixtures/ohlcv_fixture_3K1.csv` | NEW |
| `tests/test_market_data_fixture_adapter.py` | NEW |
| `tools/run_live_3E.py` | MODIFIED |

---

## Decisiones

| Decisión | Valor |
|----------|-------|
| `MarketDataEvent.ts` unit | **epoch milliseconds (int)** UTC |
| `poll()` order | no-decreciente por `ts` |
| Duplicados | error (validación en ohlcv_loader) |
| Placement | `engine/market_data/` (nuevo subdir) |

---

## Comandos Ejecutados

```bash
# Branch
git checkout -b feature/AG-3K-1-1_market_data_adapter

# Tests nuevos
pytest tests/test_market_data_fixture_adapter.py -v  # 10 passed

# Pytest global
pytest -q | tee report/pytest_3K1_market_data.txt

# Smoke test runner
python tools/run_live_3E.py --data fixture \
  --fixture-path tests/fixtures/ohlcv_fixture_3K1.csv \
  --outdir report/out_3K1_smoke --max-steps 5

# Commit
git commit -m 'AG-3K-1-1: MarketDataAdapter + Fixture adapter + tests'
```

---

## Tests

- **Nuevos tests**: 10 (test_market_data_fixture_adapter.py)
- **Pytest global**: 625 passed, 10 skipped, 7 warnings in 179.85s
- **Smoke test**: PASS (runner con `--data fixture`)

---

## Artefactos report/

| Archivo | Contenido |
|---------|-----------|
| `pytest_3K1_market_data.txt` | pytest output |
| `out_3K1_smoke/` | smoke test artifacts |
| `AG-3K-1-1_last_commit.txt` | commit hash |
| `AG-3K-1-1_diff.patch` | diffstat |
| `AG-3K-1-1_return.md` | este return packet |

---

## out_3K1_smoke/ Contents

```
events.ndjson     126 bytes
results.csv       198 bytes
run_meta.json     377 bytes
run_metrics.json  260 bytes
state.db          20 KB
```

---

## DoD Verificación

- ✅ pytest global PASS (625 passed)
- ✅ CLI runner acepta `--data fixture`
- ✅ git diff limpio tras commit
- ✅ Artefactos report generados

---

## AUDIT_SUMMARY

- **Ficheros nuevos**: 5
- **Ficheros modificados**: 1 (`tools/run_live_3E.py`)
- **Líneas añadidas**: 387
- **Líneas eliminadas**: 1
- **Commit**: 322f404
- **Branch**: feature/AG-3K-1-1_market_data_adapter
