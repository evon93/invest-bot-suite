---
nombre: README.md
versión: "0.3"
fecha: 2025-07-01
tags: ["#visión", "#KPIs", "#multi-agente", "#CI", "#seguridad"]
---

## 📈 Visión
Desplegar un **bot de inversión autónomo** respaldado por arquitectura **multi‑agente** (Kai ↔ Gemini ↔ Claude) que gestione ≥ 200 €/mes, rebalancee mensualmente y mantenga trazabilidad regulatoria.

## 🔗 Roles de IA
| Agente  | Función principal | Capacidades extra |
|---------|------------------|-------------------|
| **Kai**     | Orquestación, CI/CD            | Python glue‑code, Langfuse logging |
| **Gemini**  | Scraping de mercado + sentimiento | Análisis de imagen/visión, DeepSeek research |
| **Claude**  | Backtests + gestión de riesgo   | Contexto 200 k tokens, verificación formal |

## 🛠️ Stack técnico mínimo
- **FastAPI** gateway + WebSocket listener
- **ccxt** + **alpaca-trade-api** + **CoinGecko** (fallback)
- **vectorbt** / **bt** para backtesting
- **PostgreSQL / TimescaleDB** (historical OHLCV)

## 📊 Cartera & Estrategia
- **Target allocation**: 60 % ETFs, 20 % growth stocks, 10 % crypto, 10 % bonds
- **Rebalance**: mensual; umbral drift ±3 %
- **Gestión de riesgo**: “Kelly capped” 50 %, stop‑loss ATR 2×, drawdown guardrail 5 %

## 🎯 KPIs & SLA
- **PnL ≥ benchmark MSCI World**
- **Max DD < 5 %**
- **Latency < 1 s** (order execution)
- **Throughput ≥ 100 k tx/día**

## 🧩 Reproducibilidad & Cost
- Semilla global 42 en Python/C++/Rust (`np.random`, `std::mt19937`, `StdRng`).
- Cost guardrail: Claude sólo si ctx > 10 k tokens; prioridad Kai→Gemini.

## 🔐 Seguridad & Compliance
- Claves API en Hashicorp Vault, acceso read‑only en CI.
- Logs Langfuse + hashes SHA‑256 para payloads (MiFID II ready).

## 📈 Monitoring & Alertas
- Prometheus + Grafana dashboard (`pnl`, `latency`, `VaR`).
- Alertmanager → Gmail/Slack si DD > 3 % o API error rate > 1 %.

## 🚀 Pipeline CI & Benchmarks
- Lint/format: **black**, **ruff**
- Tests: **pytest**, **pytest‑benchmark**, **asv** (rows/s)
- C++ → `clang‑tidy`; Rust → `cargo clippy`.

## 📂 Documentación & Otros archivos
- `architecture.md` – diagrama Mermaid + endpoints FastAPI
- `risk_rules.yaml` – parámetros de riesgo & rebalanceo
- `backlog.md` – roadmap Sprint‑0→3
- `integrations.md` – APIs y claves

> **Próximo paso:** validar **architecture.md** y generar artefacto `strategy_engine.py` skeleton.
