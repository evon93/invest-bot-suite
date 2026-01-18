# CI Workflows Map (AG-H2-4-1)

## Resumen

**15 workflows** en `.github/workflows/`:

| Workflow | Trigger | Jobs | Propósito | Duplicado? |
|----------|---------|------|-----------|------------|
| ci.yml | push/PR main | check | Repo checks | Core ✓ |
| h1_gate.yml | push/PR | h1-gate | H1 tests | Merge candidate |
| graceful_shutdown_3O.yml | push/PR | test-graceful-shutdown | Shutdown tests | Merge candidate |
| edge_tests.yml | push main | edge_tests | Risk edge cases | Specific |
| e2e_smoke_2J.yml | push/PR | e2e-smoke-2j | E2E 2J pipeline | Specific |
| robustness_quick.yml | push/PR | robustness-quick | Quick robustness | Specific |
| robustness_full.yml | push/PR | robustness-full | Full robustness | Specific |
| smoke_3B.yml | push/PR main | smoke-3b | 3B integration | Similar pattern |
| smoke_3C.yml | PR main | smoke-3c | 3C runner | Similar pattern |
| smoke_3E.yml | PR/dispatch | smoke-3e | 3E tests | Similar pattern |
| smoke_3F.yml | PR | smoke-3f | 3F tests | Similar pattern |
| smoke_3G.yml | PR | smoke-3g | 3G tests | Similar pattern |
| smoke_3H.yml | push/PR | smoke-3h | 3H supervisor | Similar pattern |
| smoke_3I.yml | push/PR | smoke-3i | 3I graceful | Similar pattern |
| smoke_3J.yml | push/PR | smoke-3j | 3J strategy | Similar pattern |

## Duplicación identificada

**Patrón común** (13/15 workflows):

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: 'pip'
- run: pip install -r requirements.txt
- run: python -m pytest -q  # Muchos corren pytest full
```

**Gates vs Smokes:**

- `h1_gate.yml`, `graceful_shutdown_3O.yml` → tests específicos H1/3O
- `smoke_3B..3J` → smokes de features específicas

## Plan de consolidación

### Opción elegida: Workflow principal unificado

1. **Mantener**: `ci.yml` como entry point (repo checks + pytest -q)
2. **Consolidar en `ci.yml`**:
   - Agregar job `tests` con pytest -q (cubre lo que hacen la mayoría de smokes)
3. **Mantener separados** (tienen lógica específica no-trivial):
   - `robustness_quick.yml`, `robustness_full.yml` → workflow largo/específico
   - `e2e_smoke_2J.yml` → pipeline E2E completo
4. **Eliminar** (redundantes, subsumidos por pytest -q en CI):
   - `smoke_3C.yml` → solo corre pytest + un runner básico
   - `smoke_3E.yml`, `smoke_3F.yml`, `smoke_3G.yml` → solo pytest
5. **Fusionar en ci.yml** como jobs opcionales:
   - `h1_gate.yml` → job "h1-gate" en ci.yml
   - `graceful_shutdown_3O.yml` → job "graceful-shutdown" en ci.yml
   - `edge_tests.yml` → job "edge-tests" en ci.yml
6. **Mantener** (smokes con lógica runner específica):
   - `smoke_3B.yml` → corre runner 3B con datos sintéticos
   - `smoke_3H.yml` → corre supervisor smoke
   - `smoke_3I.yml` → corre graceful shutdown smoke
   - `smoke_3J.yml` → corre strategy validation harness

### Resultado final esperado

| Archivo | Estado |
|---------|--------|
| ci.yml | ⬆️ Expandido (tests + gates) |
| robustness_quick.yml | ✓ Mantener |
| robustness_full.yml | ✓ Mantener |
| e2e_smoke_2J.yml | ✓ Mantener |
| smoke_3B.yml | ✓ Mantener |
| smoke_3H.yml | ✓ Mantener |
| smoke_3I.yml | ✓ Mantener |
| smoke_3J.yml | ✓ Mantener |
| edge_tests.yml | 🔀 Merge → ci.yml |
| h1_gate.yml | 🔀 Merge → ci.yml |
| graceful_shutdown_3O.yml | 🔀 Merge → ci.yml |
| smoke_3C.yml | ❌ Delete |
| smoke_3E.yml | ❌ Delete |
| smoke_3F.yml | ❌ Delete |
| smoke_3G.yml | ❌ Delete |

**De 15 → 8 workflows** (47% reducción)
