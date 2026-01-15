# DS-3I-1-2: Auditoría Técnica - Simulated Monotonic Time Provider

## Hechos Verificados (basado en inputs)

### 1. Invariantes del Time Provider
- **Monotonicidad estricta**: ✅ Garantizada por `advance_ns()` y `advance_steps()` que solo incrementan `_now_ns`. Excepción ValueError para valores negativos.
- **Determinismo**: ✅ No depende de wallclock real. Misma secuencia de avances produce mismos resultados.
- **Overflow/límites**: ✅ Python int sin límite práctico. Conversión a float en `clock_fn()` puede perder precisión para tiempos >~100 días (3.15e16 ns), pero aceptable para simulaciones.
- **Reset behavior**: ✅ No hay reset; se crea nueva instancia con `start_ns`.
- **Concurrencia**: ✅ Asume single-thread (sin locks), coherente con diseño del bus.

### 2. Integración Loop/Metrics
- **Avance no duplicado**: ✅ Cada etapa avanza tiempo determinista antes de registrar `t_end`:
  - `strategy`: 1ms por barra (independiente de intents)
  - `risk`: 0.5ms por item procesado
  - `exec`: 2ms por item procesado  
  - `position`: 0.3ms por item procesado
- **Latencia por item**: ✅ Intencional y consistente (multiplicación por `*processed`).
- **Registro de stage**: ✅ `strategy` se registra una vez por barra (no por intent), con outcomes `ok`/`no_signal`. No afecta semántica.
- **Contratos/serialización**: ✅ No se modifican contratos de eventos V1.

### 3. Tests
- **Suficiencia mínima**: ✅ 8 tests para time provider + 6 tests para latencias non-zero y determinismo.
- **Flakiness**: ✅ Deterministas (semillas fijas, sin wallclock).
- **Asserts correctos**: ✅ Verifican `p50_ms > 0`, igualdad de diccionarios para determinismo.

### 4. Smoke Evidence (metrics_summary.json)
- **Coherencia counts**: 
  - `strategy`: 20 barras = 17 `no_signal` + 3 `ok` ✓
  - `risk`: 1 evento de etapa (puede representar múltiples items procesados)
- **Latencias >0**: ✅ Todas positivas (1.0, 1.5, 6.0, 0.9 ms).
- **Reproducibilidad**: ✅ Testeada en `test_determinism_simulated`.

## Riesgos / Edge-cases

### Prioridad Alta
- **Ninguno crítico** identificado.

### Prioridad Media
1. **Discrepancia en valores de latencia**:
   - `risk`: Esperado 0.5ms por item → observado 1.5ms (factor ×3)
   - `exec`: Esperado 2ms por item → observado 6ms (factor ×3)
   - **Posible causa**: Workers procesan múltiples items por step (`risk_processed=3`, `exec_processed=3`).
   - **Impacto**: No es error si el diseño permite procesar batch de items. Requiere verificación.

2. **Registro de `strategy` fuera del loop de intents**:
   - ✅ Correcto: una vez por barra.
   - ⚠️ `outcome="no_signal"` cuando no hay intents puede confundir con error (es comportamiento normal).

3. **Dependencia de `hasattr(self.time_provider, 'advance_ns')`**:
   - ✅ Funciona con `SimulatedTimeProvider`.
   - ⚠️ Si se usa otro provider sin `advance_ns`, no se avanzará tiempo (latencia cero).

### Prioridad Baja
1. **Precisión float en `clock_fn()`**: 
   - `now_ns()/1e9` puede perder precisión para tiempos >~100 días (rango improbable).

2. **Falta de locks**: Solo aplicable si futuro diseño usa multi-hilo.

## Recomendaciones Accionables

### Cambios Puntuales
1. **Documentar comportamiento de batch processing**:
   ```python
   # En loop_stepper.py, cerca de STAGE_LATENCY_NS:
   # NOTA: Las latencias risk/exec/position se multiplican por el número de items
   # procesados en cada step (puede ser >1 si hay backlog en la cola).
   ```

2. **Añadir test de verificación de latencias específicas**:
   ```python
   # tests/test_metrics_latencies_nonzero_simulated.py
   def test_latencies_match_expected_ns(self):
       """Verify recorded latencies match STAGE_LATENCY_NS * processed."""
       # Setup time_provider, collector, stepper
       # Mock workers to control processed counts
       # Run simulation and assert t1-t0 == expected_ns
   ```

3. **Renombrar outcome "no_signal" a "skip"** (opcional):
   ```python
   outcome = "ok" if intents else "skip"  # más claro que "no_signal"
   ```

### Tests Extra Sugeridos
1. **Edge case: time_provider sin advance_ns**:
   ```python
   def test_no_advance_ns_fallback(self):
       """Should not crash if time_provider lacks advance_ns."""
       class DummyProvider:
           def now_ns(self): return 0
       stepper = LoopStepper(time_provider=DummyProvider())
       # Run simple simulation, verify no exception
   ```

2. **Verificación overflow** (baja prioridad):
   ```python
   def test_very_large_advance_ns(self):
       """advance_ns with large value should not break clock_fn."""
       provider = SimulatedTimeProvider(start_ns=10**18)  # ~32 años
       provider.advance_ns(10**18)
       # clock_fn should return float without overflow
   ```

## Checklist de Merge

- [x] **Tests pasan**: 534 passed, 10 skipped (reportado)
- [x] **Smoke test muestra latencias >0**: metrics_summary.json confirma
- [x] **No breaking changes**: Interfaces existentes intactas
- [x] **Documentación**: Comentarios en código adecuados
- [ ] **Discrepancia latencias investigada**: ❓ Requiere confirmación de diseño (batch processing)
- [x] **Determinismo verificado**: Tests cross-run pasan

## Veredicto

**CONDITIONAL** (con recomendaciones)

La implementación cumple con los requisitos principales:
1. ✅ Monotonicidad estricta garantizada
2. ✅ Determinismo completo (sin wallclock)
3. ✅ Latencies non-zero en simulated mode
4. ✅ Integración correcta con métricas

**Condición para PASS definitivo**:
- Confirmar que las discrepancias de latencia (risk 1.5ms vs 0.5ms esperado) son por diseño (batch processing de múltiples items por step) mediante:
  - Documentación clara en código O
  - Test que verifique la relación `latencia = STAGE_LATENCY_NS * processed`

Si se confirma que el batch processing es intencional, cambiar veredicto a **PASS**. La implementación es sólida y los tests cubren los casos críticos.

---

**Nota para el equipo**: Las discrepancias numéricas observadas son probables debido a que `risk_worker.step(bus, max_items=100)` procesa todos los items pendientes en la cola (no solo uno por barra). Esto es comportamiento esperado en bus mode. Recomiendo añadir un comentario explicando esto en `loop_stepper.py`.