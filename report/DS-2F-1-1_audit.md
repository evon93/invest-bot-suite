# DS-2F-1-1_audit

> **Source**: DS-2F-1-1_deepseek_audit.pdf  
> **Ingested**: 2026-01-02 22:15  
> **Note**: Extracted from external model output (web chat)

---

DS-2F-1-1 — Auditoría del Loader OHLCV  
1. Resumen Ejecutivo  
El loader OHLCV implementado en tools/load_ohlcv.py  cumple con el contrato 
especificado: carga datos de archivos CSV/Parquet, normaliza nombres de columnas, 
convierte tipos de datos, ordena por fecha y elimina duplicados. Los 10 tests existentes 
cubren casos básicos y pasan satisfactoriamente.  
Veredicto: APPROVE  — El código es funcional y adecuado para el propósito. Se 
recomiendan mejoras menores para robustez.  
2. Cumplimiento del Contrato  
Requisito  Cumplido  Observaciones  
Input: CSV/Parquet con 
columnas flexibles     Soporta alias comunes (o, h, l, c, vol, 
timestamp, etc.)  
Output: columnas 
canónicas (date, open, high, 
low, close, volume)     Normalización mediante mapeo de alias  
Dtype date: datetime64[ns] 
naive     pd.to_datetime  + eliminación de 
timezone  
Dtype OHLCV: float64     pd.to_numeric  con coerción a float64  
Orden ascendente por date     sort_values("date", 
ascending=True)  
Duplicados eliminados 
(keep last)     drop_duplicates(subset=["date"], 
keep="last")  
Manejo de errores: 
FileNotFoundError, 
ValueError, ImportError     Excepciones apropiadas  
CLI funcional     Exit code 0/1 y summary imprimible  

3. Edge Cases No Cubiertos  
3.1. Datos Inválidos o Problemáticos  
• NaNs en fecha : pd.to_datetime(..., errors="coerce")  convierte a NaT, 
pero no se filtran. Filas con NaT permanecen en el DataFrame.  
• Encoding no UTF -8: CSV con encoding diferente (latin -1, windows -1252) 
causará UnicodeDecodeError . 
• Timestamps numéricos : Columnas de fecha con enteros 
(segundos/milisegundos desde epoch) no se detectan automáticamente.  
• Fechas con hora y timezone : Se elimina timezone, pero no se normaliza la hora 
(ej: convertir a fecha sin hora para datos diarios).  
3.2. Semántica de Datos  
• Columnas extra : Se descartan silenciosamente. Podría ser deseable 
preservarlas opcionalmente.  
• Validación de rangos : No se verifica que high ≥ low, open/close dentro de [low, 
high], volume ≥ 0.  
• Gaps de fechas : No se detectan ni rellenan (decisión de diseño).  
• Deduplicación por granularidad : Si hay fechas con diferente hora pero mismo 
día, se tratarán como duplicados solo si la fecha (día) coincide exactamente.  
3.3. Performance y Robustez  
• Archivos grandes : Carga completa en memoria; podría ser problemático para 
series muy largas.  
• Memoria : No se usa dtype  optimizado en pd.read_csv  (ej: float32  para 
OHLCV).  
• Parquet sin compresión : No se especifica compresión al escribir tests.  
4. Tests Adicionales Recomendados  
Mínimo 3 tests unitarios adicionales (sin romper reproducibilidad):  
def test_nat_dates_are_filtered():  
    """Fechas inválidas (NaT) deben eliminarse o manejarse 
explícitamente."""  
    df = pd.DataFrame({  
        "date": ["2024 -01-01", "invalid", "2024 -01-02"],  
        "open": [100, 101, 102],  
        "high": [105, 106, 107],  

        "low": [95, 96, 97],  
        "close": [102, 103, 104],  
        "volume": [1000, 2000, 3000],  
    }) 
    # Expectativa: fila con "invalid" → NaT → eliminada o marcada  
    # Actual: se conserva como NaT, podría causar problemas en 
ordenamiento  
 
def test_encoding_fallback():  
    """CSV con encoding latin -1 debe manejarse con detección o 
parámetro."""  
    # Crear CSV con caracteres latin -1 (ej: "café")  
    # Verificar que loader no falle con UnicodeDecodeError  
    # Posible solución: try utf -8, luego la tin-1 
 
def test_keep_last_duplicate_logic():  
    """Verificar que 'keep last' funcione correctamente con valores 
diferentes."""  
    df = pd.DataFrame({  
        "date": ["2024 -01-01", "2024 -01-01", "2024 -01-01"],  
        "open": [100, 101, 102],  # Último debe ser 102  
        "high": [105, 106, 107],  
        "low": [95, 96, 97],  
        "close": [102, 103, 104],  
        "volume": [1000, 2000, 3000],  
    }) 
    # Después de ordenar y deduplicar, open debe ser 102 (último del 
grupo)  
  
5. Sugerencias de Mejora (Priorizadas)  
Prioridad Alta (P1)  
1. Filtrar fechas NaT : Después de _parse_date , eliminar filas con 
df["date"].isna() . 
2. Manejo de encoding : Agregar parámetro encoding  (default "utf -8") y/o 
detección automática.  
3. Mensajes de error más informativos : Al faltar columnas, listar las columnas 
disponibles vs. esperadas.  

Prioridad Media (P2)  
4. Warning al eliminar timezone : Loggear warning cuando se detecte y elimine 
timezone.  
5. Parámetro para preservar columnas extra : Opcional 
keep_extra_columns=False . 
6. Validación básica de datos : Opcional validate=True  para verificar high ≥ 
low, etc.  
Prioridad Baja (P3)  
7. Soporte para timestamps numéricos : Detectar columnas de fecha con dtype 
numérico y convertir desde epoch.  
8. Muestreo por rango de fechas : Parámetros start_date , end_date  para filtrar 
durante carga.  
9. Optimización de memoria : Usar dtype  específico en pd.read_csv  para 
columnas OHLCV.  
6. Riesgos Identificados  
1. Pérdida silenciosa de datos : Columnas extra se descartan sin advertencia.  
2. Fechas inválidas conservadas : NaT permanece en DataFrame, afectando 
ordenamientos y agrupaciones.  
3. Problemas de encoding en producción : Archivos CSV de fuentes externas 
podrían fallar.  
4. Timezone inconsciente : Eliminar timezone sin registrar la zona original puede 
afectar análisis temporales.  
7. Conclusión  
El loader OHLCV cumple su función básica adecuadamente y está listo para uso en el 
pipeline de invest -bot-suite. Los tests existentes cubren los casos principales.  
Recomendación de implementación inmediata :  
1. Agregar filtrado de filas con fecha NaT.  
2. Añadir parámetro encoding  al loader (backward -compatible).  
3. Implementar los 3 tests adicionales propuestos.  
Con estas mejoras, el loader será más robusto para datos reales del mundo financiero.  
 

