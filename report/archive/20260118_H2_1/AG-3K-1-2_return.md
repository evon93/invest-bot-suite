# AG-3K-1-2 Return Packet

**Ticket**: AG-3K-1-2 — MarketDataAdapter hardening (schema/no-lookahead/exhaust/gaps/nans)  
**Fecha**: 2026-01-13T20:15:00+01:00  
**Status**: ✅ PASS

---

## Firma Final `poll()`

```python
def poll(
    self, 
    max_items: int = 100, 
    up_to_ts: Optional[int] = None
) -> List[MarketDataEvent]:
    """
    Fetch next batch of market data events.
    
    Args:
        max_items: Maximum number of events to return (default: 100).
        up_to_ts: Optional upper bound timestamp (epoch ms UTC).
                  If provided, only events with ts <= up_to_ts are returned.
                  Events beyond up_to_ts remain buffered for future polls.
                  
    Returns:
        List of MarketDataEvent in non-decreasing ts order.
        Returns empty list [] when exhausted (EOF).
        
    Contract:
        - len(result) <= max_items
        - All events satisfy: event.ts <= up_to_ts (if up_to_ts provided)
        - Events are ordered: result[i].ts <= result[i+1].ts
    """
```

---

## Semántica EOF/No-Lookahead

| Comportamiento | Definición |
|----------------|------------|
| **EOF** | `poll()` retorna `[]` cuando no hay más eventos. Llamadas posteriores continúan retornando `[]`. Sin excepciones. |
| **No-Lookahead** | Con `up_to_ts=X`, solo se emiten eventos con `ts <= X`. Eventos futuros quedan buffered para próximos polls. |
| **is_exhausted()** | Nuevo método para verificar estado EOF sin consumir. |
| **peek_next_ts()** | Nuevo método para ver ts del próximo evento sin consumir. |

---

## Paths Tocados

| Archivo | Acción |
|---------|--------|
| `engine/market_data/market_data_adapter.py` | MODIFIED (Protocol clarificado) |
| `engine/market_data/fixture_adapter.py` | MODIFIED (schema, up_to_ts, gaps) |
| `tests/test_market_data_fixture_adapter.py` | MODIFIED (+14 tests hardening) |

---

## Tests Nuevos (AG-3K-1-2)

| Test | Categoría |
|------|-----------|
| `test_poll_up_to_ts_respects_boundary` | no-lookahead |
| `test_poll_up_to_ts_blocks_future_events` | no-lookahead |
| `test_poll_up_to_ts_buffers_future_events` | no-lookahead |
| `test_eof_returns_empty_list_not_exception` | EOF |
| `test_is_exhausted_flag` | EOF |
| `test_peek_next_ts_returns_none_at_eof` | EOF |
| `test_schema_rejects_negative_prices` | schema |
| `test_schema_rejects_invalid_ohlc_high_low` | schema |
| `test_schema_strict_false_allows_minor_issues` | schema |
| `test_gaps_detected_in_fixture` | gaps |
| `test_no_gaps_in_regular_fixture` | gaps |
| `test_nan_in_ohlcv_raises_error` | NaNs |
| `test_utc_conversion_from_offset_timezone` | UTC |
| `test_utc_epoch_ms_is_integer` | UTC |

---

## Resultados

| Métrica | Valor |
|---------|-------|
| **pytest global** | 639 passed, 10 skipped, 7 warnings |
| **Tiempo** | 177.58s |
| **Commit** | e298c49 |

---

## DoD Verificación

- ✅ pytest -q | tee report/pytest_3K1_2_market_data_hardening.txt → PASS
- ✅ Firma final poll() documentada con up_to_ts
- ✅ Semántica EOF/no-lookahead definida
- ✅ git diff --stat limpio tras commit

---

## AUDIT_SUMMARY

- **Ficheros modificados**: 3
- **Líneas añadidas**: 388
- **Líneas eliminadas**: 29
- **Commit**: e298c49
- **Branch**: feature/AG-3K-1-1_market_data_adapter
