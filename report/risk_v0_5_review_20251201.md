# Revisión de Código: Risk Manager v0.5

**Fecha:** 2025-12-01
**Versión Revisada:** v0.5 (Draft)
**Archivos:** `risk_manager_v0_5.py`, `tests/test_risk_dd_v0_5.py`, `tests/test_risk_atr_stop_v0_5.py`

---

## 1. Resumen Ejecutivo
El código implementa correctamente la lógica de guardrails solicitada. Las funciones críticas (`compute_drawdown`, `eval_dd_guardrail`, `compute_atr_stop`) son matemáticamente consistentes y robustas ante la mayoría de los casos borde (precios negativos, falta de datos ATR).

Se han ejecutado los tests existentes y una suite extendida de casos límite, pasando todos satisfactoriamente.

## 2. Análisis de Funciones Críticas

### `compute_drawdown`
*   **Correctitud**: Calcula correctamente el High Water Mark (HWM) y el drawdown relativo.
*   **Edge Cases**:
    *   **Curvas Negativas**: Maneja correctamente escenarios de bancarrota (equity < 0), ignorando picos negativos para el cálculo de DD.
    *   **NaN/Inf**: El código actual ignora valores `NaN` silenciosamente (debido a que `NaN > peak` es `False`). Esto evita crashes, pero podría ocultar problemas de datos.
*   **Riesgo**: Asume que `equity_curve` contiene la historia suficiente para determinar el HWM real. Si se pasa una ventana truncada, el DD será relativo al máximo local de esa ventana.

### `eval_dd_guardrail`
*   **Lógica**: Las transiciones `Normal` → `Risk Off Light` → `Hard Stop` respetan estrictamente los umbrales configurados.
*   **Comportamiento**:
    *   En zona `hard_stop`, devuelve `size_multiplier: 0.0` y `allow_new_trades: False`. Esto es seguro.

### `compute_atr_stop`
*   **Lógica**: Implementa correctamente `max(dist_atr, dist_min_pct)`.
*   **Seguridad**: Retorna `None` ante precios inválidos o negativos, lo cual es el comportamiento seguro deseado (no poner stop es mejor que poner un stop erróneo que ejecute inmediatamente, siempre que el sistema maneje el `None`).

## 3. Hallazgos y Posibles Bugs

No se han encontrado bugs críticos que rompan la ejecución, pero sí puntos de atención:

*   **[INFO] Manejo Implícito de NaN**: En `compute_drawdown`, la presencia de `NaN` no genera error ni advertencia.
    *   *Impacto*: Bajo, pero dificulta depuración si los datos vienen sucios.
*   **[INFO] Semántica de `entry_price`**: `compute_atr_stop` usa el nombre `entry_price`. Si se planea usar para Trailing Stops, el nombre puede ser confuso (debería ser `reference_price`). La lógica sigue siendo válida.

## 4. Sugerencias de Mejora (Sin romper API)

1.  **Validación de Datos en Drawdown**:
    Agregar un chequeo simple para filtrar o loguear valores no finitos en `compute_drawdown`.
    ```python
    # Sugerencia no intrusiva
    if not math.isfinite(nav): continue
    ```

2.  **Documentación de Hard Stop**:
    Aclarar en el docstring de `eval_dd_guardrail` que `hard_stop` implica el cese de *nuevas* operaciones, pero no necesariamente la liquidación forzosa de las existentes (eso depende del orquestador).

3.  **Tests Adicionales**:
    Se recomienda integrar los siguientes casos borde a la suite de tests permanente (se ha creado un archivo temporal `tests/test_risk_v0_5_extended.py` con ellos):
    *   `test_compute_drawdown_nan_values`: Verificar que no explota con NaNs.
    *   `test_compute_drawdown_negative_values`: Verificar cálculo con equity negativa.
    *   `test_compute_atr_stop_zero_atr`: Verificar fallback a `min_stop_pct`.

## 5. Conclusión
El módulo está listo para integración experimental. La lógica es conservadora y segura. Se recomienda mantener el archivo `tests/test_risk_v0_5_extended.py` como parte del repositorio para asegurar cobertura de casos extremos.
