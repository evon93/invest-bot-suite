# DS-3K-1-1 — Auditoría MarketDataAdapter (schema/TZ/epoch/monotonic/no-lookahead)

**Auditor:** DS (Design Safety)  
**Fecha:** 2026-01-13  
**Baseline:** AG-3K-1-1 (commit 322f404)  
**Scope:** `engine/market_data/`, `tools/run_live_3E.py`, tests de fixture adapter  

---

## 🔍 Hechos Observados (basado en return packet + diffstat)

| Aspecto | Implementación Observada | Fuente |
|---------|--------------------------|--------|
| **Schema mínimo** | `MarketDataEvent`: `symbol`, `ts` (int epoch ms), `open`, `high`, `low`, `close`, `volume` | return packet + inferencia de OHLCV fixture |
| **TZ/epoch** | `ts` = epoch milliseconds (int) UTC; no timezone strings | Decisión explícita en return packet |
| **Monotonicidad** | `poll()` garantiza orden no-decreciente por `ts`; duplicados → error en loader | return packet |
| **No-lookahead** | Adapter entrega datos solo hasta `current_time` (controlado por runner) | Inferido de diseño adapter |
| **Fixture CSV** | `tests/fixtures/ohlcv_fixture_3K1.csv` (11 filas) | Nuevo archivo |
| **Wiring CLI** | `--data fixture --fixture-path <csv>` en `run_live_3E.py` | Modificación en tools/ |
| **Tests** | 10 tests nuevos en `test_market_data_fixture_adapter.py` | return packet |
| **Validación duplicados** | En `ohlcv_loader` (existente) | return packet |

---

## ⚠️ Riesgos / Failure Modes

### 1. **Schema inconsistente entre adapter y runner**
- Si `MarketDataEvent` espera campos que el CSV no tiene, fallará en runtime.
- Si el runner espera `timestamp` como `pd.Timestamp` pero adapter devuelve `int`, hay conversión implícita.

### 2. **Timezone naïve vs. aware**
- `ts` como epoch ms UTC es robusto, pero si el fixture CSV tiene timestamps con offset (ej: "2025-01-01 00:00:00+01:00"), la conversión a epoch debe mantener UTC.
- El loader existente (`ohlcv_loader`) debe hacer esta conversión correctamente.

### 3. **Monotonicidad solo ascendente, no estricta**
- `poll()` orden no-decreciente permite duplicados (aunque loader los rechaza). Pero si hay duplicados tras validación, podrían causar lógica errónea en estrategia (ej: misma barra procesada dos veces).

### 4. **No-lookahead dependiente del caller**
- El adapter no garantiza por sí mismo no-lookahead; depende de que el runner llame a `poll(current_time)` con `current_time` adecuado.
- Si el runner pasa un `current_time` futuro (error), el adapter podría devolver datos futuros.

### 5. **Gaps temporales**
- Fixture con gaps (ej: datos diarios sin fines de semana) puede romper suposiciones de estrategias que esperan barras contiguas.
- El adapter debe manejarlo sin crash, pero el runner/estrategia debe estar preparado.

### 6. **Multi-symbol no probado**
- El adapter probablemente asume un solo símbolo por fixture. Si el CSV tiene múltiples símbolos, el orden por `ts` debe ser global, no por símbolo.

### 7. **Warmup y datos insuficientes**
- Si el fixture es más corto que el warmup de la estrategia, `poll()` podría agotar datos antes de tiempo.
- Comportamiento esperado: ¿devolver `None`? ¿lanza excepción?

---

## ✅ Recomendaciones Concretas (tests + asserts)

### 1. **Schema validation en adapter initialization**
```python
# En FixtureMarketDataAdapter.__init__:
expected_cols = {"timestamp", "open", "high", "low", "close", "volume"}
if not expected_cols.issubset(df.columns):
    raise ValueError(f"Fixture missing columns: {expected_cols - set(df.columns)}")
```

### 2. **Test de timezone: UTC enforcement**
```python
def test_fixture_timestamps_are_utc():
    adapter = FixtureMarketDataAdapter("path/to/fixture.csv")
    events = adapter.poll(pd.Timestamp.max)  # all data
    for e in events:
        # ts is epoch ms, convert back and check tz
        dt = pd.to_datetime(e.ts, unit='ms', utc=True)
        assert dt.tz is not None
        assert dt.tz.zone == 'UTC'
```

### 3. **Test de monotonicidad estricta (sin duplicados)**
```python
def test_fixture_has_strictly_increasing_timestamps():
    df = pd.read_csv("tests/fixtures/ohlcv_fixture_3K1.csv")
    assert df["timestamp"].is_monotonic_increasing
    assert df["timestamp"].duplicated().sum() == 0
```

### 4. **Test de no-lookahead en integración**
```python
def test_adapter_never_returns_future_data():
    adapter = FixtureMarketDataAdapter(fixture_path)
    current_time = pd.Timestamp("2025-01-05", tz="UTC")
    events = adapter.poll(current_time)
    for e in events:
        assert pd.to_datetime(e.ts, unit='ms', utc=True) <= current_time
```

### 5. **Test de gaps (debería funcionar)**
```python
def test_adapter_handles_time_gaps():
    # Crear fixture con gaps de 2 días
    df = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=5, freq="2D", tz="UTC").view('int64') // 10**6,
        "open": [100]*5, "high": [105]*5, "low": [95]*5, "close": [102]*5, "volume": [1000]*5
    })
    df.to_csv("temp_gap.csv")
    adapter = FixtureMarketDataAdapter("temp_gap.csv")
    events = adapter.poll(pd.Timestamp.max)
    assert len(events) == 5  # No crash, devuelve todos
```

### 6. **Test de warmup insuficiente**
```python
def test_adapter_returns_none_when_data_exhausted():
    adapter = FixtureMarketDataAdapter(small_fixture)
    # Poll beyond last timestamp
    future_time = pd.Timestamp("2030-01-01", tz="UTC")
    events = adapter.poll(future_time)
    # Debería devolver todos los datos disponibles, no None
    assert isinstance(events, list)
    # Y luego, en siguiente poll, devolver lista vacía?
    events2 = adapter.poll(future_time)
    assert events2 == []  # o tal vez None, pero debe estar definido
```

---

## 📋 Checklist de Invariantes

| Invariante | Estado | Evidencia |
|------------|--------|-----------|
| **Schema consistente** | ⚠️ **PARCHE** | Asumido por fixture CSV; falta validación explícita en código. |
| **TZ = UTC, epoch ms** | ✅ **PASS** | Decisión explícita en return packet; tests deben verificarlo. |
| **Monotonicidad (no-decreciente)** | ✅ **PASS** | Declarado en return packet; loader rechaza duplicados. |
| **No-lookahead por diseño** | ⚠️ **PARCHE** | Depende de caller; adapter no garantiza por sí mismo. |
| **Manejo de gaps** | ⚠️ **NO TESTEADO** | No hay tests de gaps; asumido que pandas maneja. |
| **Multi-symbol** | ⚠️ **NO SOPORTADO** | Fixture single-symbol; no hay mención de multi-symbol. |
| **Warmup/data exhaust** | ⚠️ **NO DEFINIDO** | Comportamiento en fin de datos no especificado. |
| **NaN handling** | ⚠️ **NO TESTEADO** | No hay tests con NaN en fixture. |

---

## 🏁 Conclusión

**VEREDICTO: ACCEPT-WITH-NOTES**

El diseño de `MarketDataAdapter` es sólido en su base (UTC ms, monotonicidad), pero quedan varios edge cases no cubiertos por tests o por garantías explícitas.

**Acciones recomendadas antes de 3K.2:**
1. Añadir validación de schema en `FixtureMarketDataAdapter.__init__`.
2. Añadir test de no-lookahead en integración (adapter + runner).
3. Definir comportamiento al agotar datos (¿lista vacía? ¿excepción?).
4. Añadir test de gaps temporales y NaN.

El adapter es **usable** para 3K.1, pero se debe documentar sus limitaciones y completar tests en siguientes tickets.