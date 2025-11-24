# Registro de Estado  Proyecto invest-bot-suite

_Registro histórico, contexto para IAs colaboradoras y trazabilidad completa._

---

##  Estado Actual (2025-11-21)

- **Entorno**: Windows 11 host · WSL 2 Ubuntu 24.04 (Python 3.12.3 en `.venv`).
- **Ruta de trabajo**: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
- **Rama**: `orchestrator-v2` (base tag `baseline_20251121_D0`).
- **Python venv**: 3.12.3 · numpy 2.3.1 · pandas 2.3.1 · pytest 8.4.1 · pyyaml 6.0.2.
- **Build/tests**: `pytest` → 4 FAIL / 6 PASS (fallos en `tests/test_backtest_deepseek.py`).
- **Artefactos baseline**: `requirements.lock`, `baseline_venv_packages_0A.txt`, `report/pytest_20251121_baseline_full.txt`, `report/env_20251121.json`.

---

##  Estado Actual (2025-07-12)

- **Entorno**: Windows 11 23H2 host  **WSL 2** (Ubuntu 24.04, kernel 5.15, GPU habilitada).
- **Ruta de trabajo**: `~/invest-bot-suite` (ext4, fuera de OneDrive).
- **Python venv**: 3.12 · numpy 1.28 · pandas 2.2 · pytest 8.2 · pyyaml 6.0.2.
- **Build/tests**: `pytest`  **6 FAIL / 4 PASS** (error `.columns` en `SimpleBacktester._rebalance`).
- **CI**: workflow **edge_tests** operativo; métricas automáticas pendientes (`calc_metrics`).
- **Backlog abierto**: P1  P5 (ver tabla de problemas).
- **Próximo hito**: Rama `docs/v1.3`  CHANGELOG provisional  PR Stage A.

### Problemas abiertos (prioridad descendente)

| Nº | Ítem | Acción requerida |
|----|------|------------------|
| P1 | 6 tests fallan (`SimpleBacktester._rebalance`) | Refactor para soportar Series & DataFrame |
| P2 | `requirements.txt` sin versiones | Ejecutar `pip freeze > requirements.lock`, pin dependencias |
| P3 | Dev Container incompleto | Completar Dockerfile + `devcontainer.json` |
| P4 | OneDrive pop-ups al borrar archivos | Excluir `shared` de sincronización |
| P5 | Falta CI/CD completo | Crear workflow CI + GHCR |

---

##  Estado Actual (2025-07-08)

- **Freeze candidate v1.3:** código sincronizado en repo privado `evon93/invest-bot-suite`.
- RiskManager v0.5 (parches ISS-1923) en rama `main`.
- CI GitHub Actions activo: workflow **edge_tests** genera artefacto `edge_logs` .
- CHANGELOG y metrics report pendientes de subir (Calmar  2.0, FeeAdj ROIC  2.2 %, WF_ratio > 65 %).
- Orquestación IA establecida: Kai (o3), Claude Opus 4, Gemini 2.5 Pro, DeepSeek R1.

---

##  Historial de Fases Clave

### 2025-07-12  Migración a WSL 2 & detección de 6 tests FAIL
- Copiado repo a `~/invest-bot-suite` en volumen ext4.
- Creado venv `.venv` y actualización mínima de dependencias.
- Corregido indent en `backtest_initial.py`; aparecen 6 FAIL en rebalanceo.

### 2025-07-08  v1.3 (Design-Freeze loop)
-  Repo GitHub privado creado y código base push.
-  Añadido workflow **edge_tests** + artefactos logs.
-  Fixes críticos ISS-1923 integrados (cascade alert, liquidity multiplier Asia, stablecoin de-peg, gas multipliers, edge-tests CI).

### 2025-07-04
- Base limpia RiskManager v0.4 + SHIM universal + tests `3 passed`.
- Backup generado: `backup_20250704_1753.zip`.

---

##  Lecciones Aprendidas

1. Sin CI no hay auditoría IA  workflow mínimo indispensable.
2. Parar trading en rangos y cascadas evita DD > 15 %.
3. Métricas deben ser fee- y slippage-aware (FeeAdj ROIC).
4. Migrar a Linux/WSL reduce fricción con paths y venvs.

---

##  Próximos Hitos Inmediatos

| Semana | Hito | Responsable |
|--------|------|-------------|
| 0-1 | Crear rama `docs/v1.3`, subir CHANGELOG provisional | Kai |
| 0-1 | Generar `metrics_report.json` automático vía CI | DeepSeek |
| 1 | Completar Dev Container + Dockerfile | Gemini |
| 1 | Refactor re-balance + pasar tests | Kai |
| 2 | Declarar **Design Freeze** v1.3 final | Kai |

---

##  Trazabilidad IA  IA
- **TRACE_ID última build:** migrate_wsl2_v1.3_candidate
- IAs colaboradoras: Kai (o3), Claude Opus 4, Gemini 2.5 Pro, DeepSeek R1.

---

##  Notas
- Actualizar este registro tras cada push relevante.
- Adjuntar artefactos (edge_logs, metrics) en cada auditoría.
- Mantener backups tras milestones.
