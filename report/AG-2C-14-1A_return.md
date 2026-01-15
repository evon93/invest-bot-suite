# AG-2C-14-1A — Return Packet

**Fecha:** 2025-12-26 22:18 CET  
**Rama:** `main`  
**Commit:** `d901535`

---

## Documentos creados/actualizados

| Archivo | Propósito |
|---------|-----------|
| `bridge_2C_to_2D_report.md` | Resumen 2C + roadmap 2D |
| `.ai/active_context.md` | Estado actual del proyecto |
| `registro_de_estado_invest_bot.md` | Entrada 2025-12-26 añadida |

---

## Validación

| Check | Resultado |
|-------|-----------|
| **pytest** | ✅ 77 passed (1.29s) |
| **validate_risk_config** | ✅ 0 errors, 0 warnings |

---

## Artefactos

| Archivo | Propósito |
|---------|-----------|
| `report/AG-2C-14-1A_pytest.txt` | Salida pytest |
| `report/AG-2C-14-1A_validate.txt` | Salida validador |
| `report/AG-2C-14-1A_diff.patch` | Diff de cambios |
| `report/AG-2C-14-1A_last_commit.txt` | Hash del commit |
| `report/AG-2C-14-1A_return.md` | Este documento |

---

## Resumen de fase 2C

### Implementado
- Schema + selector determinista para topk.json
- Builder CLI para generar best_params_2C.json
- Apply CLI para actualizar risk_rules.yaml
- Promoción de parámetros calibrados

### Parámetros aplicados
| Path | Antes | Después |
|------|-------|---------|
| `stop_loss.atr_multiplier` | 2.5 | 2.0 |
| `max_drawdown.hard_limit_pct` | 0.08 | 0.1 |
| `kelly.cap_factor` | 0.50 | 0.7 |

### EOL Hygiene
- 48 archivos renormalizados a LF
- Commit: `3c3d74b`

---

## Known pitfalls

- Windows: usar `python -m pytest -q` en lugar de `pytest -q`
- Ver `bridge_2C_to_2D_report.md` para detalles

---

## DoD

- [x] pytest OK (77 passed)
- [x] validate_risk_config OK (0 errors)
- [x] Commit único creado (`d901535`)
- [x] Artefactos generados
