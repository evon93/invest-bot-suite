---

## version: "0.3" fecha: 2025-07-13 tags: ["#arquitectura", "#Mermaid", "#event-driven", "#kafka", "#ci", "#otlp"]

# Arquitectura · *invest-bot-suite* (v0.3)

> Fuente de verdad para IAs colaboradoras y equipo core. Mantener sincronizado con el código.

## 1. Diagrama de alto nivel

```mermaid
flowchart TD
  subgraph UI[User / IA Orchestration]
      Kai(O3 Kai)
      Claude(Claude Opus 4)
      Gemini(Gemini 2.5)
      DeepSeek(DeepSeek R1)
  end

  subgraph CORE[[Core Services]]
      STRAT["Strategy Engine"]
      RISK["Risk Manager"]
      BROKER[(Exchange Connector)]
      METRICS[Metrics Generator]
  end

  subgraph BUS{{Kafka / Redpanda}}
      SIG_TOPIC((signal))
      RISK_TOPIC((risk_eval))
  end

  subgraph TESTS[[Quality Gates]]
      EDGE(edge_tests)
      STRESS(stress_tester)
      PyTest(pytest suite)
  end

  subgraph CI[CI/CD · GitHub Actions]
      MATRIX(Matrix 3.10‒3.12)
      CALC(calc_metrics)
      DRIFT(check_metrics_diff)
  end

  subgraph TOOLING[Dev Tooling]
      DEVCON(DevContainer)
      OTEL(OpenTelemetry)
  end

  Kai -->|prompts| STRAT
  Gemini -->|scrape & charts| STRAT
  DeepSeek -->|review PR| CI

  STRAT --orders--> BROKER
  STRAT --new_positions--> RISK
  RISK --alerts--> STRAT
  STRAT --signals--> SIG_TOPIC
  SIG_TOPIC --> RISK_TOPIC --> RISK

  TESTS --> CI
  EDGE --> MATRIX
  MATRIX --> CALC --> DRIFT
  DEVCON --bind mount--> CORE
  OTEL --- METRICS
```

## 2. Componentes principales

| Bloque                | Descripción                                                      | Código / Artefacto                                |
| --------------------- | ---------------------------------------------------------------- | ------------------------------------------------- |
| **Strategy Engine**   | Ingesta señales, ejecuta reglas de portfolio y envía órdenes.    | `strategy_engine.py`                              |
| **Risk Manager**      | Enforce DD\_max, ATR, Kelly cap; produce eventos de riesgo.      | `risk_manager.py` + `risk_rules.yaml`             |
| **Metrics Generator** | Post‑CI calcula Calmar, FeeAdj ROIC, WF.                         | `scripts/calc_metrics.py`                         |
| **Backtester**        | Validación offline & research.                                   | `backtest_initial.py`, `tests/test_backtester.py` |
| **Stress‑tester**     | Escenarios tail, liquidity, flash‑crash.                         | `stress_tester_v0.2.py`                           |
| **CI Matrix**         | Python 3.10‑3.12; artefactos `edge_logs`, `metrics_report.json`. | `.github/workflows/edge_tests.yml`                |
| **DevContainer**      | Entorno VS Code con micromamba, bind a WSL.                      | `Dockerfile`, `devcontainer.json`                 |

## 3. Observabilidad

- **OpenTelemetry** auto‑instrumentation (ISS‑19) → export a **Prometheus**/**Grafana Loki**.
- Traces de estrategia y riesgo enlazados por `trace_id`.

## 4. Seguridad

- Principio de *least privilege*: `risk_rules.yaml` controla límites duros.
- Firmado de contenedores con **cosign** (pendiente Stage C).
- **OPA Gatekeeper** planificado para validar deployments en k8s.

## 5. Calidad & Guardrails

- Edge tests + stress tests obligatorios antes de merge.
- `check_metrics_diff.py` bloquea drift > ±5 % en Calmar, ROIC, WF.
- `requirements.lock` versiona deps (NumPy, Pandas, SciPy, PyYAML, PyTest).

## 6. Roadmap mejoras (v0.4)

1. **Schema Registry** para mensajes `signal` / `risk_eval`.
2. **Dead‑Letter Queue** + reintentos exponenciales (Kafka).
3. **GitOps** (ArgoCD) para despliegue continuo en k8s.
4. **KServe** para futuros modelos ML de señales.

---

> Última actualización: 2025‑07‑13 por Kai (o3).

