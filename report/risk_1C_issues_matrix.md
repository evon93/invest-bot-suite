# RiskManager v0.5 — Matriz de Issues (Fase 1C Audit)

Esta matriz consolida todos los hallazgos provenientes de:
- DeepSeek
- Gemini
- Claude
- Grok
- Otras IAs / revisión manual

Los issues aquí listados se usarán para:
1. Decidir los parches mínimos previos a la Fase 1D.
2. Documentar qué problemas se consideran cerrados, descartados o postergados.
3. Justificar diseño y alcance de 1D+.

---

## Tabla de Issues

| ID | Categoría | Descripción | Archivo / Línea | Severidad (1–4) | Propuesto por | Estado | Notas |
|----|-----------|-------------|-----------------|------------------|----------------|--------|-------|
|    |           |             |                 |                  |                |        |       |
|    |           |             |                 |                  |                |        |       |
|    |           |             |                 |                  |                |        |       |
| S1 | Wiring | `backtest_initial.py` no pasa equity_curve, atr_ctx, dd_cfg → guardrails inactivos | backtest_initial.py | 1 | DeepSeek, Gemini, Grok | Pendiente | Bloquea 1D |
| S2 | Lógica | Falta flujo completo risk_decision/filter_signal según especificación | risk_manager_v0_5.py | 1 | Grok | Pendiente | Requiere reconciliación con lectura DeepSeek/Gemini |
| S3 | Config | Desalineación YAML: soft_limit_pct/hard_limit_pct ≠ max_dd_soft/max_dd_hard | risk_rules.yaml | 1 | DeepSeek, Gemini | Pendiente | Guardrail DD no operativo |
| S4 | Lógica | ATR stop depende de side no normalizado | risk_manager_v0_5.py | 1 | DeepSeek | Pendiente | Riesgo de stops ignorados |
| S5 | Robustez | Falta contexto → guardrails ignorados sin warning | risk_manager_v0_5.py | 1 | Gemini, DeepSeek, Grok | Pendiente | Riesgo silencioso |

| S6 | Config | Falta size_multiplier_soft en YAML | risk_rules.yaml | 2 | DeepSeek | Pendiente | Incompleto |
| S7 | Tests | Integración no detecta wiring roto | tests/* | 2 | Gemini, Grok | Pendiente | Añadir tests E2E |
| S8 | Lógica DD | Peak inicial fijo subestima DD | risk_manager_v0_5.py | 2 | DeepSeek | Pendiente | Revisar compute_drawdown |
| S9 | ATR | Stops irreales para ATR extremos | risk_manager_v0_5.py | 2 | DeepSeek | Pendiente | Validación extra |
| S10 | Versionado | YAML sigue en 0.4 mientras código es 0.5 | risk_rules.yaml | 2 | Grok | Pendiente | Debe sincronizarse |

| S11 | Lógica DD | Equity negativa → DD=0 sin semántica definida | risk_manager_v0_5.py | 3 | Gemini, Grok | Pendiente | Edge case |
| S12 | Robustez | Falta validación NaN/inf en DD | risk_manager_v0_5.py | 3 | DeepSeek, Grok | Pendiente | |
| S13 | Flujo | Kelly se aplica tras hard_stop | risk_manager_v0_5.py | 3 | DeepSeek | Pendiente | Refinar orden |
| S14 | Diseño | API pesada (inyección excesiva) | risk_manager_v0_5.py | 3 | Gemini, Grok | Pendiente | Evaluar refactor |
| S15 | Doc | Semántica ambigua force_close_positions | risk_manager_v0_5.py | 3 | DeepSeek | Pendiente | Documentar |

| S16 | Extensión | Stubs volatilidad/liquidez no implementados | risk_manager_v0_5.py | 4 | DeepSeek | Pendiente | Para 1D+ |
| S17 | Logging | Logging insuficiente | risk_manager_v0_5.py | 4 | Grok | Pendiente | Aumentar trazabilidad |
| S18 | Naming | `entry_price` debería ser `reference_price` | risk_manager_v0_5.py | 4 | Grok | Pendiente | Estético |
| S19 | Factory | Selección manual de versión v0.5 | risk_manager_factory.py | 4 | DeepSeek | Pendiente | Mejorar ergonomía |

---

## Leyenda de severidades

- **1 — Crítico:** Bug lógico que puede producir riesgo real, ruptura de guardrails o inconsistencia en PnL / equity.  
- **2 — Alto:** Comportamiento inesperado en edge cases relevantes; puede volverse crítico según contexto de mercado.  
- **3 — Medio:** Problemas de diseño, claridad o mantenibilidad que no afectan la seguridad del riesgo.  
- **4 — Bajo:** Mejora cosmética, refactor opcional, estilo, documentación secundaria.

---

## Estado

- **Pendiente:** Aún debe evaluarse o corregirse.  
- **Resuelto:** Parche aplicado y validado con tests.  
- **Descartado:** Se determina que no es un issue válido o no aplica.  
- **Futuro:** Se agenda para una fase posterior (por ejemplo, 1D+, 2A, etc.).

---

## Notas finales

Rellena esta matriz una vez hayas copiado las auditorías multi-IA en:
`report/risk_1C_multiIA_findings_template.md`

Este archivo será utilizado en AUDIT.6 para generar parches de severidad 1–2 y en AUDIT.7 para generar el informe final de auditoría.
