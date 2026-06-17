import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import threading
import os
import random
from flask import Flask
from datetime import datetime

# --- CONFIGURAZIONE SERVER DI TEST ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"🧪 BOT DI TEST OPERATIVO. Ultima scansione: {getattr(app, 'last_scan', 'Mai')}"

# --- WEBHOOKS ESCLUSIVI PER L'AREA TEST ---
# (Incolla qui i link dei 3 nuovi canali che crei nella categoria TEST)
WEBHOOK_4H_TEST      = "https://discord.com/api/webhooks/1516694458484261035/e-f8YSlg8G6PkKFGGOUswB_HZcQtW7HIdnRBeMoE4QfGQ-yFIvT2ihj8AqFvnadDiml-"
WEBHOOK_DAILY_TEST   = "https://discord.com/api/webhooks/1516694554433159228/11rWbzbOFlBDRU2PYnS2O4nuE498RYK4Bpb7v7AD1CdTrqNVufsVR_TzeI9-7b1Rd4yr"
WEBHOOK_WEEKLY_TEST  = "https://discord.com/api/webhooks/1516694640474980485/81JQjiXRSOEKSmUYqsbRvX5S6_y9MTcLbesRk6DuBkM7ZmCQMAd35TL1tnhrK_o-uCWv"

# --- TIME FRAMES DI TEST ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H_TEST,     "tv_interval": "240"},
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY_TEST,  "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY_TEST, "tv_interval": "W"}
}

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except: 
        return []

def esegui_scansione_test():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{app.last_scan}] >>> 🧪 INIZIO CICLO TEST: Analisi di {len(watchlist)} titoli <<<", flush=True)
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 TEST ANALISI: {ticker}", flush=True)
        
        for tf_name, tf_config in timeframes.items():
            try:
                df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                
                if df.empty or len(df) < 130: 
                    continue
                    
                if isinstance(df.columns, pd.MultiIndex): 
                    df.columns = [col[0] for col in df.columns]
                
                # =========================================================================
                # ⚙️ QUI PUOI MODIFICARE I PARAMETRI PER FARE I TUOI ESPERIMENTI!
                # =========================================================================
                df['RSI_60'] = ta.rsi(df['Close'], length=60)
                df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                df = df.dropna()
                
                if df.empty: 
                    continue
                
                ultimo_rsi = float(df['RSI_60'].iloc[-1])
                ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                
                # Puoi provare a cambiare la soglia (es. < 45) o la media per vedere cosa succede
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: 
                            candele += 1
                        else: 
                            break
                    
                    # Puoi provare a cambiare il numero di candele consecutive (es. >= 10)
                    if candele >= 15:
                        ticker_tv = ticker.split('.')[0]
                        link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                        msg = {"content": f"🧪 **[TEST] ACCUMULO: {ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Candele: {candele} 🔗 [Grafico]({link})"}
                        requests.post(tf_config["webhook"], json=msg)
                        print(f"    🟢 !!! SEGNALE TEST TROVATO: {ticker} su {tf_name} !!!", flush=True)
                
                time.sleep(random.uniform(0.2, 0.4))
            except Exception as e:
                print(f"    --- Errore test su {ticker} ({tf_name}): {e}", flush=True)
                continue
        
        time.sleep(random.uniform(1.0, 1.8))
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> 🧪 CICLO TEST COMPLETATO <<<", flush=True)

def loop_scansione_background():
    while True:
        esegui_scansione_test()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Test in attesa 30 minuti...", flush=True)
        time.sleep(1800)

# Avvio dello scanner di test in background
threading.Thread(target=loop_scansione_background, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
