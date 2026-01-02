# G3-2F-1-1_audit

> **Source**: G3-2F-1-1_gemini_audit.pdf  
> **Ingested**: 2026-01-02 22:15  
> **Note**: Extracted from external model output (web chat)

---

Aquí tienes el informe de auditoría generado bajo la identidad G3-2F-1-1-AUDIT . 
[EXTENDED THOUGHT :: ANALYSIS]  
1. Robustez de Tipos:  El loader es agresivo normalizando ( coerce ), lo cual es 
bueno para evitar crashes inmediatos, pero peligroso si silencia corrupción de 
datos (ej. convertir fechas inválidas a NaT  y dejarlas en el DF).  
2. Invariante de Fechas:  La decisión de hacer tz_localize(None)  es práctica 
para evitar conflictos de "offset -naive vs aware" en Pandas, pero asume que el 
input ya viene en el "tiempo base" correcto (UTC o local consistente). Si el CSV 
mezcla zonas horarias, esto corromperá la secuencia temporal.  
3. Gestión de Vacíos:  El código actual no elimina filas con NaN  o NaT . Un 
open=NaN  romperá cualquier indicador técnico downstream (TA -Lib). Es un 
punto crítico.  
 
[EDITOR :: report/G3 -2F-1-1_audit.md]  
# G3-2F-1-1 — Audit: Local OHLCV Loader  
 
**ID:** G3 -2F-1-1-AUDIT  
**Fecha:** 2026 -01-02 
**Target:** `tools/load_ohlcv.py` & `tests/test_load_ohlcv.py`  
**Estado:** Aprobado con Riesgos Controlados (Yellow).  
 
---  
 
## 1. Invariantes del Output  
 
El contrato de datos que `load_ohlcv.py` garantiza (y que los 
consumidores downstream deben esperar) es:  
 
1.  **Schema Estricto:** El DataFrame resultante **siempre** tiene 
exactamente estas 6 columnas, en este orden (implícito por 
reindexación/selección):  
    *   `date` , `open`, `high`, `low`, `close`, `volume`.  
2.  **Tipos de Datos (Dtypes):**  
    *   `date`: `datetime64[ns]` (Numpy native), **Offset -Naive** 
(sin zona horaria).  
    *   `OHLCV`: `float64` (Standard float).  
3.  **Ordenamiento:** Estrictamente ascendente por `date`.  
4.  **Unicidad:** No existen duplicados en `date`.  
5.  **Deduplicación:** Política `keep='last'`. Ante un conflicto de 

timestamp, la última fila leída del archivo prevalece 
(sobrescritura).  
6.  **Index:** `RangeIndex` (0...N -1). La columna `date` **no** es 
el índice.  
 
---  
 
## 2. Matriz de Edge Cases (Priorizada)  
 
Análisis de robustez ante entradas hostiles o sucias:  
 
| Prioridad | Edge Case | Comportamiento Actual | Riesgo |  
| :--- | :--- | :--- | :--- | 
| **Alta** | **Parse Failures (NaNs)** | `errors='coerce'` convierte 
basura a `NaN`/`NaT`, pero **mantiene la fila**. | **Crítico.** TA -
Lib o cálculos vectorizados fallarán si reciben `NaN` en precios o 
`NaT` en fechas. |  
| **Alta** | **Unix Timestamps** | `pd.to_datetime` sin `unit` puede 
interpretar enteros grandes como nanosegundos desde 1970 (fecha 
incorrecta) e n lugar de segundos/ms. | Alto. Un CSV con unix epoch 
(ej: `1700000000`) podría parsearse como el año 1970. |  
| **Media** | **Timezone Stripping** | `dt.tz_localize(None)` 
elimina la info de zona. Si el input mezcla UTC y EST, el orden 
temporal relativo se corrompe. | Medio. Asumimos input consistente. 
| 
| **Media** | **Empty File (Headers only)** | Devuelve DF vacío con 
columnas correctas. | Bajo (Correcto). El consumidor debe manejar DF 
vacío. |  
| **Baja** | **Volumen "None"** | Si volumen falta o es stri ng 
vacío, se convierte a `NaN`. | Medio. Algunas estrategias requieren 
volumen. |  
| **Baja** | **Separadores de miles** | "1,200.50". `pd.to_numeric` 
no maneja comas por defecto. Se convertirá a `NaN`. | Bajo. Formato 
no estándar en data raw científica. |  
 
---  
 
## 3. Tests Mínimos Adicionales (Propuesta)  
 
Se recomienda añadir estos casos a `tests/test_load_ohlcv.py` para 
blindar el contrato.  
 

### 3.1. `test_load_garbage_values`  
*   **Objetivo:** Verificar comportamiento ante datos no numéricos.  
*   **Fixture:** CSV con `open="N/A"`, `high="foobar"`.  
*   **Validación Actual:** Confirmar que devuelve `NaN` (y decidir 
si eso es aceptable, ver sección 4).  
 
### 3.2. `test_unix_timestamp_parsing`  
*   **Objetivo:** Verificar si detecta timestamps numéricos 
(segundos/milisegundos).  
*   **Fixture:** CSV con columna `time` conteniendo enteros ej: 
`1609459200`.  
*   **Validación:** La fecha resultante debe ser `2021 -01-01`, no 
`1970-01-01...`.  
 
### 3.3. `test_empty_file_with_header`  
*   **Objetivo:** Robustez ante archivos vacíos.  
*   **Fixture:** CSV solo con header 
`date,open,high,low,close,volume`.  
*   **Validación:** `len(df) == 0`, columnas presentes, dtypes 
correctos (no `object`).  
 
### 3.4. `test_tz_stripping_consistency`  
*   **Objetivo:** Confirmar que una fecha con offset `2024 -01-01 
12:00:00+05:00` se convierte a `2024 -01-01 12:00:00` (Wall Time) y 
no a UTC.  
*   **Fixture:** CSV con fechas ISO8601 c on offset.  
 
---  
 
## 4. Recomendaciones (Patch Intent)  
 
No se requiere reescribir todo, pero se sugieren estos ajustes 
defensivos:  
 
### A. Política de NaNs (Recomendado: Strict Drop)  
Actualmente el loader devuelve filas con `NaN` si el parseo falla.  
*   **Cambio:** Añadir paso `df.dropna(subset=['date', 'close'])` al 
final.  
*   **Razón:** Un OHLCV con fecha o cierre inválido es inútil y 
peligroso para el backtest.  
*   **Impacto:** Reduce filas devueltas, pero garantiza integridad.  
 

### B. Inferencia de Fecha (Smart Parsing)  
*   **Cambio:** Si `pd.to_datetime` falla o devuelve fechas cercanas 
a 1970 para inputs numéricos grandes, intentar inferir `unit='s'` o 
`unit='ms'`.  
*   **Razón:** Evitar el error común de Unix Epoch en nanosegundos.  
 
### C. Validación de Volumen  
*   **Cambio:** `fillna(0)` para la columna `volume`.  
*   **Razón:** Es mejor asumir volumen 0 que tener `NaN` que se 
propague en medias móviles de volumen.  
 
---  
 
**Conclusión:**  
El loader es funcional y cumple el "Happy Path". Sin embargo, para 
uso en Fase 2G (Calibración Robusta), debe endurecerse contra `NaNs` 
y ambigüedad de timestamps. Se aprueba su uso para prototipado (2F), 
pero se marca deuda técnica para 2G.  
  
[TERMINAL :: INSTRUCTION]  Usuario, he generado el reporte de auditoría en 
report/G3 -2F-1-1_audit.md . Léelo y guárdalo. Este reporte servirá de base para 
cuando necesites "endurecer" el loader en la siguiente fase. Por ahora, con el código 
actual es suficiente para descargar data de Yahoo y probar.  
 

