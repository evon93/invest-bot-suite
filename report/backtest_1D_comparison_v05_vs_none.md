# PLAN 1D.validation · 1D.v2 — Mini-backtest comparativo (none vs RiskManager v0.5)

## 1. Configuración

- Script: backtest_initial.py
- Dataset: escenario por defecto del proyecto.
- Comparación:
  - Escenario A (none): sin gestor de riesgo.
  - Escenario B (v0_5): RiskManagerV05 activado con risk_rules.yaml actual.

Comandos ejecutados:

- Escenario A — sin gestor de riesgo:
  python backtest_initial.py --risk-manager-version none | tee report/backtest_1D_none.txt

- Escenario B — con RiskManager v0.5:
  RISK_MANAGER_VERSION=v0_5 python backtest_initial.py | tee report/backtest_1D_v05.txt

## 2. Resultados numéricos

### 2.1 Escenario A — sin RiskManager (none)

Métricas reportadas por calculate_metrics(...):

{ 'cagr': 0.15790395006451363,
  'total_return': 0.15790395006451363,
  'max_drawdown': -0.09847045115855935,
  'sharpe_ratio': 1.30109905514287,
  'volatility': 0.11853472060855608 }

Interpretación breve:

- Estrategia base genera aproximadamente 15.8% de retorno total (CAGR similar).
- Máx. drawdown controlado en torno al -9.85%.
- Sharpe ratio alrededor de 1.30.

### 2.2 Escenario B — con RiskManager v0.5 (v0_5)

Logs relevantes observados:

- WARNING - Señal rechazada: ['kelly_cap:ETF] (repetido múltiples veces).

Métricas reportadas:

{ 'cagr': 0.0,
  'total_return': 0.0,
  'max_drawdown': 0.0,
  'sharpe_ratio': 0.0,
  'volatility': 0.0 }

Interpretación:

- El guardrail de Kelly (regla kelly_cap:ETF) bloquea todas las señales relevantes para el ETF en este escenario.
- Como resultado:
  - No se ejecutan operaciones significativas.
  - El NAV permanece plano y todas las métricas quedan en 0.
- Este comportamiento es coherente con una configuración muy conservadora del tamaño máximo de posición para el activo principal del backtest.

## 3. Conclusión operativa 1D.v2

- 1D.core confirma que:
  - El wiring backtester → RiskManagerV05 funciona (no hay excepciones; el flujo de decisión se ejecuta).
  - La diferencia de comportamiento entre none y v0_5 en este dataset es extrema:
    - none: estrategia libre, retorno positivo con drawdown razonable.
    - v0_5: modo prácticamente risk-off debido al guardrail de Kelly.

- Decisión para 1D.validation:
  - No se modifican parámetros de riesgo en este paso.
  - Se documenta explícitamente que, en el escenario de test actual, RiskManagerV05 está configurado de forma tan conservadora que anula la operativa.
  - Ajustes de parámetros (por ejemplo, relajación de Kelly para ETF) se delegan a planes posteriores (2A/2B), donde se definen objetivos cuantitativos de riesgo/retorno y escenarios de calibración.

