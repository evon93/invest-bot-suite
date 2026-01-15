# DS-3I-1-1: Auditoría Técnica - Monotonic Time Provider

## Findings

### ✅ **1. now_utc() - Tz-aware UTC en implementaciones principales**
- **SystemTimeProvider**: `datetime.now(timezone.utc)` → correcto, siempre tz-aware
- **SimulatedTimeProvider**: Calculado desde `epoch_utc` (tz-aware por defecto) + `timedelta` → mantiene tz-aware
- **FrozenTimeProvider**: Campo `frozen_utc` inicializado con `tzinfo=timezone.utc`

### ⚠️ **2. FrozenTimeProvider.set_utc() acepta datetime naive**
```python
def set_utc(self, dt: datetime) -> None:
    self.frozen_utc = dt  # No valida tzinfo
```
- **Riesgo**: Si se pasa datetime naive, código downstream que asume UTC podría fallar
- **Impacto**: Bajo (solo en tests manuales), pero podría causar bugs sutiles

### ✅ **3. monotonic_ns() usa fuentes correctas**
- **SystemTimeProvider**: `time.monotonic_ns()` → portable (Python ≥3.3)
- **Frozen/Simulated**: Implementaciones deterministas con validación `delta_ns ≥ 0`

### ⚠️ **4. SimulatedTimeProvider fusiona monotonic_ns() y now_ns()**
```python
def monotonic_ns(self) -> int:
    return self._now_ns  # Mismo que now_ns()
```
- **Semántica**: En sistemas reales, `monotonic_ns()` y `time.time_ns()` son relojes diferentes
- **Justificación**: Para simulación es aceptable, pero debe documentarse

### ❌ **5. Singleton sin reset entre tests - riesgo de flakiness**
```python
_global_time_provider: Optional[TimeProvider] = None
```
- **Problema**: Si un test establece `set_time_provider(FrozenTimeProvider())` y no restaura, tests siguientes usan provider incorrecto
- **Impacto**: Alto para tests paralelos o ejecución aleatoria

### ✅ **6. Advertencia thread-safety clara**
```python
# WARNING: Not thread-safe. Call at test setup/teardown only.
```
- **Adecuado**: Documentado explícitamente; el diseño actual es single-threaded

### ⚠️ **7. FrozenTimeProvider permite "time travel" en now_utc()**
- `set_utc()` puede establecer cualquier datetime (incluso retroceder)
- **Contrato**: `now_utc()` no requiere monotonicidad, pero timestamps que retroceden pueden confundir métricas/ordenamiento

### ✅ **8. Backward compatibility preservada**
- **RealTimeProvider** marcado como deprecated, pero mantiene interfaz
- **Nuevos métodos** son adiciones, no rompen código existente

## Riesgos de Determinismo

### Alto
- **Singleton global en tests**: Tests que cambian provider y no lo restauren causarán non-determinismo cross-test

### Medio
- **SimulatedTimeProvider monotonic_ns = now_ns**: Si código futuro usa monotonic_ns para latencias y now_ns para timestamps, en simulación serán idénticos (podría enmascarar bugs)

### Bajo
- **FrozenTimeProvider.set_utc() naive datetime**: Solo afecta tests manuales que usen esta API

## Riesgos Semánticos

### UTC/monotonic
- **now_utc()**: No garantiza monotonicidad (correcto, es wall-clock)
- **monotonic_ns()**: Garantiza monotonicidad (correcto)
- **Confusión potencial**: Desarrolladores podrían usar `now_utc()` para calcular duraciones (incorrecto)

### Edge Cases
- **Overflow**: Python int sin límite práctico, pero `timedelta(seconds=elapsed_seconds)` con `elapsed_seconds` muy grande podría overflow (extremadamente improbable)
- **Negative deltas**: Validados en `advance_ns()` y `advance_monotonic_ns()`
- **Conversiones float**: `SimulatedTimeProvider.now_utc()` divide `_now_ns / 1e9` → posible pérdida de precisión para tiempos >100 días

## Recomendaciones Concretas

### 1. Validar tzinfo en FrozenTimeProvider.set_utc()
```python
def set_utc(self, dt: datetime) -> None:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    self.frozen_utc = dt
```

### 2. Fixture pytest para reset automático del provider
```python
# conftest.py
import pytest
from engine.time_provider import set_time_provider

@pytest.fixture(autouse=True)
def reset_time_provider():
    """Reset global time provider before each test."""
    original = get_time_provider()
    yield
    set_time_provider(original if original is not None else None)
```

### 3. Documentar semántica de monotonic_ns() en simulación
```python
# En docstring de SimulatedTimeProvider.monotonic_ns():
"""
In simulated mode, monotonic_ns() returns the same value as now_ns().
This differs from real systems where monotonic and wall clocks are separate,
but is acceptable for deterministic simulation.
"""
```

### 4. Tests adicionales (sugeridos)
- **Test naive datetime**: Verificar que `set_utc(naive_dt)` levanta ValueError
- **Test singleton reset**: Verificar que tests independientes no se contaminen
- **Test monotonic ordering**: Llamadas repetidas a `monotonic_ns()` nunca decrecen
- **Test tz-aware**: `now_utc().tzinfo is not None` para todos los providers

## Tests Adicionales Sugeridos

```python
# tests/test_time_provider_3I1.py - Añadir
def test_set_utc_requires_timezone():
    provider = FrozenTimeProvider()
    naive_dt = datetime(2025, 1, 1, 0, 0, 0)  # Sin tzinfo
    with pytest.raises(ValueError, match="timezone-aware"):
        provider.set_utc(naive_dt)

def test_singleton_isolation():
    # Test 1: Establecer provider personalizado
    custom = FrozenTimeProvider()
    set_time_provider(custom)
    assert get_time_provider() is custom
    
    # Test 2: Restaurar a default
    set_time_provider(None)
    assert isinstance(get_time_provider(), SystemTimeProvider)

def test_monotonic_never_decreases():
    provider = SystemTimeProvider()
    times = [provider.monotonic_ns() for _ in range(10)]
    for i in range(1, len(times)):
        assert times[i] >= times[i-1], f"Monotonic decreased at step {i}"
```

## Veredicto

**ACCEPT-WITH-NOTES**

### Justificación
- ✅ Cambio aditivo, no rompe compatibilidad
- ✅ Contrato claro: `now_utc()` (wall-clock) vs `monotonic_ns()` (monotónico)
- ✅ Tests existentes pasan (14 tests específicos + 579 totales)
- ✅ Documentación adecuada de limitaciones (thread-safety)

### Condiciones para merge
1. **Alta prioridad**: Implementar fixture pytest o mecanismo para resetear provider entre tests
2. **Media prioridad**: Validar tzinfo en `FrozenTimeProvider.set_utc()`
3. **Baja prioridad**: Documentar que `SimulatedTimeProvider.monotonic_ns()` = `now_ns()`

### Nota final
La implementación establece una base sólida para centralización del tiempo. Los riesgos identificados son manejables y principalmente afectan el entorno de pruebas. Con las recomendaciones aplicadas, el sistema será robusto y determinista.