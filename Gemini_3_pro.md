Aquí tienes la revisión sénior del código propuesto para el módulo de gestión de riesgo `v0.5`.

### RESUMEN DE HALLAZGOS

*   **Arquitectura y Diseño:** El uso de métodos estáticos (`@staticmethod`) para las funciones de cálculo (`compute_drawdown`, `eval_dd_guardrail`, `compute_atr_stop`) es excelente. Facilita enormemente los tests unitarios y desacopla la lógica pura del estado de la clase.
*   **Defensividad:** El código es robusto en cuanto a tipos de datos. El uso de `try-except` para conversiones a `float` y validaciones de `None` previene caídas del sistema en tiempo de ejecución (RuntimeErrors).
*   **Lógica de Negocio:**
    *   La lógica de **Stop Loss (ATR)** implementa correctamente un mecanismo de "suelo" (`min_stop_pct`), lo cual evita stops ridículamente ajustados en regímenes de baja volatilidad.
    *   La lógica de **Drawdown** es matemáticamente estándar (High-Water Mark).
    *   La lógica de **Guardrail** implementa correctamente la transición de estados (Normal -> Soft -> Hard).

### POSIBLES BUGS O RIESGOS DE SEGURIDAD

1.  **Fallo "Abierto" en `eval_dd_guardrail` (Riesgo Moderado/Alto):**
    *   **El problema:** Si `dd_value` es inválido (ej. `None`, `NaN` o un string corrupto), el bloque `except` retorna el estado `"normal"` con `size_multiplier: 1.0`.
    *   **Por qué es peligroso:** En un sistema de riesgo, si no podemos determinar la exposición actual (el drawdown es desconocido), **no deberíamos asumir que todo está bien**. Asumir "Normal" ante falta de datos es un comportamiento *agresivo*, no conservador.
    *   **Consecuencia:** Si el cálculo de equity falla silenciosamente, el sistema podría seguir operando a tamaño completo mientras la cuenta se desangra.

2.  **Referencia de `peak` inicial en `compute_drawdown`:**
    *   **El problema:** Si la curva de equity comienza en negativo o cero (ej. datos normalizados incorrectamente o PnL acumulado en lugar de Equity total), la condición `if peak <= 0: continue` hará que el drawdown sea siempre 0.0 hasta que la cuenta suba por encima de 0.
    *   **Consecuencia:** Podrías tener una caída de -100 a -200 y el sistema reportaría 0% DD.

### EDGE CASES QUE FALTAN EN LOS TESTS

Aunque los tests cubren lo básico, faltan escenarios de frontera críticos para un sistema financiero:

1.  **Límites exactos en Guardrail:**
    *   No hay tests que verifiquen qué pasa exactamente cuando `dd == max_dd_soft` o `dd == max_dd_hard`. ¿Es inclusivo o exclusivo? (El código usa `<`, por lo que la igualdad cae en el cubo siguiente, más restrictivo. Esto es correcto/conservador, pero debe testearse explícitamente).
2.  **ATR vs Min Pct:**
    *   Falta un test donde `dist_atr < dist_min_pct`. Actualmente se prueba cuando ATR es `None`, pero no cuando el ATR es válido pero muy pequeño (para confirmar que `max()` funciona).
3.  **Equity Curve con Ceros:**
    *   Una curva `[100, 0, 50]`. El cálculo debería manejar la división por cero o el drawdown del 100% correctamente.
4.  **Stop Triggered con igualdad:**
    *   Verificar explícitamente que si `last_price == stop_price`, se dispara (el código usa `<=` y `>=` lo cual es correcto, pero un test explícito da seguridad).

### SUGERENCIAS DE MEJORA DEL CÓDIGO

#### 1. Cambiar a "Fail-Safe" en `eval_dd_guardrail`
En lugar de retornar "normal" ante errores, retorna un estado de precaución o bloqueo.

```python
# En RiskManagerV05.eval_dd_guardrail
except (TypeError, ValueError):
    # SUGERENCIA: Ante duda, no operar o reducir tamaño drásticamente.
    return {
        "state": "data_error",  # Estado explícito de error
        "allow_new_trades": False,
        "size_multiplier": 0.0,
        "hard_stop": True, # O False si quieres permitir cierres, pero bloquear aperturas
    }
```

#### 2. Logging en métodos estáticos
Los métodos estáticos capturan excepciones silenciosamente. Sería ideal pasar el logger o permitir que la excepción suba (o loguear a `logging` root si es crítico), para que el operador sepa que el cálculo de riesgo falló por un input inválido.

#### 3. Refinar `compute_drawdown` para Equity vs PnL
Asegurar en la documentación (docstring) que `equity_curve` debe ser *Total Equity* (balance > 0) y no PnL acumulado, ya que el cálculo de porcentaje depende de un denominador positivo. Si se usa PnL, el cálculo de DD porcentual no tiene sentido matemático estándar.

### SUGERENCIAS DE TESTS ADICIONALES

Añade estos tests a `tests/test_risk_dd_v0_5.py` y `tests/test_risk_atr_stop_v0_5.py`:

```python
# --------------------------------------------------------------------------- #
#  Adiciones a tests/test_risk_dd_v0_5.py
# --------------------------------------------------------------------------- #

def test_eval_dd_guardrail_boundary_conditions():
    """Verifica comportamiento exacto en los umbrales."""
    cfg = {"max_dd_soft": 0.05, "max_dd_hard": 0.10, "size_multiplier_soft": 0.5}
    
    # Caso exacto en el límite soft (0.05). 
    # Código actual: if dd < 0.05 (Normal) else ...
    # Por tanto 0.05 debería caer en risk_off_light.
    res_soft = RiskManagerV05.eval_dd_guardrail(0.05, cfg)
    assert res_soft["state"] == "risk_off_light"
    
    # Caso exacto en el límite hard (0.10).
    # Debería caer en hard_stop.
    res_hard = RiskManagerV05.eval_dd_guardrail(0.10, cfg)
    assert res_hard["state"] == "hard_stop"

def test_compute_drawdown_crash_to_zero():
    """Verifica comportamiento si la cuenta quiebra (llega a 0)."""
    curve = [100.0, 50.0, 0.0]
    result = RiskManagerV05.compute_drawdown(curve)
    assert math.isclose(result["max_dd"], 1.0, rel_tol=1e-9) # 100% DD

# --------------------------------------------------------------------------- #
#  Adiciones a tests/test_risk_atr_stop_v0_5.py
# --------------------------------------------------------------------------- #

def test_compute_atr_stop_atr_too_small():
    """El ATR es válido pero menor que el stop mínimo porcentual."""
    cfg = {"atr_multiplier": 1.0, "min_stop_pct": 0.05} # 5% min
    # Price 100. Min stop = 5.
    # ATR = 2. Multiplier = 1 -> Dist ATR = 2.
    # Se debe elegir max(2, 5) = 5. Stop Long = 95.
    stop = RiskManagerV05.compute_atr_stop(100.0, 2.0, "long", cfg)
    assert math.isclose(stop, 95.0, rel_tol=1e-9)

def test_is_stop_triggered_exact_boundary():
    """Verifica que tocar el precio exacto dispara el stop."""
    # Long: Stop en 100, precio toca 100 -> True
    assert RiskManagerV05.is_stop_triggered("long", 100.0, 100.0) is True
    # Short: Stop en 100, precio toca 100 -> True
    assert RiskManagerV05.is_stop_triggered("short", 100.0, 100.0) is True
```