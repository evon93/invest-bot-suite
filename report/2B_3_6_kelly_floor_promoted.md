# 2B-3.6: Kelly Floor Promoted to Baseline

**Timestamp**: 2025-12-29T16:20

---

## Decisión

`kelly.cap_factor >= 0.70` promovido como floor mínimo en config baseline.

## Justificación (2B-3.5)

| cap_factor | active_rate | gate_passed (3 seeds) |
|------------|-------------|----------------------|
| 0.50 | 0% | 0/3 ❌ |
| 0.70 | 100% | 3/3 ✅ |

Validación multi-seed (42, 43, 44) confirmó robustez.

## Cambio Aplicado

**Archivo**: `configs/risk_calibration_2B.yaml`

```yaml
# Antes
cap_factor: [0.30, 0.50, 0.70]

# Después
cap_factor: [0.70, 0.90, 1.10, 1.30]
```

## Grid Total

Con el floor aplicado:
- 4 valores Kelly × otras dimensiones = grid reducido pero 100% activo

## Referencias

- `report/2B_3_5_kelly_floor_promotion.md` — Análisis multi-seed
- `report/out_2B_3_5_kelly07_seed*/` — Evidencia Kelly 0.7
- `report/out_2B_3_5_kelly05_seed*/` — Evidencia Kelly 0.5
