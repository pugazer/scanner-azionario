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
    return f"Bot Operativo. Ultimo avvio scansione: {getattr(app, 'last_scan', 'Mai')}"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# --- WEBHOOKS ---
WEBHOOK_4H      = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
WEBHOOK_DAILY   = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
WEBHOOK_WEEKLY  = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"

# --- PERIODI OTTIMIZZATI ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "100d",  "webhook": WEBHOOK_4H,   "tv_interval": "240"},
    "Daily":  {"interval": "1d",  "period": "300d",  "webhook": WEBHOOK_DAILY,  "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "150wk", "webhook": WEBHOOK_WEEKLY, "tv_interval": "W"}
}

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except: return []

def esegui_scansione():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"[{app.last_scan}] --- INIZIO CICLO: Analisi di {len(watchlist)} titoli ---")
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] In analisi: {ticker}...")
        
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
                        print(f"   >> SEGNALE TROVATO per {ticker} su {tf_name}!")
                
                time.sleep(5) 
            except Exception as e:
                print(f"   >> Errore su {ticker} [{tf_name}]: {e}")
                continue
        
        time.sleep(15) 
    print(f"[{datetime.now().strftime('%H:%M:%S')}] --- CICLO TERMINATO. Attesa 30 minuti ---")

# --- CICLO INFINITO ---
while True:
    esegui_scansione()
    time.sleep(1800)
