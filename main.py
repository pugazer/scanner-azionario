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
    italia = ["A2A.MI", "AMP.MI", "AZM.MI", "BAMI.MI", "BCA.MI", "BPER.MI", "BZU.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "ERG.MI", "EVO.MI", "RACE.MI", "FBK.MI", "G.MI", "HER.MI", "INW.MI", "ISP.MI", "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PIRC.MI", "PST.MI", "PRY.MI", "REC.MI", "SGO.MI", "SRG.MI", "STLAM.MI", "STMMI.MI", "TEN.MI", "TRN.MI", "UCG.MI", "UNI.MI"]
    europa = ["ADS.DE", "ADYEN.AS", "AD.AS", "AI.PA", "AIR.PA", "ALV.DE", "ASML.AS", "CS.PA", "BAS.DE", "BAYN.DE", "BBVA.MC", "SAN.MC", "BMW.DE", "BNP.PA", "DTE.DE", "ENR.DE", "EL.PA", "IBE.MC", "ITX.MC", "INGA.AS", "KER.PA", "MBG.DE", "MC.PA", "MUV2.DE", "OR.PA", "PRX.AS", "RI.PA", "RMS.PA", "RWE.DE", "SAF.PA", "SAN.PA", "SAP.DE", "SU.PA", "SIE.DE", "UNA.AS", "VOW3.DE", "WKL.AS", "DHL.DE", "HEI.DE", "CON.DE"]
    usa = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "ADBE", "AMD", "COST", "AVGO", "CSCO", "ACN", "ADSK", "AEE", "AEP", "AES", "AFL", "A", "APD", "AKAM", "ALK", "ALB", "ARE", "ALLE", "LNT", "ALL", "GOOG", "MO", "AMGN", "APH", "ADI", "ANSS", "AON", "APA", "APO", "AMAT", "APTV", "ACGL", "ADM", "AJG", "AIZ", "ATO", "AVB", "AVY", "AXON", "BRK-B", "BAC", "BAX", "BDX", "BKR", "BALL", "WRB", "BBY", "BIO", "BIIB", "BLK", "BX", "BA", "BK", "BXP", "BSX", "BMY", "BR", "BRO", "CARR", "CTLT", "CAT", "CBOE", "CBRE", "CCI", "CELH", "CNC", "CNP", "CF", "CHRW", "CHD", "CI", "CINF", "CTAS", "CSCO", "C", "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "CL", "CMCSA", "CMA", "CAG", "COP", "ED", "STZ", "CE", "COV", "CPRT", "GLW", "CTVA", "CSGP", "CRWD", "CSX", "CMI", "CVS", "DHR", "DRI", "DVA", "DE", "DAL", "XRAY", "DVN", "DXCM", "FANG", "DLR", "DFS", "DG", "DLTR", "D", "DPZ", "DOV", "DOW", "DHI", "DTE", "DUK", "EMN", "ETN", "EBAY", "ECL", "EIX", "EW", "EA", "ELV", "EMR", "ENPH", "EOG", "EPAM", "EQT", "EFX", "EQR", "ESS", "EL", "ETR", "EVRG", "ES", "EXC", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FICO", "FAST", "FRT", "FDX", "FIS", "FITB", "FSLR", "FE", "FI", "FMC", "F", "FTNT", "FTV", "FOXA", "FOX", "BEN", "FCX", "GRMN", "IT", "GE", "GEHC", "GEV", "GEN", "GNRC", "GD", "GIS", "GM", "GPC", "GILD", "GPN", "GL", "GS", "HAL", "HIG", "HAS", "HCA", "HSY", "HES", "HPE", "HLT", "HOLX", "HD", "HON", "HRL", "HST", "HWM", "HPQ", "HUM", "HBAN", "HII", "IBM", "IEX", "IDXX", "ITW", "ILMN", "INCY", "IR", "INTC", "ICE", "IFF", "INTU", "ISRG", "IVZ", "INVH", "IQV", "IRM", "JBHT", "JKHY", "J", "SJM", "JNJ", "JCI", "JPM", "JNPR", "K", "KVUE", "KMB", "KIM", "KMI", "KLAC", "KHC", "KR", "LHX", "LH", "LRCX", "LW", "LVS", "LDOS", "LEN", "LLY", "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LULU", "LYB", "MTB", "MRO", "MPC", "MKTX", "MAR", "MMC", "MNST", "MCHP", "MDLZ", "MET", "MTD", "MGM", "MU", "MHK", "TAP", "MKC", "MCK", "MDT", "MRK", "MS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX", "NEM", "NWL", "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS", "NOC", "NCLH", "NRG", "NUE", "ORLY", "O", "ODFL", "OMC", "ON", "ORCL", "OTIS", "PCAR", "PKG", "PANW", "PAYX", "PAYC", "PYPL", "PNR", "PEP", "PFE", "PCG", "PM", "PNC", "PNW", "POOL", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU", "PEG", "PSA", "PHM", "QRVO", "QCOM", "PWR", "DGX", "RL", "RJF", "RTX", "REG", "REGN", "RF", "RSG", "RMD", "RHI", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC", "SLB", "STX", "SEE", "SRE", "NOW", "SHW", "SPG", "SWKS", "SNA", "SO", "LUV", "SWK", "SBUX", "STT", "SYK", "SYF", "SNPS", "SYY", "TMUS", "TROW", "TTWO", "TPR", "TGT", "TEL", "TDY", "TFX", "TER", "TSCO", "TXN", "TXT", "TMO", "TJX", "T", "TT", "TDG", "TRV", "TRU", "TYL", "TSN", "USB", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH", "UHS", "VLO", "VTR", "VRSN", "VRSK", "VZ", "VRTX", "VFC", "VTRS", "VICI", "V", "VMC", "WAB", "WMT", "WBA", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST", "WDC", "WY", "WHR", "WMB", "WTW", "WYNN", "XEL", "XYL", "YUM", "ZBH", "ZBRA", "ZTS", "ZION"]
    
    w4h = "https://discord.com/api/webhooks/1515991717201838164/olqUv9cAjdlaOOEnO46tilUel16UuzMmLzD6VtDlTmqXFi7Nb4dZbirdejLXke1VKnE9"
    wd = "https://discord.com/api/webhooks/1515997229385777213/n6W-mew2MNDjOdhT6ASMx_KUOO5QgY463AoS2VI_9TgE2cXlLd7jPu0psgWuhQOEn7Pp"
    ww = "https://discord.com/api/webhooks/1515997383606009936/KyJhKIRSHDlfDrH706mx5gZ5jxomU2-DhdxC6ZNae4C9HB3_cY50pVhstjzv2sMai-H5"
    
    watchlist = list(set(italia + europa + usa))
    timeframes = {"4h": ["4h", "730d", w4h, "240"], "Daily": ["1d", "5y", wd, "D"], "Weekly": ["1wk", "10y", ww, "W"]}
    
    while True:
        print("🚀 NUOVO CICLO AVVIATO")
        for ticker in watchlist:
            for tf, cfg in timeframes.items():
                try:
                    df = yf.download(ticker, period=cfg[1], interval=cfg[0], progress=False, timeout=10)
                    if df is None or df.empty or len(df) < 130: continue
                    df['RSI'] = ta.rsi(df['Close'], length=60)
                    df['EMA'] = ta.ema(df['RSI'], length=60)
                    if df['RSI'].iloc[-1] < df['EMA'].iloc[-1] and df['RSI'].iloc[-1] < 40:
                        requests.post(cfg[2], json={"content": f"🚨 Segnale su {ticker} ({tf})"})
                    time.sleep(0.8)
                except: continue
        time.sleep(3600)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    run_bot()
