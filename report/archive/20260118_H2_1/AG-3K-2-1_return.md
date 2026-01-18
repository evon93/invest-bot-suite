# AG-3K-2-1 Return Packet

**Ticket**: AG-3K-2-1 — CCXT sandbox MarketData feed (gated) + tests (no network in CI)  
**Fecha**: 2026-01-13T20:52:00+01:00  
**Status**: ✅ PASS

---

## Implementación

### CCXTMarketDataAdapter

```python
class CCXTMarketDataAdapter:
    def __init__(
        self,
        client: OHLCVClient,  # Inyectable para testing
        config: CCXTConfig,
        allow_network: bool = False  # Gating
    )
    
    def poll(max_items, up_to_ts) -> List[MarketDataEvent]
```

**Gating:**

- `--allow-network` flag (default: False)
- `INVESTBOT_ALLOW_NETWORK=1` env var
- Sin gating → `NetworkDisabledError` explícito

### OHLCVClient Protocol

```python
class OHLCVClient(Protocol):
    def fetch_ohlcv(symbol, timeframe, since, limit) -> List[List]
```

### MockOHLCVClient

Mock determinista para tests sin red (seed42).

---

## CLI Wiring

```bash
python tools/run_live_3E.py \
  --data ccxt \
  --allow-network \
  --ccxt-exchange binance \
  --ccxt-symbol BTC/USDT \
  --ccxt-timeframe 1h \
  --ccxt-limit 100
```

**Comportamiento:**

- Sin `--allow-network`: error con mensaje claro y exit(1)
- Con `--allow-network` + ccxt no instalado: fallback a MockOHLCVClient

---

## Paths Tocados

| Archivo | Acción |
|---------|--------|
| `engine/market_data/__init__.py` | MODIFIED |
| `engine/market_data/ccxt_adapter.py` | NEW |
| `tests/test_ccxt_adapter.py` | NEW |
| `tools/run_live_3E.py` | MODIFIED |

---

## Tests (16 nuevos)

| Test | Categoría |
|------|-----------|
| `test_deterministic_data_generation` | MockClient |
| `test_different_seeds_produce_different_data` | MockClient |
| `test_fetch_respects_since_filter` | MockClient |
| `test_fetch_respects_limit` | MockClient |
| `test_poll_returns_market_data_events` | Adapter |
| `test_poll_events_have_correct_symbol` | Adapter |
| `test_poll_monotonic_timestamps` | Adapter |
| `test_poll_up_to_ts_blocks_future` | no-lookahead |
| `test_poll_respects_max_items` | Adapter |
| `test_exhaustion_returns_empty_list` | EOF |
| `test_network_disabled_raises_error` | Gating |
| `test_env_var_enables_network` | Gating |
| `test_allow_network_flag_enables` | Gating |
| `test_error_message_includes_instructions` | Gating |
| `test_ccxt_without_allow_network_fails` | Runner |
| `test_ccxt_with_allow_network_runs` | Runner |

---

## Resultados

| Métrica | Valor |
|---------|-------|
| **pytest global** | 655 passed, 10 skipped, 7 warnings |
| **Tiempo** | 168.84s |
| **Commit** | 845962e |
| **Branch** | feature/AG-3K-2-1_ccxt_gated_feed |

---

## out_3K2_smoke/

```
events.ndjson     1313 bytes
results.csv        198 bytes
run_meta.json      340 bytes
run_metrics.json   260 bytes
state.db          20 KB
```

---

## DoD Verificación

- ✅ pytest global PASS
- ✅ No llamadas de red en tests (solo mocks)
- ✅ Gating comprobado por tests
- ✅ Return Packet completo

---

## AUDIT_SUMMARY

- **Ficheros nuevos**: 2
- **Ficheros modificados**: 2
- **Líneas añadidas**: 730
- **Líneas eliminadas**: 6
- **Commit**: 845962e
- **Branch**: feature/AG-3K-2-1_ccxt_gated_feed
