---
trigger: always_on
---

# Regla de proyecto — `invest-bot-suite`

## Contexto del repo

- Proyecto: **invest-bot-suite** (backtester + gestor de riesgo en Python).
- Tech stack principal: Python 3.12, pytest, numpy, pandas, pyyaml.
- Entorno recomendado:
  - Sistema: WSL2 Ubuntu 24.04 sobre Windows 11.
  - Ruta del proyecto: `/mnt/c/Users/ivn_b/Desktop/invest-bot-suite`.
  - Entorno virtual: `.venv` (usar siempre `python -m ...` desde ahí).
- Ramas relevantes:
  - Rama de trabajo por defecto: `orchestrator-v2`.
  - Tags de baseline: `baseline_20251121_D0` y backups `*.bak_*`.

Tu misión es ayudar a **inspeccionar, modificar y probar** el código del proyecto de forma segura y trazable, minimizando errores y dejando siempre rastro de lo que haces.

---

## Reglas generales de comportamiento

1. **Nunca asumas el contexto del repo a ciegas**  
   - Cuando se te pida algo no trivial, primero:
     - Muestra un plan breve de 3–5 pasos.
     - Usa comandos tipo `ls`, `tree`, `cat`, `nl -ba`, etc., para entender el código relevante.
   - Evita “inventar” rutas o nombres de archivos; verifícalos en el sistema de archivos.

2. **Usa siempre el entorno virtual del proyecto**
   - Asume que debes ejecutar comandos como:
     - `source .venv/bin/activate` (si procede en terminal nueva).
     - `python --version`, `python -m pytest --version` para comprobar entorno.
   - Ejecuta tests con `python -m pytest`, nunca con `pytest` a secas.

3. **Sin internet, sin dependencias globales**
   - No uses red, APIs externas ni paquetes que no estén en `requirements.txt` / `requirements.lock`, salvo que el usuario lo pida explícitamente.
   - No instales paquetes globalmente ni toques la configuración de sistema fuera del repo.

4. **Seguridad en cambios de código**
   - Antes de cambiar un archivo Python importante:
     - Crea o respeta un backup local con sufijo `*.bak_XX` cuando el usuario lo pida.
   - Aplica cambios de forma **mínima y explícita**:
     - Explica qué función/clase vas a tocar y por qué.
     - Mantén el estilo del código existente (tipos, nombres, docstrings).
   - Prioriza refactors pequeños y verificables frente a reescrituras grandes.

5. **Uso de tests y reportes**
   - Después de cambios relevantes en el backtester o gestor de riesgo:
     - Ejecuta tests focalizados (por ejemplo, `python -m pytest tests/test_backtest_deepseek.py -q`).
     - Si el usuario lo pide, ejecuta `python -m pytest` completo.
   - Guarda los resultados en `report/` siguiendo una convención tipo:
     - `report/pytest_YYYYMMDD_contexto.txt`
   - Resume siempre:
     - número de tests, cuántos pasan/fallan, nombres de tests fallidos y motivo.

---

## Backtester y métricas (foco actual)

Cuando trabajes sobre:

- `backtest_initial.py`
- `tests/test_backtest_deepseek.py`

sigue estas pautas:

1. **Compatibilidad con tests existentes**
   - Cualquier cambio debe:
     - Mantener la interfaz pública de `SimpleBacktester` y `calculate_metrics`.
     - Hacer que los tests de `tests/test_backtest_deepseek.py` sean lo más robustos posible sin “hacer trampas” (no hardcodear resultados).

2. **Manejo de casos borde**
   - Asegúrate de que el backtester:
     - Soporta Series y DataFrames (activos únicos y multi-activo).
     - No revienta con precios 0 o negativos; maneja esos casos de forma explícita.
     - Registra trades solo cuando hay cambios reales en las posiciones.

3. **Métricas numéricas**
   - `calculate_metrics(df)` debe:
     - Evitar divisiones por cero o `nan` silenciosos.
     - Devolver siempre números finitos (`float`) para:
       - `cagr`, `total_return`, `max_drawdown`, `sharpe_ratio`, `volatility`.
     - En situaciones degeneradas (por ejemplo, serie muy corta o valor inicial 0):
       - Devolver métricas razonables (ej. `0.0` o límites bien definidos), documentando la decisión en un comentario.

---

## Flujo estándar de trabajo en este proyecto

Cuando el usuario pida una mejora, fix o investigación, sigue este flujo básico:

1. **Entender la petición y localizar código**
   - Resume en 2–3 frases lo que se quiere.
   - Identifica archivos y funciones afectados.

2. **Leer antes de escribir**
   - Inspecciona el código existente con `cat` / `nl -ba`.
   - Si hay tests relacionados, léelos para entender expectativas.

3. **Proponer plan mínimo**
   - Presenta un mini-plan:
     - Qué se va a cambiar.
     - Qué tests se van a ejecutar.
     - Posibles riesgos.

4. **Aplicar cambios atómicos**
   - Modifica el código en uno o pocos commits lógicos (aunque el commit lo haga el usuario).
   - Mantén un estilo claro y añade comentarios solo cuando aporten información estructural.

5. **Verificar**
   - Ejecuta tests relevantes.
   - Si fallan, analiza el diff y ajusta con el cambio mínimo adicional.
   - Documenta el resultado (por ejemplo, añadiendo/actualizando un archivo de log en `report/` si el usuario lo solicita).

---

## Cosas que NO debes hacer excepto instrucción explícita

- No borrar ni sobrescribir archivos de backup `*.bak_*`.
- No renombrar archivos o mover directorios de forma masiva.
- No cambiar configuración de git (remotes, branches) ni hacer `git commit`, `git push` por tu cuenta.
- No introducir refactors grandes de arquitectura sin que el usuario lo pida de forma clara.

---

## Estilo de comunicación

- Explica siempre:
  - Qué has inspeccionado.
  - Qué comandos has ejecutado.
  - Qué concluyes y qué propones.
- Mantén las respuestas técnicas y concisas, en español, salvo que el usuario pida lo contrario.
- Cuando exista ambigüedad, ofrece **1–2 opciones** claras y pide al usuario que elija antes de seguir.

