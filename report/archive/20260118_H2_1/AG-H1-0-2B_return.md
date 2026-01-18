# Return Packet: AG-H1-0-2B Codebase Metrics Snapshot

## 1. Contexto

- **Fecha**: 2026-01-16
- **Head**: `main` @ `44bd161`
- **Scope**: Snapshot de métricas antes de aplicar políticas de limpieza de H1.1.

## 2. Resumen de Métricas

### A. Líneas de Código (LOC)

| Bucket | Physical LOC | Effective Python (No comments/blanks) |
|---|---|---|
| **Total Tracked** | **433,540** | **24,042** (Total Python) |
| `src/` | 0 (*) | 0 (*) |
| `tests/` | 17,511 | 12,043 |
| `tools/` | 8,465 | 5,843 |
| `report/` | 391,966 (90.4%) | N/A (mostly txt/patch/md) |
| `other` | 15,598 | 6,156 |

(*) **Nota**: El proyecto no usa `src/`. El código productivo reside en raíz (`backtest_initial.py`, etc.), `engine/`, `bus/`, etc., contabilizado en `other` y `tools`.
**Total Productivo Estimado (Other + Tools)**: ~12,000 líneas efectivas de Python.

### B. Tamaño y Bloat

| Métrica | Valor | Notas |
|---|---|---|
| **Total Bytes** | **34.8 MB** | Folder `report/` ocupa **33.4 MB** (95.8%) |
| Archivos > 1MB | 3 | Todos en `report/` (2 diffs, 1 PDF) |
| Top Archivo | 11.1 MB | `report/AG-2D-02-2A_diff.patch` |

### C. Cobertura de Tests (Estática)

| Métrica | Valor |
|---|---|
| **Total Tests (Collected)** | **747** |
| Ratio LOC Physical / Test | 23.44 lines/test |
| Ratio LOC Eff (Tests) / Test | 16.12 lines/test |

## 3. Insights

1. **Report Bloat**: El directorio `report/` contiene el 90% de las líneas "physical" y el 96% del peso en bytes del repositorio. Urge política H1.1.
2. **Estructura Flat**: La ausencia de pasta `src/` dispersa ~6k líneas de código productivo en `other` (raíz y subcarpetas no estándar).
3. **Densidad de Tests**: Con ~12k líneas de test efectivas para ~12k líneas de producto, el ratio 1:1 sugiere una cobertura intensiva (o verbose).

## 4. Artefactos Generados

Todos los ficheros crudos se encuentran en `report/`:

- `AG-H1-0-2B_baseline.txt`
- `AG-H1-0-2B_loc_physical.txt`
- `AG-H1-0-2B_loc_py_effective.txt`
- `AG-H1-0-2B_bytes.txt`
- `AG-H1-0-2B_pytest_collect.txt`
- `AG-H1-0-2B_ratios.txt`
