# DS-3I-3-1: Auditoría Técnica - Metrics Rotate Keep

## Resumen de Implementación

Se ha implementado la funcionalidad `--metrics-rotate-keep N` para retener solo los N archivos rotados más recientes de `metrics.ndjson`. La implementación se encuentra en:

1. **`engine/metrics_collector.py`**: `MetricsWriter` con nuevo parámetro `rotate_keep` y método `_cleanup_rotated()`
2. **`tools/run_live_3E.py`**: Nuevo argumento CLI `--metrics-rotate-keep` y wiring correspondiente

## Análisis de Edge Cases

### 1. Patrón de Glob y Protección del Archivo Activo

**Implementación actual:**
```python
pattern = "metrics.ndjson.*"
for p in self._run_dir.glob(pattern):
    suffix = p.suffix.lstrip(".")
    if suffix.isdigit():
        rotated_files.append((int(suffix), p))
```

**Protecciones incluidas:**
- ✅ El glob `metrics.ndjson.*` excluye automáticamente el archivo activo `metrics.ndjson` (sin sufijo)
- ✅ Filtro `.isdigit()` evita archivos con sufijos no-numéricos (`backup`, `temp`, etc.)
- ✅ El archivo activo se reabre después de la rotación, asegurando que no sea eliminado

**Riesgo identificado:** Ninguno crítico. El patrón es seguro.

### 2. Ordenación de "Más Recientes"

**Estrategia actual:** Ordenación por sufijo numérico descendente (mayor = más reciente)

**Ventajas:**
- Determinista y reproducible
- No depende de `mtime` del filesystem (puede variar)
- Coherente con el esquema de numeración secuencial

**Limitaciones:**
- Si se eliminan archivos manualmente, puede haber huecos en la numeración
- En sistemas distribuidos, podría haber conflictos (no aplicable aquí)

**Recomendación:** Mantener la aproximación actual. Es la más simple y apropiada para el caso de uso.

### 3. Riesgos de Concurrencia

**Contexto:** Sistema single-threaded, single-process. No hay locks explícitos.

**Riesgos potenciales:**
1. **Race condition durante glob + delete**: Otro proceso podría crear un archivo entre el glob y el delete
2. **Error en delete**: Se maneja con try/except por archivo (best-effort)
3. **Rotación simultánea**: No aplicable (un solo writer)

**Protecciones actuales:**
- ✅ Best-effort individual por archivo
- ✅ No se propaga excepción si falla un delete

**Recomendación:** Documentar que no es thread-safe ni process-safe. Adecuado para el diseño actual.

## Tests Adicionales Recomendados

### 1. Test de keep mayor que archivos existentes
```python
def test_keep_greater_than_existing_files(self):
    """Cuando keep > archivos rotados, no debe eliminar ninguno."""
    writer = MetricsWriter(run_dir=tmpdir, rotate_keep=10)
    # Crear solo 3 archivos rotados
    for i in range(1, 4):
        (tmpdir / f"metrics.ndjson.{i}").touch()
    writer._cleanup_rotated()
    # Deben quedar los 3
    assert len(list(tmpdir.glob("metrics.ndjson.*"))) == 3
```

### 2. Test con nombres de archivo inusuales
```python
def test_unusual_filenames_preserved(self):
    """Archivos con sufijos no-numéricos o formato diferente no deben tocarse."""
    writer = MetricsWriter(run_dir=tmpdir, rotate_keep=1)
    # Archivos que NO deben ser eliminados
    special_files = [
        "metrics.ndjson.backup",
        "metrics.ndjson.temp",
        "metrics.ndjson.old",
        "otherfile.txt",
        "metrics.json",  # Sin .ndjson
    ]
    for fname in special_files:
        (tmpdir / fname).touch()
    writer._cleanup_rotated()
    # Todos los especiales deben permanecer
    for fname in special_files:
        assert (tmpdir / fname).exists()
```

### 3. Test de directorio vacío/no existente
```python
def test_cleanup_empty_directory(self):
    """No debe fallar si no hay archivos rotados."""
    writer = MetricsWriter(run_dir=tmpdir, rotate_keep=2)
    # Directorio vacío
    writer._cleanup_rotated()
    # No debe lanzar excepción
    assert True
```

### 4. Test de múltiples rotaciones secuenciales
```python
def test_multiple_rotations_with_keep(self):
    """Simular varias rotaciones y verificar que se mantiene keep correcto."""
    writer = MetricsWriter(run_dir=tmpdir, rotate_keep=3, 
                          rotate_max_lines=10)  # Rotar cada 10 líneas
    
    # Escribir para forzar 5 rotaciones
    for i in range(50):
        writer.append_event({"event": i})
    
    # Deberían quedar máximo 3 archivos rotados + el activo
    rotated = list(tmpdir.glob("metrics.ndjson.[0-9]*"))
    assert len(rotated) <= 3
```

### 5. Test de keep=0 con archivos existentes
```python
def test_keep_zero_deletes_all_rotated(self):
    """keep=0 debe eliminar todos los archivos rotados."""
    writer = MetricsWriter(run_dir=tmpdir, rotate_keep=0)
    
    # Crear algunos archivos rotados
    for i in range(1, 6):
        (tmpdir / f"metrics.ndjson.{i}").touch()
    
    writer._cleanup_rotated()
    
    # No debe haber archivos rotados
    assert len(list(tmpdir.glob("metrics.ndjson.[0-9]*"))) == 0
    # Pero el activo (si existe) debe permanecer
```

## Checklist de Merge

### Requisitos Funcionales
- [x] Flag `--metrics-rotate-keep N` funciona en CLI
- [x] Retiene solo N archivos más recientes
- [x] No elimina el archivo activo `metrics.ndjson`
- [x] No elimina archivos con sufijos no-numéricos
- [x] Best-effort en eliminación (errores no rompen el flujo)

### Calidad de Código
- [x] Tests existentes cubren casos básicos (keep=2, keep=0, keep=None)
- [x] Manejo de errores adecuado (try/except por archivo)
- [x] Documentación en docstrings

### Seguridad y Robustez
- [x] No hay vulnerabilidades de path traversal (usa Path de pathlib)
- [x] Filtrado adecuado de sufijos (solo numéricos)
- [x] No depende de timestamps del filesystem

## Recomendaciones Concretas

### 1. Añadir logging para depuración (opcional)
```python
import sys
def _cleanup_rotated(self):
    # ...
    for suffix, path in to_delete:
        try:
            path.unlink()
            # Opcional: sys.stderr.write(f"Deleted old metrics: {path.name}\n")
        except OSError as e:
            # Opcional: sys.stderr.write(f"Could not delete {path}: {e}\n")
            pass
```

### 2. Documentar limitaciones de concurrencia
Añadir en la docstring de `MetricsWriter`:
```
Note: This class is not thread-safe or multi-process safe. It assumes
a single process is writing to the metrics directory.
```

### 3. Considerar límite máximo de archivos por seguridad
Podría añadirse un límite máximo (ej. 1000) para prevenir DoS accidental:
```python
if self._rotate_keep > 1000:
    raise ValueError("rotate_keep cannot exceed 1000 for safety")
```

## Veredicto

**PASS** con recomendaciones menores.

La implementación cumple con los requisitos del ticket y maneja adecuadamente los edge cases principales. Los tests existentes son suficientes, aunque se podrían añadir algunos tests adicionales para mayor robustez (especialmente para keep=0 y archivos inusuales).

La arquitectura es simple y efectiva, adecuada para el caso de uso de retención de métricas rotadas.