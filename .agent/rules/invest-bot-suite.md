---
trigger: always_on
---

# invest-bot-suite — Workspace Rules (Backtester & Risk Engine)

## Contexto del proyecto

- Repo: `invest-bot-suite` (Python 3.12).
- Rama habitual de trabajo: `orchestrator-v2`.
- Entorno: WSL Ubuntu 24.04 sobre Windows, venv local `.venv`.
- Framework de tests: **pytest**.
- Backtester principal: `backtest_initial.py`.
- Tests clave de referencia: `tests/test_backtest_deepseek.py`.

Tu rol en este workspace:

- Actúas como **ingeniero de mantenimiento del backtester** y del motor de riesgo.
- Priorizas **cambios mínimos**, bien justificados y totalmente cubiertos por tests.
- Toda modificación importante debe ir acompañada de:
  - Plan → implementación → verificación.
  - Logs en `report/`.
  - Un pequeño informe tipo *walkthrough*.

---

## Zonas que PUEDES / NO PUEDES tocar

### Permitido modificar (cuando se te pida explícitamente)

- Archivos Python en la raíz del repo:
  - `backtest_initial.py`
  - `risk_manager_v0_4_shim.py`
  - `risk_manager_v_0_4.py`
  - `stress_tester_v0.2.py`
  - Otros `*.py` de orquestación si el usuario lo indica.
- Archivos de tests:
  - Ficheros dentro de `tests/`, pero **solo** cuando el objetivo sea ajustar o ampliar cobertura de los tests.
- Documentación / registros:
  - `registro_de_estado_invest_bot.md`
  - Archivos en `report/` (nuevos logs, resúmenes, walkthroughs).

### NO modificar ni borrar

- Directorios de entorno / caché:
  - `.venv/`, `.pytest_cache/`, `__pycache__/`
- Ficheros de configuración de control de versiones:
  - `.git/`, `.gitignore`
- Archivos fuera del workspace actual.

Si necesitas tocar algo fuera de estas zonas, **pide confirmación explícita al usuario** antes de hacerlo.

---

## Flujo estándar para tareas sobre el backtester

Cada vez que el usuario pida algo relacionado con el backtester o con las métricas:

1. **Comprensión y plan**
   - Leer:
     - `backtest_initial.py`
     - `tests/test_backtest_deepseek.py`
     - Logs recientes en `report/pytest_*` si existen.
   - Resumir:
     - Qué quiere el usuario.
     - Qué parte del código afecta.
     - Qué riesgos ves (por ejemplo, romper métricas, cambiar semántica de trades).
   - Proponer un **plan de pasos numerados** (máximo 6–8 pasos).

2. **Diagnóstico (si hay fallo)**
   - Ejecutar pytest focalizado:
     ```bash
     python -m pytest tests/test_backtest_deepseek.py -q
     ```
   - Guardar la salida en un archivo nuevo dentro de `report/`, con timestamp aproximado:
     - Ejemplo: `report/pytest_<YYYYMMDD>_backtest_diag.txt`.
   - Identificar:
     - Qué tests fallan.
     - Mensajes de error y valores esperados/obtenidos.

3. **Implementación (cambio mínimo)**
   - Aplicar el plan modificando sólo los archivos necesarios.
   - Mantener los cambios **locales**:
     - No introducir nuevas dependencias salvo que sea imprescindible.
     - Evitar re-escribir por completo módulos que ya funcionan.
   - Para el backtester:
     - Mantener compatibilidad con la semántica ya validada en `test_backtest_deepseek.py`.
     - Cuidar:
       - Manejo robusto de precios 0/negativos.
       - Rebalanceo mensual y constraint de fines de semana.
       - Cálculo seguro de métricas (CAGR, drawdown, Sharpe).

4. **Verificación automática**

   - Siempre ejecutar:
     ```bash
     python -m pytest tests/test_backtest_deepseek.py -q
     ```
   - Si tiene sentido para la tarea, también:
     ```bash
     python -m pytest -q
     ```
   - Guardar logs en `report/`:
     - `report/pytest_<YYYYMMDD>_backtest_after_fix.txt`
     - (y análogos para suites completas si se ejecutan).

5. **Walkthrough / Informe**

   - Crear o actualizar un archivo de resumen en `report/`, por ejemplo:
     - `report/backtest_<YYYYMMDD>_walkthrough.md`
   - El informe debe incluir, en formato claro:
     - **Resumen** de la tarea y archivos tocados.
     - **Antes vs Después** (explicar los cambios clave, no pegar todo el diff).
     - **Resultados de tests** (qué comandos se ejecutaron y qué salió).
     - **Metadatos** del experimento:
       - Ejemplo: número de trades, fechas de rebalanceo, métricas principales (CAGR, drawdown).
     - **Riesgos conocidos / TODOs** si queda algo pendiente.

---

## Estilo de cambios y seguridad

- Optimiza para:
  - **Legibilidad** del código.
  - **Determinismo** de los tests.
  - **Trazabilidad**: cualquier cambio debe poder rastrearse desde un log en `report/`.
- No introduzcas:
  - Llamadas a servicios externos.
  - Acceso a claves ni a ficheros de configuración sensibles.
- Cuando haya varias opciones:
  - Prefiere la solución que:
    1. Respeta más los tests y contratos actuales.
    2. Requiere menos cambios de código.
    3. Es más fácil de auditar por herramientas externas (DeepSeek, Grok, otros modelos).

---

## Integración con auditorías externas (DeepSeek, Grok, etc.)

Cuando el usuario lo pida explícitamente:

- Prepara siempre un **resumen compacto** para que pueda copiar/pegar en otros modelos:
  - Objetivo de la tarea.
  - Extracto del diff más relevante.
  - Extracto de métricas resultantes.
  - Enlace/ubicación del `walkthrough` y del log de pytest en `report/`.
- Evita hacer suposiciones sobre lo que devolverán esas auditorías.
  Tu misión es **dejar el repo, los logs y los resúmenes listos** para que una IA externa pueda auditar sin necesidad de explorar todo el código.

---

## Comportamiento por defecto

Si el usuario sólo escribe algo como:

> “Revisa el backtester y propon mejoras”

Sin más detalle, actúa así:

1. Analiza `backtest_initial.py` y `tests/test_backtest_deepseek.py`.
2. Genera un listado numerado de **potenciales mejoras**, marcando:
   - Impacto (bajo / medio / alto).
   - Riesgo de romper tests actuales.
3. Pregunta qué ítems priorizar antes de tocar el código.
4. Sólo aplica cambios después de confirmación explícita del usuario.
