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

# --- TIMEFRAMES CON PASSO PROMEMORIA PERSONALIZZATO ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H_TEST,     "tv_interval": "240", "reminder_step": 6},  # Promemoria ogni 6 candele (~24h di mercato)
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY_TEST,  "tv_interval": "D",   "reminder_step": 5},  # Promemoria ogni 5 candele (1 settimana)
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY_TEST, "tv_interval": "W",   "reminder_step": 4}   # Promemoria ogni 4 candele (~1 mese)
}

# 🧠 MEMORIA INTRA-CANDELA ed EVOLUZIONE GIORNALIERA
gia_inviati = {}
giorno_ultimo_controllo = None

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"⚠️ Errore nel caricamento della watchlist: {e}", flush=True)
        return []

def carica_incubatore():
    try:
        with open("incubatore.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return [] # Se il file non esiste ancora su GitHub, restituisce una lista vuota

def controlla_ticker_delistato(ticker):
    """Verifica se un titolo è realmente delistato/inesistente o fermo da oltre 30 giorni."""
    try:
        df_check = yf.download(ticker, period="max", interval="1d", progress=False, timeout=10)
        if df_check.empty:
            return True
        if isinstance(df_check.columns, pd.MultiIndex):
            df_check.columns = [col[0] for col in df_check.columns]
            
        ultima_candela = df_check.index[-1]
        data_candela = ultima_candela.date() if hasattr(ultima_candela, 'date') else pd.to_datetime(ultima_candela).date()
        giorni_di_silenzio = (datetime.now().date() - data_candela).days
        
        if giorni_di_silenzio > 30:
            return True
        return False
    except Exception:
        return True

def rimuovi_ticker_da_file(ticker_da_rimuovere):
    """Rimuove il ticker dalla sessione odierna di Render per evitare log ridondanti."""
    try:
        watchlist = carica_watchlist()
        if ticker_da_rimuovere in watchlist:
            watchlist.remove(ticker_da_rimuovere)
            with open("list1.txt", "w") as f:
                for t in watchlist:
                    f.write(f"{t}\n")
            print(f"🗑️ Ticker {ticker_da_rimuovere} rimosso temporaneamente dalla sessione locale.", flush=True)
    except Exception as e:
        print(f"⚠️ Errore durante la rimozione locale di {ticker_da_rimuovere}: {e}", flush=True)

def esegui_scansione_test():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{app.last_scan}] >>> 🧪 INIZIO CICLO TEST: Analisi di {len(watchlist)} titoli <<<", flush=True)
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 TEST ANALISI: {ticker}", flush=True)
        
        for tf_name, tf_config in timeframes.items():
            try:
                df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                
                # --- VERIFICA COERENZA DATI STORICI ---
                if df.empty or len(df) < 130: 
                    if tf_name == "Daily":
                        print(f"    ⚠️ Dati insufficienti su Daily per {ticker}. Verifica stato delistato...", flush=True)
                        
                        if controlla_ticker_delistato(ticker):
                            print(f"    🔴 {ticker} è inattivo/delistato. Segnalazione inviata.", flush=True)
                            
                            # Ti suggerisce esplicitamente di spostarlo nell'incubatore
                            msg = {
                                "content": f"🔴 **[WATCHLIST] TITOLO INATTIVO O DELISTATO:**\n"
                                           f"Il ticker **{ticker}** non ha dati o è fermo da oltre 30 giorni.\n"
                                           f"L'ho rimosso per oggi. **Taglialo da `list1.txt` e incollalo in `incubatore.txt` su GitHub!**"
                            }
                            requests.post(WEBHOOK_DAILY_TEST, json=msg)
                            rimuovi_ticker_da_file(ticker)
                            break 
                        else:
                            print(f"    ℹ️ {ticker} è attivo ma giovane (IPO). Rimane in list1.txt.", flush=True)
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
                
                # --- VERIFICA STRATEGIA ---
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: candele += 1
                        else: break
                    
                    SOGLIA_MINIMA = 15
                    if candele >= SOGLIA_MINIMA:
                        passo = tf_config["reminder_step"]
                        
                        if (candele - SOGLIA_MINIMA) % passo == 0:
                            chiave_segnale = (ticker, tf_name)
                            timestamp_candela_attuale = df.index[-1]
                            
                            if gia_inviati.get(chiave_segnale) != timestamp_candela_attuale:
                                ticker_tv = ticker.split('.')[0]
                                link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                                
                                prefisso = "🎯 **[TEST] NUOVO ACCUMULO**" if candele == SOGLIA_MINIMA else "🔄 **[TEST] PROMEMORIA ACCUMULO**"
                                msg = {"content": f"{prefisso}: **{ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Candele consecutive: {candele} 🔗 [Grafico]({link})"}
                                
                                requests.post(tf_config["webhook"], json=msg)
                                print(f"    🟢 ALERT SPEDITO ({tf_name}): {ticker} a quota {candele} candele.", flush=True)
                                gia_inviati[chiave_segnale] = timestamp_candela_attuale
                        else:
                            print(f"    🟡 {ticker} ({tf_name}) è a quota {candele} candele. Promemoria non dovuto.", flush=True)
                
                time.sleep(random.uniform(0.2, 0.4))
            except Exception as e:
                print(f"    --- Errore generico su {ticker} ({tf_name}): {e}", flush=True)
                continue
        time.sleep(random.uniform(1.0, 1.8))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> 🧪 CICLO TEST COMPLETATO <<<", flush=True)


def esegui_scansione_incubatore():
    """Controlla i titoli parcheggiati nell'incubatore per vedere se qualcuno si è risvegliato."""
    incubatore = carica_incubatore()
    if not incubatore:
        return
        
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] >>> 💤 CONTROLLO GIORNALIERO INCUBATORE: Analisi di {len(incubatore)} titoli in quarantena <<<", flush=True)
    
    for ticker in incubatore:
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False, timeout=10)
            
            if not df.empty and len(df) >= 130:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                
                ultima_candela = df.index[-1]
                data_candela = ultima_candela.date() if hasattr(ultima_candela, 'date') else pd.to_datetime(ultima_candela).date()
                giorni_di_silenzio = (datetime.now().date() - data_candela).days
                
                # Se ha abbastanza candele e ha scambiato negli ultimi 30 giorni, si è svegliato!
                if giorni_di_silenzio <= 30:
                    msg = {
                        "content": f"🎉 **[INCUBATORE] TITOLO RISVEGLIATO O PRONTO!**\n"
                                   f"Il ticker **{ticker}** ha accumulato lo storico necessario ({len(df)} candele) ed è tornato attivo.\n"
                                   f"**Ora puoi rimetterlo in `list1.txt` e rimuoverlo da `incubatore.txt` su GitHub!**"
                    }
                    requests.post(WEBHOOK_DAILY_TEST, json=msg)
                    print(f"    🎉 {ticker} si è risvegliato! Segnalato su Discord.", flush=True)
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            print(f"    --- Errore incubatore su {ticker}: {e}", flush=True)


def loop_scansione_background():
    global giorno_ultimo_controllo
    while True:
        # 1. Scansione ordinaria della watchlist attiva
        esegui_scansione_test()
        
        # 2. Controllo dell'incubatore (Una sola volta al giorno o ad ogni riavvio di Render)
        oggi = datetime.now().date()
        if giorno_ultimo_controllo != oggi:
            esegui_scansione_incubatore()
            giorno_ultimo_controllo = oggi
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Test in attesa 30 minuti...", flush=True)
        time.sleep(1800)

# Avvio del thread
threading.Thread(target=loop_scansione_background, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
