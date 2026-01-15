# Score Formula Alternatives — AG-2B-4-2

## Contexto

La fórmula actual es:
```
1.0*sharpe_ratio + 0.5*cagr - 1.5*abs(max_drawdown)
```

Queremos incorporar las nuevas métricas de riesgo:
- `win_rate` — porcentaje de trades ganadores
- `atr_stop_count` — veces que ATR stop se activó
- `hard_stop_trigger_count` — transiciones a hard_stop por DD
- `pct_time_hard_stop` — % del tiempo en estado hard_stop

---

## Alternativa A (Conservadora)

**Filosofía**: Prioriza retorno ajustado al riesgo. Penaliza hard_stop % de forma suave sin descartar estrategias que ocasionalmente entran en hard_stop.

```python
formula: "1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop"
```

**Trade-offs**:
- ✅ Premia win_rate (estrategias consistentes)
- ✅ Penalización suave de pct_time_hard_stop (escala 0-1 → impacto -0 a -0.5)
- ✅ Mantiene retorno/riesgo como drivers principales
- ⚠️ No penaliza hard_stop triggers individuales

---

## Alternativa B (Estricta)

**Filosofía**: Penaliza fuertemente cualquier activación de hard_stop. Estrategias que activan guardrails múltiples veces son descartadas.

```python
formula: "1.0*sharpe_ratio + 0.5*cagr + 0.3*win_rate - 1.5*abs(max_drawdown) - 0.5*pct_time_hard_stop - 0.2*hard_stop_trigger_count - 0.1*atr_stop_count"
```

**Trade-offs**:
- ✅ Penaliza fuertemente estrategias con múltiples triggers
- ✅ Usa todas las métricas disponibles
- ⚠️ Puede ser demasiado punitiva para estrategias agresivas válidas
- ⚠️ atr_stop_count puede acumularse rápido en estrategias volátiles

---

## Decisión

**Elegida: Alternativa A** (conservadora)

**Razón**: 
- La Alternativa A penaliza el % de tiempo en hard_stop sin descartar estrategias por triggers ocasionales
- Es más robusto para un primer despliegue
- Podemos iterar hacia B si A no filtra suficiente

**Anti-div0 / Anti-NaN**:
El runner ya tiene fallback a `sharpe_ratio` si hay error en eval.
Todas las métricas tienen default 0 en `compute_score()`.
