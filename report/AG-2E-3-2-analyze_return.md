# AG-2E-3-2-analyze: Análisis Full Run out_2E_3_1_full

**Timestamp**: 2025-12-28T15:33  
**Run analizado**: `report/out_2E_3_1_full`

---

## 1. Resumen run_meta.json

| Campo | Valor |
|-------|-------|
| mode | full |
| total_grid | 216 |
| active_n | 72 |
| inactive_n | 144 |
| **active_rate** | 33.33% |
| active_pass_rate | 100% |
| **gate_passed** | true |
| gate_fail_reasons | [] |
| rejection_other | 144 (100% de inactivos) |

**Thresholds aplicados** (de configs/risk_calibration_2B.yaml):
- `min_active_n`: 20 → cumplido (72 ≥ 20)
- `min_active_rate`: 60% → **NO cumplido** (33% < 60%) pero gate pasa
- `min_active_pass_rate`: 70% → cumplido (100%)

> **Nota**: El gate pasó porque la lógica actual requiere `active_n < min_active_n AND active_rate < min_active_rate` para fallar por insufficient_activity. Como `active_n=72 ≥ 20`, la condición no se cumple.

---

## 2. Análisis por kelly.cap_factor

| kelly.cap_factor | Total | Activos | Inactivos | active_rate |
|------------------|-------|---------|-----------|-------------|
| 0.3 | 72 | 0 | 72 | **0%** |
| 0.5 | 72 | 0 | 72 | **0%** |
| 0.7 | 72 | 72 | 0 | **100%** |

### Distribución num_trades por kelly.cap_factor

| kelly.cap_factor | min | median | max |
|------------------|-----|--------|-----|
| 0.3 | 0 | 0 | 0 |
| 0.5 | 0 | 0 | 0 |
| 0.7 | 4 | 4 | 4 |

> **Hallazgo clave**: `kelly.cap_factor` es el **único determinante** de actividad. Los demás parámetros (atr_multiplier, min_stop_pct, soft/hard_limit) no afectan si hay trades o no.

---

## 3. Quality Gate Pass/Fail

| Métrica | Criterio | Activos (72) | Resultado |
|---------|----------|--------------|-----------|
| num_trades | ≥ 1 | 4 | ✓ PASS |
| sharpe_ratio | ≥ 0.3 | 1.07 | ✓ PASS |
| cagr | ≥ 0.05 | 14.26% | ✓ PASS |
| max_drawdown | ≥ -0.25 | -9.93% | ✓ PASS |

**¿Por qué active_pass_rate = 100%?**

Todos los 72 escenarios activos tienen **métricas idénticas** porque:
1. Señal sintética es determinista (seed=42)
2. kelly.cap_factor=0.7 es el único valor que produce trades
3. Los demás parámetros no influyen el resultado del backtest

---

## 4. Top-K Análisis

### Criterio de scoring
```
score = 1.0*sharpe + 0.5*cagr + 0.3*win_rate - 1.5*|max_dd| - 0.5*pct_time_hard_stop
```

### Top 10 (todos idénticos)

| Rank | Score | Sharpe | CAGR | MaxDD | kelly | Diferencia |
|------|-------|--------|------|-------|-------|------------|
| 1-10 | 0.9926 | 1.07 | 14.26% | -9.93% | 0.7 | solo varían otros params |

**Problema**: No hay diferenciación entre los 72 escenarios activos — todos producen exactamente el mismo resultado porque la señal sintética es demasiado simple.

---

## 5. Análisis de Warnings (run_log.txt)

| Warning | Conteo |
|---------|--------|
| "Asset limit exceeded" | **0** |
| "Señal rechazada" | **0** |
| Otros warnings | **0** |

El log solo contiene entradas START/END sin warnings. Esto indica que:
- No hay bloqueo por risk limits
- No hay rechazo explícito de señales en los escenarios inactivos
- La inactividad viene de **ausencia total de señales** (no de bloqueo)

---

## 6. Diagnóstico: ¿Dónde está el cuello de botella?

### Descartados
- ❌ **Limits/Risk blocks**: 0 warnings de límites o bloqueos
- ❌ **Signal scarcity**: La señal sintética genera trades cuando kelly ≥ 0.7

### Causa raíz identificada
- ✅ **Kelly sizing gate**: Cuando `kelly.cap_factor < 0.7`, el position size calculado es 0 (o rechazado), resultando en 0 trades.

**Hipótesis verificable**: El modelo de Kelly en `RiskManager.filter_signal` o el tamaño mínimo de posición rechaza posiciones cuando el cap_factor es bajo.

---

## 7. Conclusión y Próximos Tickets

### El cuello de botella es Kelly/Sizing

La correlación perfecta entre `kelly.cap_factor=0.7` y actividad indica que:
1. El grid de calibración solo explora 3 valores de kelly: {0.3, 0.5, 0.7}
2. Solo kelly=0.7 produce trades
3. Los otros parámetros (stop_loss, max_drawdown) son irrelevantes para el resultado

### Tickets propuestos

**Config primero (bajo riesgo, rápido)**:

1. **Ticket 2E-4-config-kelly-grid**: Expandir grid de kelly.cap_factor
   - Valores propuestos: {0.5, 0.6, 0.65, 0.7, 0.8, 0.9}
   - Objetivo: encontrar el threshold real donde comienzan los trades
   - Impacto: solo YAML, sin cambio de código

2. **Ticket 2E-5-config-min-position**: Revisar min_position_size en risk_rules.yaml
   - Verificar si hay un floor de posición que bloquea kelly bajos
   - Ajustar si es innecesariamente restrictivo

**Instrumentación después (si config no basta)**:

3. **Ticket 2E-6-telemetry-kelly**: Añadir logging al cálculo de Kelly
   - Emitir `kelly_raw`, `kelly_capped`, `position_size` en risk_decision
   - Persiste en results.csv para diagnóstico

---

## Archivos de este ticket

- `report/AG-2E-3-2-analyze_return.md` ← este archivo
- `report/AG-2E-3-2-analyze_run.txt`
