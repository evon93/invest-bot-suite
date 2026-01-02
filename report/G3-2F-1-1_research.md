# G3-2F-1-1_research

> **Source**: G3-2F-1-1_gemini_research.pdf  
> **Ingested**: 2026-01-02 22:15  
> **Note**: Extracted from external model output (web chat)

---

Aquí tienes el informe de investigación solicitado, optimizado para integrarse con el 
loader que acabas de implementar.  
[EXTENDED THOUGHT :: ANALYSIS]  
1. Calidad vs. Accesibilidad:  Para un bot institucional (simulado), la calidad del 
dato es crítica.  
a. Binance Vision  es la fuente "Gold Standard" (datos crudos del exchange, 
granularidad de 1m), pero viene en ZIPs mensuales sin cabeceras. 
Requiere pre -procesamiento.  
b. CryptoDataDownload  es accesible y ya viene en CSV, pero a veces tiene 
filas de metadatos al inicio que pueden romper parsers simples si no se 
saltan.  
c. Yahoo Finance  es ruidoso para Crypto (precio agregado), pero es vital 
tenerlo en el radar porque será la fuente primaria para la parte de 
"Stocks" del bot.  
2. Compatibilidad con load_ohlcv.py : 
a. El loader implementado normaliza columnas ( open , high , low , close ). 
b. Binance NO trae cabeceras. El usuario tendrá que añadirlas 
manualmente o el loader necesitará un flag --no-header . (Asumiré 
descarga manual y edición rápida de cabecera para esta fase).  
c. Yahoo trae cabeceras estándar ( Open , High , etc.) que el loader 
normalizará bien.  
3. Recomendación de Estrategia:  Usar Yahoo Finance  para pruebas rápidas de 
integración (fácil descarga) y Binance Vision  para el Backtest serio (Fase 
2G/3A).  
 
[EDITOR :: report/GR -2F-1-1_research.md]  
# GR-2F-1-1 — Research: Fuentes de Datos Históricos (BTC/ETH)  
 
**ID:** GR -2F-1-1 
**Fecha:** 2026 -01-02 
**Objetivo:** Identificar fuentes de datos históricos manuales 
compatibles con `load_ohlcv.py` para Crypto y Stocks.  
 
---  
 
## 1. Fuente A: Binance Vision (Public Data)  
**Perfil:** "Gold Standard" para Crypto. Datos oficiales del 

exchange con máxima granularidad.  
**Uso recomendado:** Backtesting de alta fidelidad y calibración 
final.  
 
*   **URL:** `https://data.binance.vision/`  
*   **Granularidad:** 1s, 1m, 5m, 15m, 1h, 1d, etc.  
*   **Rango:** Desde el listado del par (BTC: ~2017, ETH: ~2017).  
*   **Formato:** ZIPs mensuales/diarios conteniendo CSVs.  
*   **Columnas (Sin Cabecera):**  
    `Open time, Open, High, Low, Close, Volume, Close time, Quote 
asset volume, Number of trades, Taker buy base asset volume, Taker 
buy quote asset vol ume, Ignore`  
*   **Licencia:** Pública (sin restricciones explícitas para uso 
personal/no comercial).  
 
### Checklist de Descarga Reproducible  
1.  Navegar a: 
`https://data.binance.vision/?prefix=data/spot/monthly/klines/`  
2.  Seleccionar par: `BTCUSDT` o `ETHUSDT`.  
3.  Seleccionar timeframe: `1h` (recomendado para pruebas) o `1d`.  
4.  Descargar el ZIP del mes más reciente (ej. `BTCUSDT -1h-2025-
11.zip`).  
5.  Descomprimir.  
6.  **Acción Manual Requerida:** El CSV no tiene cabeceras. Abrir y 
añadir primera línea : 
    
`timestamp,open,high,low,close,volume,close_time,quote_vol,trades,tb
_base,tb_quote,ignore`  
 
---  
 
## 2. Fuente B: Yahoo Finance  
**Perfil:** "Generalista". Cobertura global de Stocks y Crypto 
(agregado).  
**Uso recomendado:** Prototipado rápido y validación del loader para 
Stocks.  
 
*   **URL:** `https://finance.yahoo.com/`  
*   **Granularidad:** Diario (histórico completo), Semanal, Mensual. 
(Intradía limitado).  
*   **Rango:** BTC desde 2014.  
*   **Formato:** CSV directo.  

*   **Columnas (Con Cabecera):**  
    `Date, Open, High, Low, Close, Adj Close, Volume`  
*   **Licencia:** Uso personal informativo. No redistribución.  
 
### Checklist de Descarga Reproducible  
1.  Buscar `BTC -USD` en la barra de búsqueda.  
2.  Clic en pestaña **"Historical Data"**.  
3.  Time Period: **"Max"**.  
4.  Frequency: **"Daily"**.  
5.  Clic en **"Apply"** y luego **"Download"**.  
6.  **Compatibilidad:** `load_ohlcv.py` debería normalizar `Date` -> 
`date` automáticamente.  
 
---  
 
## 3. Fuente C: CryptoDataDownload  
**Perfil:** "Intermedio". Ag regador de exchanges específicos en 
formato amigable.  
**Uso recomendado:** Si se necesita data de un exchange específico 
(ej. Coinbase) sin procesar ZIPs.  
 
*   **URL:** `https://www.cryptodatadownload.com/data/`  
*   **Granularidad:** 1h, 1d (Minutera disponible pero a veces 
limitada).  
*   **Rango:** Variable (2018+).  
*   **Formato:** CSV. **Nota:** Suele incluir 1 fila de metadatos 
antes del header real.  
*   **Columnas:** `Unix, Date, Symbol, Open, High, Low, Close, 
Volume...`  
*   **Licencia:** Uso personal /investigación.  
 
### Checklist de Descarga Reproducible  
1.  Ir a "Binance" o "Coinbase Pro" section.  
2.  Buscar `BTC/USDT` (Hourly o Daily).  
3.  Clic "Download CSV".  
4.  **Acción Manual Requerida:** Abrir CSV y borrar la fila 1 si 
contiene texto legal/meta (el header debe ser la fila 1).  
 
---  
 
## 4. Comparativa y Selección  
 

| Fuente | Calidad | Dificultad Proceso | Cobertura | Recomendación 
| 
| :--- | :--- | :--- | :--- | :--- | 
| **Binance Vision** |       | Alta (ZIPs, sin header) | 
Solo Crypto | **Producción/Calibración** |  
| **Yahoo Finance** |     | Baja (Click & Run) | Crypto + 
Stocks | **Dev/Test Rápido** |  
| **CryptoDataDownload**|      | Media (Limpieza header) | Top 
Exchanges | Alternativa |  
 
**Decisión para Fase 2F:**  
Descargar manualmente **Yahoo Finance (BTC -USD, Daily)** para 
verificar el pipeline de `load_ohlcv. py` inmediatamente, ya que 
requiere cero pre -procesamiento y valida la lógica de normalización 
de fechas. Para la fase de calibración seria (2G), pasaremos a 
**Binance Vision**.  
  
[TERMINAL :: INSTRUCTION]  Usuario, he generado el reporte de investigación. Por 
favor, crea el archivo report/GR -2F-1-1_research.md  con el contenido de arriba.  
Una vez creado, te sugiero que descargues un CSV de prueba (puede ser de Yahoo 
Finance por simplicidad) y lo coloques en data/raw/  para probar tu nuevo script 
load_ohlcv.py . 
 

