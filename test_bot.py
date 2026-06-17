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
import base64
from flask import Flask
from datetime import datetime

# --- CONFIGURAZIONE SERVER DI TEST ---
app = Flask(__name__)
@app.route('/')
def home():
    return f"🧪 BOT AUTOMATICO OPERATIVO. Ultima scansione: {getattr(app, 'last_scan', 'Mai')}"

# --- WEBHOOKS ESCLUSIVI PER L'AREA TEST ---
WEBHOOK_4H_TEST      = "https://discord.com/api/webhooks/1516694458484261035/e-f8YSlg8G6PkKFGGOUswB_HZcQtW7HIdnRBeMoE4QfGQ-yFIvT2ihj8AqFvnadDiml-"
WEBHOOK_DAILY_TEST   = "https://discord.com/api/webhooks/1516694554433159228/11rWbzbOFlBDRU2PYnS2O4nuE498RYK4Bpb7v7AD1CdTrqNVufsVR_TzeI9-7b1Rd4yr"
WEBHOOK_WEEKLY_TEST  = "https://discord.com/api/webhooks/1516694640474980485/81JQjiXRSOEKSmUYqsbRvX5S6_y9MTcLbesRk6DuBkM7ZmCQMAd35TL1tnhrK_o-uCWv"

# --- TIMEFRAMES CON PASSO PROMEMORIA PERSONALIZZATO ---
timeframes = {
    "4h":     {"interval": "4h",  "period": "2y", "webhook": WEBHOOK_4H_TEST,     "tv_interval": "240", "reminder_step": 6},
    "Daily":  {"interval": "1d",  "period": "2y", "webhook": WEBHOOK_DAILY_TEST,  "tv_interval": "D",   "reminder_step": 5},
    "Weekly": {"interval": "1wk", "period": "5y", "webhook": WEBHOOK_WEEKLY_TEST, "tv_interval": "W",   "reminder_step": 4}
}

# --- CREDENZIALI GITHUB PER SCRITTURA AUTOMATICA ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO  = os.environ.get("GITHUB_REPO")

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
    if not os.path.exists("incubatore.txt"):
        with open("incubatore.txt", "w") as f:
            f.write("")
        return []
    try:
        with open("incubatore.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def scrivi_file_su_github(path_file, linee, messaggio_commit):
    """Invia gli aggiornamenti direttamente alla repository GitHub via API."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print(f"⚠️ Cloud Sync disattivato: Manca GITHUB_TOKEN o GITHUB_REPO nelle variabili di Render.", flush=True)
        return False
        
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_file}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # 1. Recupera lo SHA del file esistente (richiesto da GitHub per sovrascrittura)
    sha = ""
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha", "")
        
    # 2. Prepara il payload in Base64
    testo_completo = "\n".join(linee) + "\n" if linee else ""
    testo_base64 = base64.b64encode(testo_completo.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": messaggio_commit,
        "content": testo_base64
    }
    if sha:
        payload["sha"] = sha
        
    # 3. Invia la modifica pushando su GitHub
    r_put = requests.put(url, headers=headers, json=payload)
    return r_put.status_code in [200, 201]

def sposta_ticker_automatico(ticker, direzione):
    """
    Gestisce lo spostamento di un titolo aggiornando sia i file locali di sessione
    sia la repository remota su GitHub.
    Direzioni ammesse: 'da_watchlist_a_incubatore' | 'da_incubatore_a_watchlist'
    """
    watchlist = carica_watchlist()
    incubatore = carica_incubatore()
    
    if direzione == "da_watchlist_a_incubatore":
        if ticker in watchlist: watchlist.remove(ticker)
        if ticker not in incubatore: incubatore.append(ticker)
        msg_commit_1 = f"Bot: Rimosso {ticker} da Watchlist (Inattivo)"
        msg_commit_2 = f"Bot: Spostato {ticker} in Incubatore"
        
    elif direzione == "da_incubatore_a_watchlist":
        if ticker in incubatore: incubatore.remove(ticker)
        if ticker not in watchlist: watchlist.append(ticker)
        msg_commit_1 = f"Bot: Rimosso {ticker} da Incubatore (Risvegliato)"
        msg_commit_2 = f"Bot: Ripristinato {ticker} in Watchlist"
    else:
        return

    # Aggiornamento Locale (immediato per il ciclo corrente)
    try:
        with open("list1.txt", "w") as f: f.write("\n".join(watchlist) + ("\n" if watchlist else ""))
        with open("incubatore.txt", "w") as f: f.write("\n".join(incubatore) + ("\n" if incubatore else ""))
        print(f"🔄 Spostamento locale completato per {ticker}.", flush=True)
    except Exception as e:
        print(f"⚠️ Errore nel salvare i file locali durante lo switch: {e}", flush=True)

    # Sincronizzazione permanente su GitHub
    ok1 = scrivi_file_su_github("list1.txt", watchlist, msg_commit_1)
    ok2 = scrivi_file_su_github("incubatore.txt", incubatore, msg_commit_2)
    
    if ok1 and ok2:
        print(f"🚀 Sincronizzazione GitHub riuscita con successo per {ticker}.", flush=True)
    else:
        print(f"❌ Errore durante la sincronizzazione cloud su GitHub.", flush=True)

def controlla_ticker_delistato(ticker):
    try:
        df_check = yf.download(ticker, period="max", interval="1d", progress=False, timeout=10)
        if df_check.empty: return True
        if isinstance(df_check.columns, pd.MultiIndex): df_check.columns = [col[0] for col in df_check.columns]
            
        ultima_candela = df_check.index[-1]
        data_candela = ultima_candela.date() if hasattr(ultima_candela, 'date') else pd.to_datetime(ultima_candela).date()
        if (datetime.now().date() - data_candela).days > 30: return True
        return False
    except Exception:
        return True

def esegui_scansione_test():
    watchlist = carica_watchlist()
    app.last_scan = datetime.now().strftime('%H:%M:%S')
    print(f"\n[{app.last_scan}] >>> 🧪 INIZIO CICLO TEST: Analisi di {len(watchlist)} titoli <<<", flush=True)
    
    for ticker in watchlist:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧪 TEST ANALISI: {ticker}", flush=True)
        
        for tf_name, tf_config in timeframes.items():
            try:
                df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False, timeout=10)
                
                # --- VERIFICA STRUTTURA DATI ---
                if df.empty or len(df) < 130: 
                    if tf_name == "Daily":
                        print(f"    ⚠️ Dati storici insufficienti su Daily per {ticker}. Verifica stato delistato...", flush=True)
                        
                        if controlla_ticker_delistato(ticker):
                            print(f"    🔴 {ticker} è inattivo/delistato. Avvio SPOSTAMENTO AUTOMATICO...", flush=True)
                            
                            # Esegue lo switch dei file e lo scrive su GitHub
                            sposta_ticker_automatico(ticker, "da_watchlist_a_incubatore")
                            
                            msg = {
                                "content": f"⚙️ **[AUTOMAZIONE] TITOLO SPOSTATO IN INCONBATORIO:**\n"
                                           f"Il ticker **{ticker}** è inattivo o delistato. È stato tolto automaticamente da `list1.txt` "
                                           f"e parcheggiato in `incubatore.txt` sia su Render che su GitHub. Tu non devi fare nulla! 🤖"
                            }
                            requests.post(WEBHOOK_DAILY_TEST, json=msg)
                            break 
                        else:
                            print(f"    ℹ️ {ticker} è attivo ma giovane (IPO). Rimane in list1.txt.", flush=True)
                    continue 
                    
                if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
                
                # --- CALCOLO INDICATORI ---
                df['RSI_60'] = ta.rsi(df['Close'], length=60)
                df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                df = df.dropna()
                if df.empty: continue
                
                ultimo_rsi = float(df['RSI_60'].iloc[-1])
                ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                
                # --- STRATEGIA ACCUMULO ---
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
                                gia_inviati[chiave_segnale] = timestamp_candela_attuale
                
                time.sleep(random.uniform(0.2, 0.4))
            except Exception as e:
                print(f"    --- Errore generico su {ticker} ({tf_name}): {e}", flush=True)
                continue
        time.sleep(random.uniform(1.0, 1.8))
    print(f">>> 🧪 CICLO TEST COMPLETATO <<<", flush=True)

def esegui_scansione_incubatore():
    """Controlla l'incubatore e riprende automaticamente i titoli pronti."""
    incubatore = carica_incubatore()
    if not incubatore: return
        
    print(f"\n >>> 💤 CONTROLLO GIORNALIERO INCUBATORE: Analisi di {len(incubatore)} titoli <<<", flush=True)
    
    for ticker in incubatore:
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False, timeout=10)
            if not df.empty and len(df) >= 130:
                if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
                
                ultima_candela = df.index[-1]
                data_candela = ultima_candela.date() if hasattr(ultima_candela, 'date') else pd.to_datetime(ultima_candela).date()
                
                # Se è tornato attivo negli ultimi 30 giorni ed ha lo storico pronto, lo risveglia da solo!
                if (datetime.now().date() - data_candela).days <= 30:
                    print(f"    🎉 {ticker} si è svegliato! Ripristino automatico...", flush=True)
                    
                    sposta_ticker_automatico(ticker, "da_incubatore_a_watchlist")
                    
                    msg = {
                        "content": f"🎉 **[AUTOMAZIONE] TITOLO RISVEGLIATO E RIPRISTINATO!**\n"
                                   f"Il ticker **{ticker}** ha finalmente i dati pronti ({len(df)} candele) ed è tornato a scambiare.\n"
                                   f"Il bot l'ha **reinserito automaticamente** in `list1.txt` e rimosso dall'incubatore su GitHub! 🤖"
                    }
                    requests.post(WEBHOOK_DAILY_TEST, json=msg)
            time.sleep(random.uniform(0.5, 1.0))
        except Exception as e:
            print(f"    --- Errore incubatore su {ticker}: {e}", flush=True)

def loop_scansione_background():
    global giorno_ultimo_controllo
    while True:
        esegui_scansione_test()
        
        # Controllo giornaliero dell'incubatore
        oggi = datetime.now().date()
        if giorno_ultimo_controllo != oggi:
            esegui_scansione_incubatore()
            giorno_ultimo_controllo = oggi
            
        print(f"Test in attesa 30 minuti...", flush=True)
        time.sleep(1800)

threading.Thread(target=loop_scansione_background, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
