import warnings, yfinance as yf, pandas_ta as ta, requests, time, threading, os
from flask import Flask

warnings.filterwarnings("ignore", category=FutureWarning)

WEBHOOK = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"

def get_next_list():
    ciclo = int(time.time() / 3600) % 10 + 1 
    filename = f"list{ciclo}.txt"
    
    # Controllo rigoroso: se il file non esiste, il bot si blocca e segnala l'errore
    if not os.path.exists(filename):
        print(f"❌ ERRORE: Il file {filename} non esiste! Crea il file su GitHub.")
        return None, filename
        
    with open(filename, "r") as f:
        tickers = [line.strip() for line in f if line.strip()]
        return tickers, filename

def analizza(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False, timeout=8)
        if df.empty or len(df) < 50: return
        df['RSI'] = ta.rsi(df['Close'], length=60)
        df['EMA'] = ta.ema(df['RSI'], length=60)
        if df['RSI'].iloc[-1] < df['EMA'].iloc[-1] and df['RSI'].iloc[-1] < 40:
            requests.post(WEBHOOK, json={"content": f"🚨 Accumulo: {ticker} | RSI: {df['RSI'].iloc[-1]:.1f}"})
    except: pass

def run_bot():
    while True:
        tickers, nome_file = get_next_list()
        
        if tickers:
            print(f"🚀 Scansione di {len(tickers)} titoli dal file {nome_file}...")
            for ticker in tickers:
                analizza(ticker)
                time.sleep(1.0)
            print("✅ Ciclo completo.")
        else:
            print(f"⚠️ In attesa di trovare il file {nome_file}...")
            
        time.sleep(60) # Aspetta 1 minuto prima di riprovare se non trova il file

app = Flask(__name__)
@app.route('/')
def home(): return "Scanner Rotativo Rigoroso Online"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()

if __name__ == "__main__":
    run_bot()
