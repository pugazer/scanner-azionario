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

# 🧠 MEMORIA INTRA-CANDELA (Evita lo spam nei cicli da 30 minuti dello stesso timeframe)
gia_inviati = {}

def carica_watchlist():
    try:
        with open("list1.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"⚠️ Errore nel caricamento della watchlist: {e}", flush=True)
        return []

def controlla_ticker_delistato(ticker):
    """
    Verifica se un titolo è realmente delistato/inesistente (True)
    o se è solo giovane / ha una mancanza temporanea di dati (False).
    """
    try:
        # Scarichiamo la massima cronologia sul Daily per controllo macro
        df_check = yf.download(ticker, period="max", interval="1d", progress=False, timeout=10)
        
        if df_check.empty:
            return True # Nessun dato restituito da Yahoo -> Delistato o errore di digitazione
            
        if isinstance(df_check.columns, pd.MultiIndex):
            df_check.columns = [col[0] for col in df_check.columns]
            
        # Estraiamo l'ultima data disponibile sul mercato per questo ticker
        ultima_candela = df_check.index[-1]
        data_candela = ultima_candela.date() if hasattr(ultima_candela, 'date') else pd.to_datetime(ultima_candela).date()
        
        giorni_di_silenzio = (datetime.now().date() - data_candela).days
        
        # Se il titolo non scambia da più di 30 giorni, è morto o congelato
        if giorni_di_silenzio > 30:
            return True
            
        return False
    except Exception:
        # Se l'API fallisce bloccando l'analisi, prudenzialmente lo consideriamo non valido
        return True

def rimuovi_ticker_da_file(ticker_da_rimuovere):
    """Rimuove il ticker dal file locale su Render per silenziarlo fino al prossimo riavvio giornaliero."""
    try:
        watchlist = carica_watchlist()
        if ticker_da_rimuovere in watchlist:
            watchlist.remove(ticker_da_rimuovere)
            with open("list1.txt", "w") as f:
                for t in watchlist:
                    f.write(f"{t}\n")
            print(f"🗑️ Ticker {ticker_da_rimuovere} rimosso temporaneamente dal file di sessione locale.", flush=True)
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
                    # Se mancano dati sul Daily, verifichiamo se il titolo è delistato
                    if tf_name == "Daily":
                        print(f"    ⚠️ Dati storici insufficienti su Daily per {ticker}. Verifica stato delistato...", flush=True)
                        
                        if controlla_ticker_delistato(ticker):
                            print(f"    🔴 {ticker} è delistato o inattivo permanente. Avvio rimozione...", flush=True)
                            
                            # 1. Invia alert di servizio su Discord (canale Daily)
                            msg = {
                                "content": f"🔴 **[ALERT WATCHLIST] TITOLO DELISTATO O INATTIVO:**\n"
                                           f"Il ticker **{ticker}** non esiste più o non scambia da oltre 30 giorni.\n"
                                           f"L'ho rimosso temporaneamente per oggi. "
                                           f"**Ricordati di eliminarlo o sostituirlo nel tuo `list1.txt` su GitHub!**"
                            }
                            requests.post(WEBHOOK_DAILY_TEST, json=msg)
                            
                            # 2. Rimuove dal file locale su Render per non rielaborarlo ogni 30 min
                            rimuovi_ticker_da_file(ticker)
                            break # Interrompe l'analisi degli altri timeframe per questo ticker morto
                        else:
                            print(f"    ℹ️ {ticker} è attivo ma ha pochi dati (es. IPO recente). Rimane in lista.", flush=True)
                    
                    continue # Salta il timeframe corrente se non ha abbastanza dati
                    
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
                
                # --- VERIFICA DELLE CONDIZIONI DI STRATEGIA ---
                if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                    df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                    
                    # Conteggio candele consecutive a ritroso a partire dalla candela attuale
                    candele = 0
                    for i in range(len(df)-1, -1, -1):
                        if df['Sotto_Media'].iloc[i]: 
                            candele += 1
                        else: 
                            break
                    
                    SOGLIA_MINIMA = 15
                    
                    # Verifichiamo se abbiamo raggiunto o superato la soglia minima richiesta
                    if candele >= SOGLIA_MINIMA:
                        passo = tf_config["reminder_step"]
                        
                        # LOGICA MATEMATICA: Controlla se siamo al primo ingresso (es. 15) o a un passo del promemoria (es. 20, 25, 30)
                        if (candele - SOGLIA_MINIMA) % passo == 0:
                            
                            # FILTRO ANTI-SPAM INTRA-CANDELA: Evita i duplicati nelle scansioni da 30 min dello stesso giorno/periodo
                            chiave_segnale = (ticker, tf_name)
                            timestamp_candela_attuale = df.index[-1]
                            
                            if gia_inviati.get(chiave_segnale) != timestamp_candela_attuale:
                                ticker_tv = ticker.split('.')[0]
                                link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                                
                                # Personalizzazione del testo dell'alert
                                if candele == SOGLIA_MINIMA:
                                    prefisso = "🎯 **[TEST] NUOVO ACCUMULO**"
                                else:
                                    prefisso = "🔄 **[TEST] PROMEMORIA ACCUMULO**"
                                    
                                msg = {"content": f"{prefisso}: **{ticker}** | RSI: {ultimo_rsi:.1f} | TF: {tf_name} | Candele consecutive: {candele} 🔗 [Grafico]({link})"}
                                
                                requests.post(tf_config["webhook"], json=msg)
                                print(f"    🟢 ALERT SPEDITO ({tf_name}): {ticker} a quota {candele} candele.", flush=True)
                                
                                # Memorizza l'avvenuto invio per la candela corrente
                                gia_inviati[chiave_segnale] = timestamp_candela_attuale
                        else:
                            print(f"    🟡 {ticker} ({tf_name}) è a quota {candele} candele. Promemoria non ancora dovuto (passo ogni {passo}).", flush=True)
                
                time.sleep(random.uniform(0.2, 0.4))
            except Exception as e:
                print(f"    --- Errore generico su {ticker} ({tf_name}): {e}", flush=True)
                continue
        
        time.sleep(random.uniform(1.0, 1.8))
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] >>> 🧪 CICLO TEST COMPLETATO <<<", flush=True)

def loop_scansione_background():
    while True:
        esegui_scansione_test()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Test in attesa 30 minuti...", flush=True)
        time.sleep(1800)

# Avvio del thread in background per lo scanner di test
threading.Thread(target=loop_scansione_background, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
