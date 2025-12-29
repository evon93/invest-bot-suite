# AG-H0-7-4: Finalize 7.2 PR Artifacts

**Timestamp**: 2025-12-29T19:42

---

## PR Info

**Branch**: `feature/7_2_cli_full_demo_alias`  
**Target**: `main`  
**URL**: <https://github.com/evon93/invest-bot-suite/compare/main...feature/7_2_cli_full_demo_alias>

---

## DoD Checklist

| Criterio | Estado |
|----------|--------|
| pytest -q = 132 passed | ✅ |
| `report/out_7_2_smoke_alias/` existe | ✅ |
| `report/out_7_2_smoke_canon/` existe | ✅ |
| run_meta: mode=full, gate_profile=full_demo | ✅ |
| run_meta: gate_passed=true | ✅ |
| Sin `out_7_1_smoke/` | ✅ (eliminado) |
| `7_2_last_commit.txt` en UTF-8 | ✅ |

---

## git log -1 --oneline --decorate

```
1ad7c38 (HEAD -> feature/7_2_cli_full_demo_alias, origin/feature/7_2_cli_full_demo_alias) feat(cli): add --mode full_demo alias + normalize_args + examples epilog
```

---

## git status -sb

```
## feature/7_2_cli_full_demo_alias...origin/feature/7_2_cli_full_demo_alias
```

(Limpio, sin cambios pendientes)

---

## run_meta.json (alias) - primeras 25 líneas

```json
{
  "config_hash": "6e8214a42d39b659",
  "git_head": "8da7f9d687c1",
  "seed": 42,
  "mode": "full",
  "gate_profile": "full_demo",
  "total_grid": 288,
  "num_combos": 12,
  "active_n": 12,
  "inactive_n": 0,
  "active_rate": 1.0,
  "gate_passed": true,
  ...
}
```

---

## run_meta.json (canon) - primeras 25 líneas

```json
{
  "config_hash": "6e8214a42d39b659",
  "git_head": "8da7f9d687c1",
  "seed": 42,
  "mode": "full",
  "gate_profile": "full_demo",
  "total_grid": 288,
  "num_combos": 12,
  "active_n": 12,
  "inactive_n": 0,
  "active_rate": 1.0,
  "gate_passed": true,
  ...
}
```

---

## PR Descripción

### ¿Qué arregla?

Elimina el error humano común `--mode full_demo invalid choice`. Ahora `--mode full_demo` es un alias válido que se normaliza a `--mode full --profile full_demo`.

### Verificación

- pytest: 132 passed
- 2 smokes (alias/canon) con meta equivalente
- Ambos producen `gate_passed: true`
