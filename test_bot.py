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
WEBHOOK_4H_TEST      = "https://discord.com/api/webhooks/1516694458484261035/e-f8YSlg8G6PkKFGGOUswB_HZcQtW7HIdnRBeMoE4QfGQ-yFIvT2ihj8AqFvnadDiml-"
WEBHOOK_DAILY_TEST   = "https://discord.com/api/webhooks/1516694554433159228/11rWbzbOFlBDRU2PYnS2O4nuE498RYK4Bpb7v7AD1CdTrqNVufsVR_TzeI9-7b1Rd4yr"
WEBHOOK_WEEKLY_TEST  = "https://discord.com/api/webhooks/1516694640474980485/81JQjiXRSOEKSmUYqsbRvX5S6_y9MTcLbesRk6DuBkM7ZmCQMAd35TL1tnhrK_o-uCWv"

# --- TIME FRAMES DI TEST CON PASSO PROMEMORIA DIZIONARIO ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H_TEST,     "tv_interval": "240", "reminder_step": 6},  # Promemoria ogni 6 candele (~24h di mercato)
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY_TEST,  "tv_interval": "D",   "reminder_step": 5},  # Promemoria ogni 5 candele (1 settimana)
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY_TEST, "tv_interval": "W",   "reminder_step": 4}   # Promemoria ogni 4 candele (~1 mese)
}

# 🧠 MEMORIA INTRA-CANDELA (Evita lo spam nei cicli da 30 minuti dello stesso giorno/candela)
gia_inviati = {}

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
                
                # --- CALCOLO INDICATORI ---
                df['RSI_60'] = ta.rsi(df['Close'], length=60)
                df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                df = df.dropna()
                
                if df.empty: 
                    continue
                
                ultimo_rsi = float(df['RSI_60'].iloc[-1])
                ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                
                # Condizione di base per essere sotto la media e sotto i 40 di rsi
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    
                    # Conteggio candele consecutive per la candela ATTUALE
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: 
                            candele += 1
                        else: 
                            break
                    
                    SOGLIA_MINIMA = 15
                    
                    # 🎯 VERIFICA SE ABBIAMO RAGGIUNTO LA SOGLIA
                    if candele >= SOGLIA_MINIMA:
                        passo = tf_config["reminder_step"]
                        
                        # LOGICA MATEMATICA: Calcola se siamo al primo ingresso (es. 15) o a un traguardo successivo (es. 20, 25, 30)
                        if (candele - SOGLIA_MINIMA) % passo == 0:
                            
                            # 🛡️ FILTRO ANTI-SPAM: Non inviare se abbiamo già inviato un messaggio per QUESTA esatta candela
                            chiave_segnale = (ticker, tf_name)
                            timestamp_candela_attuale = df.index[-1]
                            
                            if gia_inviati.get(chiave_segnale) != timestamp_candela_attuale:
                                ticker_tv = ticker.split('.')[0]
                                link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                                
                                # Personalizza il testo in base al tipo di notifica
                                if candele == SOGLIA_MINIMA:
                                    prefisso = "🎯 **[TEST] NUOVO ACCUMULO**"
                                else:
                                    prefisso = "🔄 **[TEST] PROMEMORIA ACCUMULO**"
                                    
                                msg = {"content": f"{prefisso}: **{ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Candele consecutive: {candele} 🔗 [Grafico]({link})"}
                                
                                requests.post(tf_config["webhook"], json=msg)
                                print(f"    🟢 ALERT SPEDITO ({tf_name}): {ticker} a quota {candele} candele.", flush=True)
                                
                                # Salva in memoria per bloccare i restanti cicli da 30 minuti di questo intervallo
                                gia_inviati[chiave_segnale] = timestamp_candela_attuale
                        else:
                            print(f"    🟡 {ticker} ({tf_name}) è a quota {candele} candele. Promemoria non ancora dovuto (passo ogni {passo}).", flush=True)
                
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
