import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import threading
import os
from flask import Flask
from datetime import datetime

# --- CONFIGURAZIONE SERVER ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"Bot attivo. Orario attuale: {datetime.now().strftime('%H:%M:%S')}"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# --- WEBHOOKS ---
WEBHOOK_4H      = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
WEBHOOK_DAILY   = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
WEBHOOK_WEEKLY  = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"

timeframes = {
    "4h":     {"interval": "4h",  "period": "730d", "webhook": WEBHOOK_4H,   "tv_interval": "240"},
    "Daily":  {"interval": "1d",  "period": "5y",    "webhook": WEBHOOK_DAILY,  "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "10y",   "webhook": WEBHOOK_WEEKLY, "tv_interval": "W"}
}

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except: return []

def esegui_scansione():
    watchlist = carica_watchlist()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Inizio scansione di {len(watchlist)} titoli.")
    
    for ticker in watchlist:
        # Controllo orario operativo
        if datetime.now().hour >= 12: 
            print("Orario limite (12:00) raggiunto.")
            break
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Analizzando: {ticker}")
        
        for tf_name, tf_config in timeframes.items():
            try:
                df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                
                if df.empty or len(df) < 130: continue
                if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
                
                df['RSI_60'] = ta.rsi(df['Close'], length=60)
                df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                df = df.dropna()
                
                ultimo_rsi = float(df['RSI_60'].iloc[-1])
                ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: candele += 1
                        else: break
                    
                    if candele >= 15:
                        valuta = "€" if any(ext in ticker for ext in [".MI", ".PA", ".DE", ".AS", ".MC", ".L", ".SW", ".CO"]) else "$"
                        ticker_tv = ticker.split('.')[0]
                        link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                        
                        msg = {"content": f"🚨 **ZONA ACCUMULO: {ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Persistenza: {candele} candele. 🔗 [Grafico]({link})"}
                        requests.post(tf_config["webhook"], json=msg)
                
                time.sleep(18) # Calibrato per finire 240 titoli * 3 TF in ~4 ore
            except Exception as e:
                print(f"Errore su {ticker}: {e}")
                continue

# --- CICLO GIORNALIERO ---
while True:
    ora_attuale = datetime.now().hour
    if ora_attuale == 8: 
        esegui_scansione()
    
    time.sleep(300) # Dorme 5 minuti tra un controllo e l'altro
