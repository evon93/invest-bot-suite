# Workflow Antigravity v0.1 — Informe de implementación (2025-12-11)

## 1. Resumen ejecutivo

Este documento describe la implementación del workflow Antigravity v0.1 en el repo
invest-bot-suite, centrado en:

- Introducción de un memory bank operativo en `.ai/`.
- Herramientas mínimas de soporte en `tools/`.
- Protocolo operativo reutilizable como System Prompt para agentes EXECUTOR/Antigravity.
- Validación básica pero estructural de `risk_rules.yaml`.
- Garantía de estabilidad mediante pytest completo.

No se ha modificado la lógica de trading ni de riesgo; solo se ha añadido infraestructura.

---

## 2. Artefactos nuevos en `.ai/`

### 2.1 `.ai/active_context.md`

- Rol: estado técnico resumido del proyecto.
- Contenido actual relevante:
  - Baseline pytest antes de Antigravity: 47 tests OK (`report/pytest_2A_before.txt`).
  - Rama de trabajo actual: `feature/workflow_antigravity_v0_1`.
  - Nota explícita para no commitear:
    - `report/pytest_2A_before.txt`
    - `risk_context_v0_6.py`
  - Bloque de Paso 5:
    - Herramientas añadidas: `config_schema.py`, `tools/validate_risk_config.py`,
      `tests/test_risk_config_schema.py`.
    - Snapshot validador: `report/validate_risk_config_step5.txt`.
    - Pytest global tras Paso 5: 48 tests OK (`report/pytest_antigravity_step5.txt`).

Uso recomendado:
- Actualizar al finalizar bloques de trabajo significativos.
- Mantenerlo corto y operativo (estado, snapshots clave, ramas).

### 2.2 `.ai/decisions_log.md`

- Rol: log de decisiones técnicas relevantes (tipo journal).
- Formato:
  - `[YYYY-MM-DD HH:MM] [actor] [rama] — Descripción`.
- Entradas relevantes para Antigravity v0.1:
  - Creación de infraestructura `.ai` (active_context, decisions_log, project_map).
  - Creación de `.ai/antigravity_operational_protocol.md v0.1`.
  - Introducción de `config_schema.py`, `tools/validate_risk_config.py`,
    `tests/test_risk_config_schema.py`; `risk_rules.yaml` validado (Errors: 0, Warnings: 4).

Uso recomendado:
- Registrar cambios en:
  - Workflow Antigravity.
  - Configuración y lógica de riesgo.
  - Tooling crítico (`tools/…`).
  - Puentes entre fases (1D, 2A, etc.).

### 2.3 `.ai/project_map.md`

- Generado automáticamente por `tools/update_project_map.py`.
- Contiene:
  - Conteo total de ficheros Python y tests.
  - Lista de módulos core detectados (RiskManager, RiskContext, backtest, stress tester).
  - Hotspots por directorio (alta densidad de código/tests).
  - Listado por directorio top-level (root, `tests/`, `audit/`, etc.).

Uso recomendado:
- Navegación rápida del repo por parte de agentes.
- Identificación de módulos sensibles o densos antes de proponer cambios.

### 2.4 `.ai/antigravity_operational_protocol.md`

- Protocolo operativo v0.1 que define:
  - Roles:
    - Kai-Orchestrator.
    - EXECUTOR-BOT.
    - IAs auxiliares (Gemini, DeepSeek, Grok, etc.).
  - Ciclo A→D obligatorio:
    - Análisis → Plan → Ejecución → Verificación/Documentación.
  - Guardrails de riesgo:
    - No tocar `risk_manager_*`, `risk_context_*`, `risk_rules.yaml`,
      ni backtest crítico sin tests + pytest + actualización de `/report` y `.ai/*`.
  - Reglas de uso de `.ai/`:
    - `active_context` como estado técnico.
    - `decisions_log` como log de diseño.
    - `project_map` como mapa operativo.
    - Este propio protocolo como System Prompt.

Uso recomendado:
- Incluirlo (total o parcial) como bloque de contexto en los prompts de agentes
  EXECUTOR/Antigravity.

---

## 3. Herramientas nuevas en `tools/`

### 3.1 `tools/update_project_map.py`

Rol:
- Generar `.ai/project_map.md` con una visión estructurada del repo.

Comportamiento:
- Recorre el directorio raíz, ignora `.git`, `.venv`, cachés, etc.
- Agrupa ficheros por directorio top-level.
- Calcula:
  - Número de ficheros `.py` por directorio.
  - Número de tests por directorio.
- Detecta módulos core por patrón en el nombre (`strategy_engine`, `risk_manager`,
  `risk_context`, `backtest`, `stress`, etc.).
- Escribe todo en markdown en `.ai/project_map.md`.

Uso:
- Ejecutar `python tools/update_project_map.py`.

Salida:
- Actualiza `.ai/project_map.md` in-place.

### 3.2 `tools/validate_risk_config.py`

Rol:
- Validar `risk_rules.yaml` usando `config_schema.py` y generar un informe en `/report`.

Comportamiento:
- Llama a `load_and_validate` de `config_schema.py`.
- Distingue:
  - Errors: problemas estructurales serios (YAML inválido, raíz no dict, valores
    numéricos incoherentes cuando existen).
  - Warnings: secciones recomendadas ausentes (`risk_limits`, `dd_limits`,
    `atr_stop`, `position_sizing`, etc.).
- Genera un informe en:
  - `report/validate_risk_config_step5.txt`.
- Código de salida:
  - 0 si no hay errores.
  - 1 si los hay.

Uso básico:
- Ejecutar `python tools/validate_risk_config.py`.

Parámetros:
- `-c / --config`: ruta alternativa a config (por defecto `risk_rules.yaml`).
- `-o / --output`: ruta de informe (por defecto `report/validate_risk_config_step5.txt`).

---

## 4. Esquema de configuración: `config_schema.py`

Rol:
- Proporcionar un esquema mínimo y validación best-effort para `risk_rules.yaml`.

Características:
- Garantiza que:
  - El YAML se parsea correctamente.
  - La raíz es un dict.
  - Las claves top-level son strings.
- Secciones recomendadas (pero no obligatorias):
  - `risk_limits`, `position_limits`, `dd_limits`, `atr_stop`, `kelly`,
    `position_sizing`.
- Validaciones numéricas:
  - Si existen:
    - `dd_limits.max_drawdown_pct` debe ser mayor que 0.
    - `atr_stop.atr_multiple` debe ser mayor que 0.
- Devuelve:
  - Lista de errores estructurales.
  - Lista de warnings (recomendaciones/no conformidades suaves).

Estado actual:
- En la validación ejecutada:
  - Errors: 0
  - Warnings: 4 (varias secciones recomendadas ausentes).

---

## 5. Integración en prompts de EXECUTOR/Antigravity

### 5.1 Bloques mínimos recomendados

Para configurar un agente EXECUTOR/Antigravity futuro, se recomienda incluir:

1. Extracto de `.ai/antigravity_operational_protocol.md`:
   - Roles.
   - Ciclo A→D.
   - Guardrails de riesgo.
2. Extracto relevante de `.ai/active_context.md`:
   - Rama actual.
   - Último estado de tests.
   - Snapshots recientes en `/report`.
3. Extracto de `.ai/project_map.md` (opcional):
   - Módulos core detectados.
   - Hotspots de código/tests.

Ejemplo de orden de bloques en prompt:
1. Protocolo Antigravity (resumido o completo).
2. Active context (estado técnico).
3. Mapa de proyecto (secciones relevantes).
4. Tarea concreta a ejecutar.

### 5.2 Reglas de uso

- El agente no debe:
  - Tocar lógica de riesgo ni `risk_rules.yaml` sin:
    - Tests nuevos o ajustados.
    - `pytest` parcial y global cuando corresponda.
    - Actualización de `/report` y `.ai/*`.
- El agente sí puede:
  - Proponer mejoras de tooling (nuevos scripts en `tools/`).
  - Enriquecer el esquema de `config_schema.py`.
  - Sugerir nuevas secciones en `risk_rules.yaml` (documentadas y testadas).

---

## 6. Tests y snapshots

Estado tras la implementación de Antigravity v0.1:

- Baseline antes de Antigravity:
  - `report/pytest_2A_before.txt` → 47 tests OK.
- Tras añadir:
  - `.ai/*` (active_context, decisions_log, project_map, protocolo).
  - `tools/update_project_map.py`.
  - `config_schema.py`.
  - `tools/validate_risk_config.py`.
  - `tests/test_risk_config_schema.py`.

Se ha ejecutado:

- `python tools/validate_risk_config.py`
  - Errors: 0
  - Warnings: 4
  - Informe: `report/validate_risk_config_step5.txt`.
- `python -m pytest -q`
  - 48 tests OK.
  - Snapshot: `report/pytest_antigravity_step5.txt`.

---

## 7. Próximos pasos recomendados

- En fases futuras de riesgo (1D/2A y posteriores):
  - Endurecer progresivamente `config_schema.py` con más campos requeridos.
  - Introducir nuevos tests específicos de configuración de riesgo.
  - Mantener sincronizado el protocolo Antigravity según evolucionen:
    - Módulos de riesgo.
    - Pipelines event-driven.
    - Métricas de riesgo objetivo.

