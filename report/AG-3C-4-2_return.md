# AG-3C-4-2 Return Packet — SQLite Position Store Hardening

**Fecha:** 2026-01-04  
**Ticket:** AG-3C-4-2 (WSL + venv)  
**Rama:** `feature/3C_4_2_sqlite_hardening`  
**Estado:** ✅ COMPLETADO

---

## 1. Cambios Implementados

### `state/position_store_sqlite.py`

| Cambio | Descripción |
|--------|-------------|
| **`_compute_new_position()`** | Helper para calcular qty/avg_price con semántica DS |
| **`apply_fill()` transaccional** | Usa `with conn:` para atomicidad read→calc→write |
| **Validación inputs** | qty>0, price>0, side BUY/SELL, symbol no vacío |
| **Short increase** | SELL sobre short recalcula avg weighted |
| **Cross long→short** | avg_price = fill price |
| **Cross short→long** | avg_price = fill price |
| **Partial cover** | Mantiene avg_price |
| **meta_json determinista** | `json.dumps(meta, sort_keys=True, separators=(',',':'))` |

---

## 2. Semántica `_compute_new_position()`

```python
# 1. Flat → Open: avg = fill_price
# 2. Increasing (same sign): weighted avg
# 3. Reducing (opposite, no cross): keep avg
# 4. Cross (sign flip): avg = fill_price
# 5. Full close: qty=0, avg=None
```

---

## 3. Tests Nuevos

| Test | Descripción |
|------|-------------|
| `test_short_increase_recalculates_avg` | SELL sobre short → weighted avg |
| `test_long_to_short_cross_uses_fill_price` | Cross → avg = fill price |
| `test_short_to_long_cross_uses_fill_price` | Cross → avg = fill price |
| `test_partial_cover_short_keeps_avg` | Partial cover → mantiene avg |
| `test_price_zero_raises` | price<=0 → ValueError |
| `test_empty_symbol_raises` | symbol vacío → ValueError |
| `test_meta_json_deterministic` | Verifica sort_keys en JSON |

**pytest total:** 308 passed, 7 skipped

---

## 4. Commit

```
9256117 3C.4.2: harden sqlite position store (shorts, crosses, atomicity, deterministic meta)
```

---

## 5. Artefactos

- [AG-3C-4-2_pytest.txt](AG-3C-4-2_pytest.txt)
- [AG-3C-4-2_diff.patch](AG-3C-4-2_diff.patch)
- [AG-3C-4-2_last_commit.txt](AG-3C-4-2_last_commit.txt)
