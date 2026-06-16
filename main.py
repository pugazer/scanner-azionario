import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import os
import threading
from flask import Flask

# --- SERVER FLASK PER RENDER ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Il bot è online e sta lavorando!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURAZIONI ---
WEBHOOK_4H = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
WEBHOOK_DAILY = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
WEBHOOK_WEEKLY = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"

timeframes = {
    "4h": {"interval": "4h", "period": "730d", "webhook": WEBHOOK_4H, "tv_interval": "240"},
    "Daily": {"interval": "1d", "period": "5y", "webhook": WEBHOOK_DAILY, "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "10y", "webhook": WEBHOOK_WEEKLY, "tv_interval": "W"}
}

def analizza_ticker(ticker, tf_name, tf_config, webhook):
    try:
        df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=15)
        
        # Filtro dati minimi
        if df.empty or len(df) < 100: 
            return
            
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        
        df['RSI_60'] = ta.rsi(df['Close'], length=60)
        df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
        df = df.dropna()
        
        if df.empty: return
        
        ultimo_rsi = float(df['RSI_60'].iloc[-1])
        ultima_ema = float(df['EMA_RSI_60'].iloc[-1])
        
        if ultimo_rsi < ultima_ema and ultimo_rsi < 40:
            df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
            candele = 0
            for i in range(len(df)-1, -1, -1):
                if df['Sotto_Media'].iloc[i]: candele += 1
                else: break
            
            if candele >= 15:
                ticker_tv = ticker.split('.')[0]
                link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                msg = {
                    "content": f"🚨 **ZONA ACCUMULO (RSI < 40)** 🚨\n📌 **Azione:** `{ticker}`\n⏱️ **TF:** `{tf_name}`\n📉 **RSI:** `{ultimo_rsi:.1f}`\n⏳ **Persistenza:** `{candele}` candele sotto media.\n🔗 [Apri Grafico]({link})"
                }
                requests.post(webhook, json=msg)
                time.sleep(1) 
    except Exception as e:
        print(f"Errore su {ticker}: {e}")

# --- CICLO PRINCIPALE ---
while True:
    ora_corrente = int(time.time() / 3600) % 10 + 1
    nome_file = f"list{ora_corrente}.txt"
    
    if os.path.exists(nome_file):
        with open(nome_file, "r") as f:
            tickers = [line.strip() for line in f if line.strip()]
        
        print(f"[{time.strftime('%H:%M:%S')}] Inizio scansione {nome_file} ({len(tickers)} titoli)")
        
        for ticker in tickers:
            print(f"-> Analisi: {ticker}")
            for tf_name, tf_config in timeframes.items():
                analizza_ticker(ticker, tf_name, tf_config, tf_config["webhook"])
            time.sleep(0.5) 
            
    else:
        print(f"File {nome_file} non trovato.")
    
    time.sleep(60)
