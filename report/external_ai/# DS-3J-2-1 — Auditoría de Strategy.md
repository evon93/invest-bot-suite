# DS-3J-2-1 — Auditoría de Strategy v0.8 (EMA Crossover)

**Auditor:** DS (Design Safety)  
**Fecha:** 2026-01-12  
**Baseline:** AG-3J-2-1 (commit `ea126b5`)  
**Scope:** Strategy v0.8 determinista + tests de no-lookahead  

---

## 🏁 VEREDICTO: **PASS**

La implementación cumple con los requisitos de determinismo, no-lookahead, warmup y manejo de NaN. Los tests son exhaustivos y cubren los casos críticos.

---

## 🔍 Hallazgos

| Área | Estado | Severidad | Observación |
|------|--------|-----------|-------------|
| **No-lookahead real** | ✅ | CRÍTICO | Slicing `df.loc[:asof_ts]` correcto; no usa datos futuros. |
| **Determinismo** | ✅ | CRÍTICO | Sin RNG, sin wallclock, sin estado global mutable. |
| **Warmup** | ✅ | IMPORTANTE | Retorna `[]` si `len(df) < slow_period`; maneja borde exacto. |
| **NaN / datos sucios** | ✅ | IMPORTANTE | Retorna `[]` si EMAs tienen NaN; no crashea con columnas faltantes. |
| **Tests de lookahead** | ✅ | IMPORTANTE | Tests `test_output_invariant_appending_future` y `test_future_data_does_not_affect_signal` capturan invariancia correctamente. |
| **Formato de entrada** | ⚠️ | NON-BLOCKER | Asume columna `timestamp` para setear índice. Compatible con v0.7, pero podría fallar si runner cambia formato. |

---

## 🧪 Tests Extra Sugeridos (no bloqueantes)

### 1. **Timestamp no alineado**  
Verificar comportamiento cuando `asof_ts` no coincide exactamente con un índice del DataFrame.

```python
def test_asof_ts_not_in_index():
    """Cuando asof_ts no está en el índice, debe usar último bar <= asof_ts."""
    df = make_ohlcv([100]*20)
    # asof_ts entre dos timestamps
    asof_ts = df["timestamp"].iloc[-1] + pd.Timedelta(minutes=30)
    result = generate_order_intents(df, {"fast_period":5, "slow_period":13}, "BTC-USD", asof_ts)
    # No debe crashear; comportamiento definido (puede ser [] o señal basada en último bar disponible)
    assert isinstance(result, list)
```

### 2. **Gaps en datos**  
EMA con gaps temporales (ej: fines de semana en daily).

```python
def test_ema_with_time_gaps():
    """EMA debe ser estable incluso con gaps en el índice temporal."""
    dates = pd.date_range("2025-01-01", periods=10, freq="D", tz="UTC")
    # Eliminar algunos días (gap)
    dates = dates.drop(dates[5])
    df = pd.DataFrame({
        "timestamp": dates,
        "close": np.random.randn(len(dates)) + 100,
    })
    asof_ts = df["timestamp"].iloc[-1]
    result = generate_order_intents(df, {"fast_period":3, "slow_period":5}, "BTC-USD", asof_ts)
    assert isinstance(result, list)
```

### 3. **Fast > Slow period swap**  
Ya está manejado en código (líneas 58-60), pero no testeado explícitamente.

```python
def test_fast_greater_than_slow_swap():
    """Si fast_period > slow_period, deben intercambiarse."""
    df = make_ohlcv([100]*30)
    params = {"fast_period": 20, "slow_period": 5}  # fast > slow
    result = generate_order_intents(df, params, "BTC-USD", df["timestamp"].iloc[-1])
    # No debe crashear; internamente los intercambia
    assert isinstance(result, list)
```

### 4. **Múltiples señales en mismo bar**  
Actualmente solo devuelve máximo una señal (BUY o SELL). Testear que no genera ambas.

```python
def test_no_contradictory_signals():
    """No debe generar BUY y SELL en el mismo bar."""
    # Crear datos donde ambas condiciones podrían activarse (raro pero posible)
    df = make_ohlcv([100]*30)
    # Forzar que fast_ema == slow_ema en prev y curr (no crossover)
    # Modificar EMAs directamente? Mejor test de integración.
    pass  # Opcional, baja prioridad.
```

---

## 📋 Recomendaciones Mínimas

1. **Documentar contrato de índice**  
   Agregar en docstring: “Requiere columna `timestamp` o índice DatetimeIndex. Si existe columna `timestamp`, se usará como índice.”

2. **Manejo de timezone**  
   El código asume que `asof_ts` tiene timezone (UTC). Si el runner pudiera pasar timestamps naïve, podría fallar en comparaciones. Ya hay test con `tz="UTC"`; mantener así.

3. **Línea duplicada en loop_stepper**  
   Ya observado en DS-3J-1-1; corregir en próximo commit de mantenimiento.

---

## ✅ Conclusión

La estrategia v0.8 es **determinista, libre de lookahead y robusta** ante datos insuficientes o sucios.  
Los tests cubren los casos críticos y son de calidad.  
**Aprobado para continuar con PASO 3J.3.**