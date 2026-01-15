# AG-2E-4-3: Handoff — Post 2E-4-1/#7 and 2E-4-2/#8

**Fecha**: 2025-12-28  
**Baseline**: `main` @ `6a225ef`

---

## Estado Completado

### 2E-4-1: Inactive Reason Breakdown (PR #7)
- **Commit merge**: db8f355
- **Cambios**:
  - `backtest_initial.py`: +`self.diagnostics` dict con contadores
  - `run_calibration_2B.py`: +`classify_inactive_reason()`, columnas CSV `rejection_*`
  - Tests: +3 nuevos (unit + integration)
- **Artefactos**: `report/AG-2E-4-1_return.md`, `report/out_2E_4_1_*`

### 2E-4-2: Structured Risk Rejection Reasons (PR #8)
- **Commit merge**: 6a225ef
- **Cambios**:
  - `backtest_initial.py`: +`risk_reject_reasons_counter: Counter`
  - `run_calibration_2B.py`: +columna CSV `risk_reject_reasons_top`, +campo meta `risk_reject_reasons_topk`
  - Tests: +1 nuevo
- **Artefactos**: `report/AG-2E-4-2_return.md`, `report/2E_4_2_risk_reject_breakdown.md`, `report/out_2E_4_2_smoke/`

---

## Contrato de Datos (Post 2E-4)

### results.csv

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `is_active` | bool | Combo produjo trades |
| `rejection_no_signal` | 0/1 | Sin señales generadas |
| `rejection_blocked_risk` | 0/1 | Rechazado por RiskManager |
| `rejection_size_zero` | 0/1 | Tamaño calculado = 0 |
| `rejection_price_missing` | 0/1 | Precio faltante |
| `rejection_other` | 0/1 | Fallback |
| `risk_reject_reasons_top` | string | Top motivos (ej. `kelly_cap:ETF:181`) |

### run_meta.json

```json
{
  "rejection_reasons_agg": {"rejection_blocked_risk": 27, ...},
  "top_inactive_reasons": ["rejection_blocked_risk"],
  "risk_reject_reasons_topk": {"kelly_cap:ETF": 4887, "dd_soft": 72}
}
```

---

## Invariantes / Riesgos Conocidos

1. **`kelly_cap:ETF` domina** (~97% de rechazos): con Kelly cap bajo (0.3, 0.5), el sizing bloquea casi todo.
2. **`rejection_size_zero` siempre 0**: requiere instrumentación adicional en backtester (no crítico).
3. **PowerShell UTF-16**: usar `Out-File -Encoding utf8` para logs legibles.

---

## Próximos Pasos Sugeridos

1. **2B/3.3 Grid Search**: ampliar grid con más variantes de Kelly.
2. **2E-5**: análisis de sensibilidad (qué parámetro libera más trades).
3. **Merge PRs pendientes**: verificar que `feature/2E_full_demo_profile` se mergea.

---

## Archivos Clave

| Path | Propósito |
|------|-----------|
| `.ai/active_context.md` | Estado actual del proyecto |
| `.ai/decisions_log.md` | Log de decisiones técnicas |
| `report/AG-2E-4-*_return.md` | Return packets por ticket |
| `report/2E_4_*_breakdown.md` | Breakdowns de razones |
