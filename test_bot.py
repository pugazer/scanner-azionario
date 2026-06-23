import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import threading
import os
import base64
from flask import Flask
from datetime import datetime

# --- CONFIGURAZIONE SERVER ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"🧪 BOT AUTOMATICO OPERATIVO. Ultima scansione: {getattr(app, 'last_scan', 'Mai')}"

# --- WEBHOOKS (PROTETTI DA VARIABILI D'AMBIENTE) ---
WEBHOOK_4H_TEST      = os.environ.get("WEBHOOK_4H_TEST")
WEBHOOK_DAILY_TEST   = os.environ.get("WEBHOOK_DAILY_TEST")
WEBHOOK_WEEKLY_TEST  = os.environ.get("WEBHOOK_WEEKLY_TEST")

# --- TIMEFRAMES ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H_TEST,     "tv_interval": "240", "reminder_step": 6},
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY_TEST,  "tv_interval": "D",   "reminder_step": 5},
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY_TEST, "tv_interval": "W",   "reminder_step": 4}
}

# --- VARIABILI GITHUB ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO  = os.environ.get("GITHUB_REPO")

gia_inviati = {}
giorno_ultimo_controllo = None

# --- FUNZIONI DI GESTIONE FILE (SORTED & UNIQUE) ---
def carica_watchlist():
    try:
        if not os.path.exists("list1.txt"): return []
        with open("list1.txt", "r") as f:
            raw_list = [line.strip() for line in f if line.strip()]
        
        lista_pulita = sorted(list(set(raw_list)))
        
        if lista_pulita != raw_list:
            with open("list1.txt", "w") as f:
                f.write("\n".join(lista_pulita) + "\n")
            print(f"🧹 Watchlist riordinata e duplicati rimossi.", flush=True)
            
        return lista_pulita
    except Exception as e:
        print(f"⚠️ Errore caricamento watchlist: {e}", flush=True)
        return []

def carica_incubatore():
    try:
        if not os.path.exists("incubatore.txt"): return []
        with open("incubatore.txt", "r") as f:
            raw_list = [line.strip() for line in f if line.strip()]
        return sorted(list(set(raw_list)))
    except:
        return []

# --- COMUNICAZIONE GITHUB ---
def scrivi_file_su_github(path_file, linee, messaggio_commit):
    if not GITHUB_TOKEN or not GITHUB_REPO: return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_file}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    sha = ""
    r = requests.get(url, headers=headers)
    if r.status_code == 200: sha = r.json().get("sha", "")
        
    testo_base64 = base64.b64encode(("\n".join(linee) + "\n").encode('utf-8')).decode('utf-8')
    payload = {"message": messaggio_commit, "content": testo_base64}
    if sha: payload["sha"] = sha
        
    r_put = requests.put(url, headers=headers, json=payload)
    return r_put.status_code in [200, 201]

def sposta_ticker_automatico(ticker, direzione):
    watchlist = carica_watchlist()
    incubatore = carica_incubatore()
    
    if direzione == "da_watchlist_a_incubatore":
        if ticker in watchlist: watchlist.remove(ticker)
        if ticker not in incubatore: incubatore.append(ticker)
        msg_c1, msg_c2 = f"Bot: Rimosso {ticker} (Inattivo)", f"Bot: Aggiunto {ticker} in Incubatore"
        
    elif direzione == "da_incubatore_a_watchlist":
        if ticker in incubatore: incubatore.remove(ticker)
        if ticker not in watchlist: watchlist.append(ticker)
        msg_c1, msg_c2 = f"Bot: Rimosso {ticker} da Incubatore (Risvegliato)", f"Bot: Ripristinato {ticker} in Watchlist"
    else: return

    watchlist = sorted(list(set(watchlist)))
    incubatore = sorted(list(set(incubatore)))

    with open("list1.txt", "w") as f: f.write("\n".join(watchlist) + "\n")
    with open("incubatore.txt", "w") as f: f.write("\n".join(incubatore) + "\n")

    scrivi_file_su_github("list1.txt", watchlist, msg_c1)
    scrivi_file_su_github("incubatore.txt", incubatore, msg_c2)
    print(f"🔄 Spostamento completato per {ticker}.", flush=True)

# --- ANALISI ---
def controlla_ticker_delistato(ticker):
    try:
        df_check = yf.download(ticker, period="max", interval="1d", progress=False, timeout=10)
        if df_check.empty: return True
        if isinstance(df_check.columns, pd.MultiIndex): df_check.columns = [col[0] for col in df_check.columns]
        ultima = df_check.index[-1]
        data_c = ultima.date() if hasattr(ultima, 'date') else pd.to_datetime(ultima).date()
        return (datetime.now().date() - data_c).days > 30
    except: return True

def esegui_scansione_test():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{app.last_scan}] >>> 🧪 INIZIO SCAN {len(watchlist)} TITOLI <<<", flush=True)
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 TEST ANALISI: {ticker}", flush=True)
        try:
            for tf_name, tf_config in timeframes.items():
                try:
                    df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                    if df.empty or len(df) < 130: 
                        if tf_name == "Daily":
                            if controlla_ticker_delistato(ticker):
                                sposta_ticker_automatico(ticker, "da_watchlist_a_incubatore")
                                requests.post(WEBHOOK_DAILY_TEST, json={"content": f"🤖 **[AUTO-SPOSTAMENTO]** Ticker **{ticker}** inattivo. Spostato in incubatore."})
                                break 
                        continue 
                        
                    if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
                    df['RSI_60'] = ta.rsi(df['Close'], length=60)
                    df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                    df = df.dropna()
                    if df.empty: continue
                    
                    if df['RSI_60'].iloc[-1] < df['EMA_RSI_60'].iloc[-1] and df['RSI_60'].iloc[-1] < 40:
                        df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                        candele = 0
                        for i in range(len(df)-1, -1, -1):
                            if df['Sotto_Media'].iloc[i]: candele += 1
                            else: break
                        
                        if candele >= 15 and (candele - 15) % tf_config["reminder_step"] == 0:
                            chiave = (ticker, tf_name)
                            if gia_inviati.get(chiave) != df.index[-1]:
                                msg = {"content": f"{'🎯 **[TEST] NUOVO ACCUMULO**' if candele == 15 else '🔄 **[TEST] PROMEMORIA ACCUMULO**'}: **{ticker}** | RSI: {df['RSI_60'].iloc[-1]:.1f} | TF: {tf_name} | Candele: {candele} 🔗 [Grafico](https://it.tradingview.com/chart/?symbol={ticker.split('.')[0]}&interval={tf_config['tv_interval']})"}
                                requests.post(tf_config["webhook"], json=msg)
                                gia_inviati[chiave] = df.index[-1]
                    
                    time.sleep(1.0)
                except Exception as e:
                    print(f"⚠️ Errore su {ticker} ({tf_name}): {e}", flush=True)
                    continue
        except Exception as e:
            print(f"‼️ ERRORE CRITICO NEL CICLO PRINCIPALE su {ticker}: {e}", flush=True)
            continue
            
    print(f"✅ >>> SCAN TERMINATA CORRETTAMENTE <<<", flush=True)

def esegui_scansione_incubatore():
    incubatore = carica_incubatore()
    for ticker in incubatore:
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False, timeout=10)
            if not df.empty and len(df) >= 130:
                ultima = df.index[-1].date()
                if (datetime.now().date() - ultima).days <= 30:
                    sposta_ticker_automatico(ticker, "da_incubatore_a_watchlist")
                    requests.post(WEBHOOK_DAILY_TEST, json={"content": f"🎉 **[AUTOMAZIONE] Ticker {ticker} RISVEGLIATO!** Reinserito in list1.txt."})
            time.sleep(1.0)
        except: continue

    def loop_scansione_background():
        global giorno_ultimo_controllo
        while True:
            esegui_scansione_test()
            if giorno_ultimo_controllo != datetime.now().date():
                esegui_scansione_incubatore()
                giorno_ultimo_controllo = datetime.now().date()
            time.sleep(1800)

    threading.Thread(target=loop_scansione_background, daemon=True).start()

    if __name__ == "__main__":
        app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
