import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import logging
import threading
import os
from flask import Flask
from datetime import datetime

# --- SERVER FLASK PER RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Il bot è online e sta scansionando!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURAZIONE ---
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

WEBHOOK_4H     = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
WEBHOOK_DAILY  = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
WEBHOOK_WEEKLY = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"

DIMENSIONE_BLOCCO = 200
MINUTI_PAUSA_BLOCCO = 5
MINUTI_PAUSA_CICLO = 60

italia = ["A2A.MI", "AMP.MI", "AZM.MI", "BAMI.MI", "BCA.MI", "BPER.MI", "BZU.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "EVO.MI", "RACE.MI", "FBK.MI", "G.MI", "HER.MI", "INW.MI", "ISP.MI", "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PIRC.MI", "PST.MI", "PRY.MI", "REC.MI", "SGO.MI", "SRG.MI", "STLAM.MI", "STMMI.MI", "TEN.MI", "TRN.MI", "UCG.MI", "UNI.MI"]
europa = ["ADS.DE", "ADYEN.AS", "AD.AS", "AI.PA", "AIR.PA", "ALV.DE", "ASML.AS", "CS.PA", "BAS.DE", "BAYN.DE", "BBVA.MC", "SAN.MC", "BMW.DE", "BNP.PA", "DTE.DE", "ENR.DE", "EL.PA", "IBE.MC", "ITX.MC", "INGA.AS", "KER.PA", "MBG.DE", "MC.PA", "MUV2.DE", "OR.PA", "PRX.AS", "RI.PA", "RMS.PA", "RWE.DE", "SAF.PA", "SAN.PA", "SAP.DE", "SU.PA", "SIE.DE", "UNA.AS", "VOW3.DE", "WKL.AS", "DHL.DE", "HEI.DE", "CON.DE"]
usa_shares = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ADBE", "AMD", "COST", "AVGO", "CSCO", "ACN", "ADSK", "AEE", "AEP", "AES", "AFL", "A", "APD", "AKAM", "ALK", "ALB", "ARE", "ALLE", "LNT", "ALL", "GOOG", "MO", "AMGN", "APH", "ADI", "ANSS", "AON", "APA", "APO", "AMAT", "APTV", "ACGL", "ADM", "AJG", "AIZ", "ATO", "AVB", "AVY", "AXON", "BRK-B", "BAC", "BAX", "BDX", "BKR", "BALL", "WRB", "BBY", "BIO", "BIIB", "BLK", "BX", "BA", "BK", "BXP", "BSX", "BMY", "BR", "BRO", "CARR", "CTLT", "CAT", "CBOE", "CBRE", "CCI", "CELH", "CNC", "CNP", "CF", "CHRW", "CHD", "CI", "CINF", "CTAS", "CSCO", "C", "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "CL", "CMCSA", "CMA", "CAG", "COP", "ED", "STZ", "CE", "COV", "CPRT", "GLW", "CTVA", "CSGP", "CRWD", "CSX", "CMI", "CVS", "DHR", "DRI", "DVA", "DE", "DAL", "XRAY", "DVN", "DXCM", "FANG", "DLR", "DFS", "DG", "DLTR", "D", "DPZ", "DOV", "DOW", "DHI", "DTE", "DUK", "EMN", "ETN", "EBAY", "ECL", "EIX", "EW", "EA", "ELV", "EMR", "ENPH", "EOG", "EPAM", "EQT", "EFX", "EQR", "ESS", "EL", "ETR", "EVRG", "ES", "EXC", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FICO", "FAST", "FRT", "FDX", "FIS", "FITB", "FSLR", "FE", "FI", "FMC", "F", "FTNT", "FTV", "FOXA", "FOX", "BEN", "FCX", "GRMN", "IT", "GE", "GEHC", "GEV", "GEN", "GNRC", "GD", "GIS", "GM", "GPC", "GILD", "GPN", "GL", "GS", "HAL", "HIG", "HAS", "HCA", "HSY", "HES", "HPE", "HLT", "HOLX", "HD", "HON", "HRL", "HST", "HWM", "HPQ", "HUM", "HBAN", "HII", "IBM", "IEX", "IDXX", "ITW", "ILMN", "INCY", "IR", "INTC", "ICE", "IFF", "INTU", "ISRG", "IVZ", "INVH", "IQV", "IRM", "JBHT", "JKHY", "J", "SJM", "JNJ", "JCI", "JPM", "JNPR", "K", "KVUE", "KMB", "KIM", "KMI", "KLAC", "KHC", "KR", "LHX", "LH", "LRCX", "LW", "LVS", "LDOS", "LEN", "LLY", "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LULU", "LYB", "MTB", "MRO", "MPC", "MKTX", "MAR", "MMC", "MNST", "MCHP", "MDLZ", "MET", "MTD", "MGM", "MU", "MHK", "TAP", "MKC", "MCK", "MDT", "MRK", "MS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX", "NEM", "NWL", "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS", "NOC", "NCLH", "NRG", "NUE", "ORLY", "O", "ODFL", "OMC", "ON", "ORCL", "OTIS", "PCAR", "PKG", "PANW", "PAYX", "PAYC", "PYPL", "PNR", "PEP", "PFE", "PCG", "PM", "PNC", "PNW", "POOL", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU", "PEG", "PSA", "PHM", "QRVO", "QCOM", "PWR", "DGX", "RL", "RJF", "RTX", "REG", "REGN", "RF", "RSG", "RMD", "RHI", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC", "SLB", "STX", "SEE", "SRE", "NOW", "SHW", "SPG", "SWKS", "SNA", "SO", "LUV", "SWK", "SBUX", "STT", "SYK", "SYF", "SNPS", "SYY", "TMUS", "TROW", "TTWO", "TPR", "TGT", "TEL", "TDY", "TFX", "TER", "TSCO", "TXN", "TXT", "TMO", "TJX", "T", "TT", "TDG", "TRV", "TRU", "TYL", "TSN", "USB", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH", "UHS", "VLO", "VTR", "VRSN", "VRSK", "VZ", "VRTX", "VFC", "VTRS", "VICI", "V", "VMC", "WAB", "WMT", "WBA", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST", "WDC", "WY", "WHR", "WMB", "WTW", "WYNN", "XEL", "XYL", "YUM", "ZBH", "ZBRA", "ZTS", "ZION"]

watchlist = list(set(italia + europa + usa_shares))
timeframes = {
    "4h":     {"interval": "4h",  "period": "730d", "webhook": WEBHOOK_4H,   "tv_interval": "240"},
    "Daily":  {"interval": "1d",  "period": "5y",    "webhook": WEBHOOK_DAILY,  "tv_interval": "D"},
    "Weekly": {"interval": "1wk", "period": "10y",   "webhook": WEBHOOK_WEEKLY, "tv_interval": "W"}
}

def dividi_in_blocchi(lista, n):
    for i in range(0, len(lista), n):
        yield lista[i:i + n]

ciclo = 1
while True:
    print(f"\n🚀 CICLO #{ciclo} AVVIATO: {datetime.now().strftime('%H:%M:%S')}")
    blocchi_azioni = list(dividi_in_blocchi(watchlist, DIMENSIONE_BLOCCO))
    tot_blocchi = len(blocchi_azioni)
    
    for num_blocco, blocco_corrente in enumerate(blocchi_azioni, 1):
        for tf_name, tf_config in timeframes.items():
            for ticker in blocco_corrente:
                try:
                    df = yf.download(ticker, period=tf_config["period"], interval=tf_config["interval"], progress=False)
                    if df.empty or len(df) < 130: continue
                    if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
                    
                    df['RSI_60'] = ta.rsi(df['Close'], length=60)
                    df['EMA_RSI_60'] = ta.ema(df['RSI_60'], length=60)
                    df = df.dropna()
                    
                    ultimo_rsi = float(df['RSI_60'].iloc[-1])
                    ultima_ema_rsi = float(df['EMA_RSI_60'].iloc[-1])
                    
                    if ultimo_rsi < ultima_ema_rsi and ultimo_rsi < 40:
                        df['Sotto_Media'] = df['RSI_60'] < df['EMA_RSI_60']
                        candele = 0
                        for i in range(len(df)-1, -1, -1):
                            if df['Sotto_Media'].iloc[i]: candele += 1
                            else: break
                        
                        if candele >= 15:
                            valuta = "$" if any(ext in ticker for ext in [".MI", ".PA", ".DE", ".AS", ".MC", ".L", ".SW", ".CO"]) == False else "€"
                            ticker_tv = ticker.split('.')[0]
                            link = f"https://it.tradingview.com/chart/?symbol={ticker_tv}&interval={tf_config['tv_interval']}"
                            
                            msg = {
                                "content": (
                                    f"🚨 **ZONA ACCUMULO ISTITUZIONALE (RSI < 40)** 🚨\n\n"
                                    f"📌 **Azione:** `{ticker}`\n"
                                    f"⏱️ **Timeframe:** `{tf_name}`\n"
                                    f"💰 **Prezzo:** {valuta}{float(df['Close'].iloc[-1]):.2f}\n"
                                    f"📉 **RSI (60):** `{ultimo_rsi:.1f}` (Sotto media EMA 60)\n"
                                    f"⏳ **Persistenza:** `{candele}` candele sotto media.\n"
                                    f"🔗 [Apri Grafico]({link})"
                                )
                            }
                            requests.post(tf_config["webhook"], json=msg)
                            time.sleep(0.5)
                    time.sleep(0.15)
                except: continue
        
        if num_blocco < tot_blocchi:
            time.sleep(MINUTI_PAUSA_BLOCCO * 60)
            
    ciclo += 1
    time.sleep(MINUTI_PAUSA_CICLO * 60)
