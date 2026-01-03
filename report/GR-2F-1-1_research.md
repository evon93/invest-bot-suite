# GR-2F-1-1_research

> **Source**: GR-2F-1-1_grok_research.pdf  
> **Ingested**: 2026-01-02 22:15  
> **Note**: Extracted from external model output (web chat)

---

GR-2F-1-1_research.md  
Introducción  
Este reporte propone tres fuentes confiables para datos históricos de OHLCV de BTC y 
ETH, con licencias adecuadas para uso personal o educativo. Las fuentes permiten 
descargas manuales estables en formato CSV (y conversión a Parquet si se desea). Se 
basa e n investigación de sitios abiertos, enfocando en reproducibilidad sin requerir 
APIs pagadas o modificaciones al repositorio. Las propuestas evitan fuentes con 
restricciones comerciales estrictas.  
Fuente 1: CryptoDataDownload  
• Qué ofrece : Datos OHLCV gratuitos para BTC y ETH (pares como BTCUSDT, 
ETHUSDT) de varios exchanges (e.g., Binance, Coinbase). Granularidades: 1 -
minuto, horaria, diaria. Rangos de fechas: Varía por exchange y par, típicamente 
desde 2017 -2021 hasta fecha actual (e.g.,  2021 -2025 para algunos pares en 
Binance).  
• Condiciones/Licencia resumida : Licencia Creative Commons Attribution -
NonCommercial -ShareAlike 4.0 International (CC BY -NC-SA 4.0). Gratuita para 
uso personal/educativo; no comercial sin suscripción PRO. Debes atribuir la 
fuente y compartir derivados bajo la misma licencia.  
• Formato típico de columnas : CSV con columnas como: unix (timestamp), date 
(fecha legible), symbol (e.g., BTCUSDT), open, high, low, close, volume, 
volume_base, volume_quote, trades.  
• Checklist de descarga reproducible : 
o Visita https://www.cryptodatadownload.com/data/  y selecciona un 
exchange (e.g., Binance).  
o Busca el par deseado (e.g., BTCUSDT o ETHUSDT) en la tabla de 
símbolos.  
o Elige la granularidad (e.g., hourly o daily).  
o Haz clic en el enlace de descarga CSV directo (no requiere registro para 
la mayoría).  
o Verifica el rango de fechas en la página (e.g., desde 2017 hasta 2025).  
o Guarda el archivo; opcionalmente, convierte a Parquet usando pandas: 
pd.read_csv('file.csv').to_parquet('file.parquet') . 
o Nota: Para reproducibilidad, anota la URL exacta y fecha de descarga.  

Fuente 2: CoinGecko  
• Qué ofrece : Datos históricos de precios, market cap y volumen para BTC y ETH. 
Granularidades: Diaria (estándar gratuita), horaria o minutal con limitaciones. 
Rangos de fechas: Hasta 365 días gratis; desde 2013 con planes pagos, pero 
métodos gratuitos cubren periodos  recientes (e.g., últimos 30 -365 días).  
• Condiciones/Licencia resumida : Gratuita para uso personal/educativo vía API 
Demo (con límites). Gobernada por Términos de Servicio de CoinGecko; no para 
uso comercial intensivo sin pago. Atribución recomendada.  
• Formato típico de columnas : CSV con columnas como: date (datetime), 
price_usd, market_cap_usd, volume_24h_usd. Para OHLC: open, high, low, 
close, volume (vía endpoint específico).  
• Checklist de descarga reproducible : 
o Regístrate en CoinGecko para una clave API Demo gratuita 
(https://www.coingecko.com/en/api ). 
o Para no -code: Usa Google Sheets o Excel con el endpoint 
https://api.coingecko.com/api/v3/coins/bitcoin/market_cha
rt?vs_currency=usd&days=365&interval=daily&x_cg_demo_api_
key=YOUR_KEY . 
o En Sheets: Instala "API Connector", crea request, exporta como CSV.  
o En Python (para reproducibilidad): Usa script con requests y pandas para 
fetch y save como CSV; reemplaza 'bitcoin' por 'ethereum' para ETH.  
o Verifica rango (e.g., últimos 365 días desde fecha actual).  
o Opcional: Convierte CSV a Parquet con df.to_parquet() . 
o Nota: Para OHLC específico, usa /coins/{id}/ohlc ; limita calls a 
<50/minuto.  
Fuente 3: Kaggle Datasets  
• Qué ofrece : Datasets independientes para BTC y ETH. Para BTC (dataset 
mczielinski/bitcoin -historical -data): 1 -minuto, desde ~2011 hasta 2021. Para 
ETH (dataset prasoonkottarathil/ethereum -historical -dataset): 1 -minuto, horaria 
y diaria, desde 2015 hasta 2020. Cubre OHLCV de exchanges selectos.  
• Condiciones/Licencia resumida : Mayoría bajo licencias abiertas como CC0 
(Public Domain) o CC BY (atribución requerida). Adecuadas para uso 
personal/educativo; verifica por dataset (e.g., BTC es CC0, ETH similar). Kaggle 
permite descargas gratuitas con cuenta.  
• Formato típico de columnas : CSV con: Timestamp (unix), Open, High, Low, 
Close, Volume_(BTC/ETH), Volume_(Currency), Weighted_Price.  
• Checklist de descarga reproducible : 
o Crea cuenta gratuita en Kaggle ( https://www.kaggle.com ). 

o Busca el dataset: "bitcoin historical data" para BTC o "ethereum 
historical dataset" para ETH.  
o Selecciona el dataset deseado (e.g., mczielinski para BTC, 
prasoonkottarathil para ETH).  
o Haz clic en "Download" (requiere login); obtén ZIP con CSVs.  
o Extrae y verifica rango de fechas (e.g., BTC 2011 -2021, ETH 2015 -2020).  
o Opcional: Convierte CSV a Parquet usando pandas en local.  
o Nota: Para reproducibilidad, anota el enlace del dataset y versión (Kaggle 
trackea cambios).  
 

