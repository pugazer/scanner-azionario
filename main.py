import warnings, yfinance as yf, pandas as pd, pandas_ta as ta, requests, time, threading, os
from flask import Flask
from datetime import datetime

warnings.filterwarnings("ignore", category=FutureWarning)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot attivo"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    # Liste aggiornate e ripulite dai ticker più problematici
    italia = ["A2A.MI", "AMP.MI", "AZM.MI", "BAMI.MI", "BPER.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "RACE.MI", "INW.MI", "ISP.MI", "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PST.MI", "PRY.MI", "SRG.MI", "STLAM.MI", "STMMI.MI", "TEN.MI", "TRN.MI", "UCG.MI", "UNI.MI"]
    europa = ["ADS.DE", "AD.AS", "AI.PA", "AIR.PA", "ALV.DE", "ASML.AS", "BAS.DE", "BAYN.DE", "BBVA.MC", "SAN.MC", "BMW.DE", "BNP.PA", "DTE.DE", "ITX.MC", "INGA.AS", "MBG.DE", "MC.PA", "OR.PA", "SAP.DE", "SIE.DE", "VOW3.DE", "DHL.DE"]
    usa = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ADBE", "AMD", "COST", "AVGO", "CSCO", "ACN", "AMGN", "ADI", "AON", "AMAT", "BAC", "BLK", "BX", "BA", "BSX", "CAT", "CBRE", "CCI", "CME", "KO", "CL", "CMCSA", "COP", "CVS", "DHR", "DE", "DOW", "ECL", "EA", "EMR", "EOG", "XOM", "FDX", "GE", "GD", "GS", "HD", "HON", "IBM", "INTC", "INTU", "JNJ", "JPM", "LLY", "LIN", "LMT", "LOW", "MAR", "MCD", "MDLZ", "MS", "NFLX", "NEE", "NKE", "ORCL", "PEP", "PFE", "PG", "PGR", "QCOM", "RTX", "CRM", "SLB", "SBUX", "SYK", "TGT", "TMO", "TXN", "UNH", "UNP", "UPS", "V", "WMT", "DIS", "WM", "WFC"]
    
    w4h = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
    wd = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
    ww = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"
    
    watchlist = list(set(italia + europa + usa))
    timeframes = {"4h": ["4h", "730d", w4h, "240"], "Daily": ["1d", "5y", wd, "D"], "Weekly": ["1wk", "10y", ww, "W"]}
    
    while True:
        print(f"🚀 NUOVO CICLO AVVIATO: {datetime.now().strftime('%H:%M:%S')}")
        for ticker in watchlist:
            for tf, cfg in timeframes.items():
                try:
                    df = yf.download(ticker, period=cfg[1], interval=cfg[0], progress=False, timeout=5)
                    if df is None or df.empty or len(df) < 130: continue
                    
                    df['RSI'] = ta.rsi(df['Close'], length=60)
                    df['EMA'] = ta.ema(df['RSI'], length=60)
                    
                    if df['RSI'].iloc[-1] < df['EMA'].iloc[-1] and df['RSI'].iloc[-1] < 40:
                        requests.post(cfg[2], json={"content": f"🚨 Segnale su {ticker} ({tf})"})
                    
                    time.sleep(0.5)
                except Exception:
                    continue 
        print("✅ CICLO COMPLETATO. ATTESA 1 ORA...")
        time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    run_bot()
