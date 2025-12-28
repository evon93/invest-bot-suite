# AG-2C-7-1A — Return Packet

**Fecha:** 2025-12-25 22:17 CET  
**Rama:** `feature/2C_apply_best_params_v0_1`  
**Commit:** `5c90685`

---

## Resultados

| Check | Resultado |
|-------|-----------|
| **Validador** | ✅ PASS (0 errors, 0 warnings) |
| **Pytest** | ✅ PASS (77 tests) |

---

## Cambios aplicados a risk_rules.yaml

| Path | Antes | Después |
|------|-------|---------|
| `stop_loss.atr_multiplier` | 2.5 | **2.0** |
| `max_drawdown.hard_limit_pct` | 0.08 | **0.1** |
| `kelly.cap_factor` | 0.50 | **0.7** |

---

## Archivos

| Archivo | Estado |
|---------|--------|
| `risk_rules.yaml` | ✅ Promovido |
| `risk_rules.yaml.bak_2C_20251225` | ✅ Backup local (en .gitignore) |
| `risk_rules_candidate.yaml` | Conservado (source) |

---

## Commit

```
5c90685 2C: promote calibrated risk_rules (backup + validate + tests)
15 files changed, 254 insertions(+), 44 deletions(-)
```

---

## DoD

- [x] Backup creado
- [x] Candidate promovido como risk_rules.yaml
- [x] Validador PASS
- [x] Pytest PASS (77 tests)
- [x] Commit creado
