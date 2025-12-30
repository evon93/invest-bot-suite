# AG-2B-3-3-0 Return Packet — Grid Search Readiness Scan

## Inventario Existente

### CLI Arguments (`tools/run_calibration_2B.py`)

| Flag | Default | Descripción |
|------|---------|-------------|
| `--mode` | `quick` | Modo: quick (≤12 combos) / full (todo) / full_demo (alias) |
| `--max-combinations` | YAML/null | Limita combinaciones |
| `--seed` | 42 | Semilla reproducible |
| `--output-dir` | YAML | Override de directorio |
| `--strict-gate` | false | Exit 1 si gate falla |
| `--profile` | auto | Perfil de gates |
| `--config` | default | Path a YAML config |

### Generación de Combinaciones

- **`flatten_grid(grid)`**: Convierte YAML grid anidado en lista de dicts planos
- **`itertools.product(*flat_values)`**: Producto cartesiano de todos los valores
- **`generate_combo_id(params)`**: MD5 hash truncado para ID estable
- **`apply_overlay(base, flat_params)`**: Aplica overlay a `risk_rules.yaml` base

### Grid YAML (`configs/risk_calibration_2B.yaml`)

```yaml
grid:
  stop_loss:
    atr_multiplier: [2.0, 2.5, 3.0]
    min_stop_pct: [0.02, 0.03]
  max_drawdown:
    soft_limit_pct: [0.05, 0.08]
    hard_limit_pct: [0.10, 0.15]
    size_multiplier_soft: [0.5, 0.7, 1.0]
  kelly:
    cap_factor: [0.70, 0.90, 1.10, 1.30]
```

**Total combinaciones**: 3×2×2×2×3×4 = **288**

### Outputs Generados

| Archivo | Contenido |
|---------|-----------|
| `results.csv` | Todas las métricas por combo |
| `run_log.txt` | Log de ejecución con timestamps |
| `topk.json` | Top-K candidatos ordenados por score |
| `run_meta.json` | Metadata (hash, git, seed, gates, stats) |
| `summary.md` | Resumen ejecutivo en markdown |

### Scoring y Ranking

- **Fórmula configurable** en YAML: `score.formula`
- **Ranking**: `sorted(results, key=score, reverse=True)[:top_k]`
- **Top-K**: Configurable en `search.top_k` (default 20)

---

## Gap Analysis

| Característica | Estado | Notas |
|---------------|--------|-------|
| Grid desde YAML | ✅ Implementado | `config.grid` → `flatten_grid()` |
| Producto cartesiano | ✅ Implementado | `itertools.product` |
| Semilla reproducible | ✅ Implementado | CLI `--seed` + YAML `repro.seed` |
| Overlay sobre rules | ✅ Implementado | `apply_overlay()` in-memory |
| CSV con métricas | ✅ Implementado | 30+ columnas |
| Ranking por score | ✅ Implementado | Fórmula configurable |
| Top-K export | ✅ Implementado | `topk.json` |
| Metadata trazable | ✅ Implementado | `run_meta.json` con git/hash |
| Gates por profile | ✅ Implementado | `profiles.{quick,full_demo,full}` |
| Strict exit code | ✅ Implementado | `--strict-gate` |

### ¿Qué falta para grid search?

**Nada significativo.** El runner ya soporta grid search completo:

1. Define grid en YAML
2. Genera combinaciones automáticamente
3. Ejecuta cada combo con semilla fija
4. Rankea por score
5. Exporta top-K candidatos

---

## Propuesta

**No se requieren cambios.** El grid search está completamente implementado.

### Posibles Mejoras Futuras (fuera de scope)

1. **Multi-seed validation**: Ejecutar cada combo con múltiples seeds y agregar resultados
2. **Parallel execution**: Paralelizar backtests (actualmente secuencial)
3. **Early stopping**: Abortar combos que claramente no superarán umbral

---

## Conclusión

**Gap = 0 líneas.** No se requiere implementación. El runner 2B tiene grid search completo y funcional desde fase 2B-3.3.
