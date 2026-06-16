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
    return f"Bot Operativo. Ultima scansione: {getattr(app, 'last_scan', 'Mai')}"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Avvia il server web in un thread separato per Render
threading.Thread(target=run_web_server, daemon=True).start()

# --- WEBHOOKS ---
WEBHOOK_4H      = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
WEBHOOK_DAILY   = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
WEBHOOK_WEEKLY  = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"

# --- TIME FRAMES CORRETTI CON PERIODI NATIVI YAHOO ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H,   "tv_interval": "240"},
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY,  "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY, "tv_interval": "W"}
}

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except: 
        return []

def esegui_scansione():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{app.last_scan}] >>> INIZIO NUOVO CICLO: Analisi di {len(watchlist)} titoli <<<", flush=True)
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ANALIZZANDO: {ticker}", flush=True)
        
        for tf_name, tf_config in timeframes.items():
            try:
                # Download con timeout di sicurezza
                df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                
                if df.empty or len(df) < 130: 
                    continue
                    
                # Gestione MultiIndex colonne (nuove versioni yfinance)
                if isinstance(df.columns, pd.MultiIndex): 
                    df.columns = [col[0] for col in df.columns]
                
                # Calcolo Indicatori
                df['RSI_60'] = ta.rsi(df['Close'], length=60)
                df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                df = df.dropna()
                
                # Evita crash se i dati puliti sono vuoti
                if df.empty: 
                    continue
                
                ultimo_rsi = float(df['RSI_60'].iloc[-1])
                ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                
                # Verifica Condizione Strategia
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: 
                            candele += 1
                        else: 
                            break
                    
                    if candele >= 15:
                        ticker_tv = ticker.split('.')[0]
                        link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                        msg = {"content": f"🚨 **ZONA ACCUMULO: {ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Candele Sotto Media: {candele} 🔗 [Grafico]({link})"}
                        requests.post(tf_config["webhook"], json=msg)
                        print(f"    !!! SEGNALE TROVATO: {ticker} su {tf_name} !!!", flush=True)
                
                time.sleep(1) # Micro-pausa tra i timeframe dello stesso titolo
            except Exception as e:
                print(f"    --- Errore su {ticker} ({tf_name}): {e}", flush=True)
                continue
        
        time.sleep(4) # Pausa bilanciata tra i vari ticker (Log dinamico assicurato)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> CICLO COMPLETATO SU TUTTA LA LISTA <<<", flush=True)

# --- LOOP INFINITO DI ESECUZIONE ---
while True:
    esegui_scansione()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] In attesa 30 minuti prima della prossima scansione...", flush=True)
    time.sleep(1800)
