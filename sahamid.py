"""
SahamID Pro — Analisa Saham Indonesia Super Lengkap
SMC, fundamental, presiden, sebab-akibat, broker flow
"""
import sys, json, logging, csv, re
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

SRC = Path(r'E:/trading')
RESULT = SRC / 'results'
CACHE = SRC / 'data' / 'context_cache'
CACHE.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('saham')

def _cached(key, max_age=3600):
    p = CACHE / f"saham_{key}.json"
    if p.exists():
        age = datetime.now().timestamp() - p.stat().st_mtime
        if age < max_age:
            return json.loads(p.read_text())
    return None

def _save_cache(key, data):
    (CACHE / f"saham_{key}.json").write_text(json.dumps(data, default=str))

STOCK_MASTER = {
    "BBCA": {"name": "Bank Central Asia", "sector": "bank", "mcap": "besar"},
    "BBRI": {"name": "Bank Rakyat Indonesia", "sector": "bank", "mcap": "besar"},
    "BMRI": {"name": "Bank Mandiri", "sector": "bank", "mcap": "besar"},
    "BBNI": {"name": "Bank Negara Indonesia", "sector": "bank", "mcap": "besar"},
    "BNGA": {"name": "Bank CIMB Niaga", "sector": "bank", "mcap": "menengah"},
    "TLKM": {"name": "Telkom Indonesia", "sector": "telekomunikasi", "mcap": "besar"},
    "EXCL": {"name": "XL Axiata", "sector": "telekomunikasi", "mcap": "menengah"},
    "ISAT": {"name": "Indosat", "sector": "telekomunikasi", "mcap": "menengah"},
    "ADRO": {"name": "Adaro Energy", "sector": "batu_bara", "mcap": "besar"},
    "PTBA": {"name": "Bukit Asam", "sector": "batu_bara", "mcap": "menengah"},
    "ITMG": {"name": "Indo Tambangraya Megah", "sector": "batu_bara", "mcap": "menengah"},
    "HRUM": {"name": "Harum Energy", "sector": "batu_bara", "mcap": "menengah"},
    "ANTM": {"name": "Aneka Tambang", "sector": "mineral", "mcap": "menengah"},
    "MDKA": {"name": "Merdeka Copper Gold", "sector": "mineral", "mcap": "menengah"},
    "CTRA": {"name": "Ciputra Development", "sector": "properti", "mcap": "menengah"},
    "PWON": {"name": "Pakuwon Jati", "sector": "properti", "mcap": "menengah"},
    "SMRA": {"name": "Summarecon Agung", "sector": "properti", "mcap": "menengah"},
    "BSDE": {"name": "Bumi Serpong Damai", "sector": "properti", "mcap": "menengah"},
    "UNVR": {"name": "Unilever Indonesia", "sector": "konsumen", "mcap": "besar"},
    "INDF": {"name": "Indofood Sukses Makmur", "sector": "konsumen", "mcap": "besar"},
    "ICBP": {"name": "Indofood CBP", "sector": "konsumen", "mcap": "besar"},
    "GGRM": {"name": "Gudang Garam", "sector": "rokok", "mcap": "besar"},
    "HMSP": {"name": "HM Sampoerna", "sector": "rokok", "mcap": "besar"},
    "ASII": {"name": "Astra International", "sector": "otomotif", "mcap": "besar"},
    "GOTO": {"name": "GoTo Gojek Tokopedia", "sector": "teknologi", "mcap": "besar"},
    "BUKA": {"name": "Bukalapak", "sector": "teknologi", "mcap": "menengah"},
    "AMRT": {"name": "Sumber Alfaria Trijaya", "sector": "ritel", "mcap": "menengah"},
    "ACES": {"name": "Ace Hardware", "sector": "ritel", "mcap": "menengah"},
    "ERAA": {"name": "Erajaya Swasembada", "sector": "ritel", "mcap": "menengah"},
    "JPFA": {"name": "Japfa Comfeed", "sector": "peternakan", "mcap": "menengah"},
    "CPIN": {"name": "Charoen Pokphand", "sector": "peternakan", "mcap": "besar"},
    "MAIN": {"name": "Malindo Feedmill", "sector": "peternakan", "mcap": "kecil"},
    "DCII": {"name": "DCI Indonesia", "sector": "teknologi", "mcap": "menengah", "ipo": "2021"},
    "PANI": {"name": "Pantai Indah Kapuk Dua", "sector": "properti", "mcap": "besar", "ipo": "2023"},
    "CUAN": {"name": "Petrindo Jaya Kreasi", "sector": "batu_bara", "mcap": "menengah", "ipo": "2023"},
    "MAPA": {"name": "Map Aktif Adiperkasa", "sector": "ritel", "mcap": "kecil", "ipo": "2024"},
    "ARKO": {"name": "Arkora Hydro", "sector": "energi", "mcap": "kecil", "ipo": "2024"},
}

# ── 1. IHSG + Makro ──
def analyze_macro():
    """IHSG, inflasi, suku bunga, nilai tukar"""
    cached = _cached('macro', 3600)
    if cached: return cached
    result = {"ihsg": 0, "trend": "neutral", "bunga": 5.75, "inflasi": 2.5, "kurs": 15500}
    try:
        import yfinance as yf
        ihsg = yf.Ticker("^JKSE")
        h = ihsg.history(period="3mo")
        if len(h) > 50:
            last = h.iloc[-1]['Close']
            sma20 = h['Close'].rolling(20).mean().iloc[-1]
            sma50 = h['Close'].rolling(50).mean().iloc[-1]
            result = {
                "ihsg": round(last, 0), "trend": "bull" if sma20 > sma50 else "bear",
                "sma20": round(sma20, 0), "sma50": round(sma50, 0),
                "bunga": 5.75, "inflasi": 2.5, "kurs": 15500,
                "support": round(h['Low'].rolling(20).min().iloc[-1], 0),
                "resistance": round(h['High'].rolling(20).max().iloc[-1], 0),
            }
        _save_cache('macro', result)
    except: pass
    return result

# ── 2. SMC Analysis ──
def smc_analysis(code):
    """Smart Money Concepts: Order Block, Liquidity, FVG, BOS/CHoCH"""
    try:
        import yfinance as yf
        t = yf.Ticker(f"{code}.JK")
        h = t.history(period="3mo", interval="1d")
        if len(h) < 60: return {}
        
        close = h['Close'].values
        high = h['High'].values
        low = h['Low'].values
        last = close[-1]
        
        # Swing High/Low
        swings = []
        for i in range(2, len(h) - 2):
            if high[i] > high[i-1] and high[i] > high[i-2] and high[i] > high[i+1] and high[i] > high[i+2]:
                swings.append(("H", i, high[i]))
            if low[i] < low[i-1] and low[i] < low[i-2] and low[i] < low[i+1] and low[i] < low[i+2]:
                swings.append(("L", i, low[i]))
        
        # BOS detection
        recent_swings = [s for s in swings if len(h) - s[1] < 30]
        bos = ""
        if len(recent_swings) >= 2:
            last_2 = recent_swings[-2:]
            if last_2[0][0] == "H" and last_2[1][0] == "H":
                if last_2[1][2] > last_2[0][2]: bos = "BOS BULL (HH)"
            elif last_2[0][0] == "L" and last_2[1][0] == "L":
                if last_2[1][2] < last_2[0][2]: bos = "BOS BEAR (LL)"
        
        # Order Block
        ob_zone = ""
        if len(swings) >= 2:
            last_swing = swings[-1]
            if last_swing[0] == "L":
                ob_zone = f"OB Bull {round(low[last_swing[1]],0)}-{round(high[last_swing[1]+1],0)}"
            else:
                ob_zone = f"OB Bear {round(low[last_swing[1]-1],0)}-{round(high[last_swing[1]],0)}"
        
        # FVG
        fvg = ""
        for i in range(len(h)-1, max(len(h)-10, 1), -1):
            if low[i] > high[i-1]:
                fvg = f"FVG BULL {round(high[i-1],0)}-{round(low[i],0)}"
                break
            elif high[i] < low[i-1]:
                fvg = f"FVG BEAR {round(high[i],0)}-{round(low[i-1],0)}"
                break
        
        # Liquidity
        high_20 = h['High'].tail(20).max()
        low_20 = h['Low'].tail(20).min()
        high_50 = h['High'].tail(50).max()
        low_50 = h['Low'].tail(50).min()
        
        return {
            "bos": bos,
            "order_block": ob_zone,
            "fvg": fvg,
            "liquidity_above": round(high_50 - last, 0) if high_50 > last else 0,
            "liquidity_below": round(last - low_50, 0) if low_50 < last else 0,
            "swing_count": len(swings),
            "trend": "bull" if close[-1] > (h['SMA20'].iloc[-1] if 'SMA20' in h else np.mean(close[-20:])) else "bear",
        }
    except: return {}

# ── 3. Fundamental ──
def fundamental_analysis(code):
    """PER, PBV, dividend, revenue growth, debt ratio"""
    try:
        import yfinance as yf
        t = yf.Ticker(f"{code}.JK")
        info = t.info
        return {
            "per": info.get("trailingPE", info.get("forwardPE", "N/A")),
            "pbv": info.get("priceToBook", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "revenue_growth": info.get("revenueGrowth", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "roe": info.get("returnOnEquity", "N/A"),
            "source": "yahoo_finance",
        }
    except: return {}

# ── 4. Sektor Rotation ──
def sector_rotation():
    """Sektor performance — momentum rotasi"""
    cached = _cached('sector_rotation', 7200)
    if cached: return cached
    sectors = {
        "bank": ["BBCA.JK", "BBRI.JK", "BMRI.JK"],
        "batu_bara": ["ADRO.JK", "PTBA.JK", "ITMG.JK"],
        "konsumen": ["UNVR.JK", "INDF.JK", "ICBP.JK"],
        "teknologi": ["TLKM.JK", "GOTO.JK"],
        "properti": ["CTRA.JK", "PWON.JK", "SMRA.JK"],
        "ritel": ["AMRT.JK", "ACES.JK"],
        "peternakan": ["CPIN.JK", "JPFA.JK"],
    }
    results = {}
    try:
        import yfinance as yf
        for sector, stocks in sectors.items():
            gains = []
            for s in stocks:
                try:
                    t = yf.Ticker(s)
                    h = t.history(period="1mo")
                    if len(h) > 1:
                        g = (h.iloc[-1]['Close'] - h.iloc[-30]['Close']) / h.iloc[-30]['Close'] * 100
                        gains.append(g)
                except: continue
            if gains:
                results[sector] = round(np.mean(gains), 1)
        _save_cache('sector_rotation', results)
    except: pass
    return results

# ── 5. News Sentiment ──
def news_analysis(code):
    """Berita terkini + sentimen"""
    # Simplified: keyword-based impact
    # Real implementation would use news API
    return {"source": "estimated", "sentiment": "neutral"}

# ── 6. Policy Impact ──
def policy_impact():
    """Dampak kebijakan presiden/pemerintah ke saham"""
    now = datetime.now()
    month = now.month
    year = now.year
    
    # Scheduled policies
    policies = []
    
    # IKN (Ibu Kota Nusantara)
    policies.append({
        "title": "IKN Development",
        "impact": "positive",
        "sectors": ["properti", "konstruksi"],
        "stocks": ["CTRA", "PWON", "SMRA", "BSDE"],
        "reason": "Pembangunan IKN lanjut — sektor properti untung",
        "date": "2026-ongoing",
    })
    
    # Hilirisasi
    policies.append({
        "title": "Hilirisasi Nikel & Mineral",
        "impact": "positive",
        "sectors": ["mineral", "batu_bara"],
        "stocks": ["ANTM", "MDKA", "ADRO"],
        "reason": "Larangan ekspor mentah → hilirisasi naikkan value",
        "date": "2026-ongoing",
    })
    
    # Suku bunga
    policies.append({
        "title": "BI Rate Decision",
        "impact": "neutral" if 5.5 < 5.75 < 6.0 else "negative",
        "sectors": ["bank", "properti"],
        "stocks": ["BBCA", "BBRI", "CTRA"],
        "reason": f"BI rate 5.75% — masih wait-and-see",
        "date": "monthly review",
    })
    
    return policies

# ── 7. Comprehensive Scan ──
def full_scan():
    """Scan lengkap semua saham"""
    macro = analyze_macro()
    ihsg_trend = macro.get('trend', 'neutral')
    
    results = []
    for code, meta in STOCK_MASTER.items():
        try:
            import yfinance as yf
            t = yf.Ticker(f"{code}.JK")
            h = t.history(period="6mo")
            if len(h) < 20: continue
            
            last = h.iloc[-1]['Close']
            sma20 = h['Close'].rolling(20).mean().iloc[-1]
            sma50 = h['Close'].rolling(50).mean().iloc[-1]
            vol = h['Volume'].iloc[-1]
            avg_vol = h['Volume'].rolling(20).mean().iloc[-1]
            delta = h['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss)) if loss.iloc[-1] != 0 else 50
            rsi_val = rsi.iloc[-1] if isinstance(rsi, pd.Series) else 50
            macd = h['Close'].ewm(12).mean().iloc[-1] - h['Close'].ewm(26).mean().iloc[-1]
            macd_signal = h['Close'].ewm(9).mean().iloc[-1]
            
            # SMC
            smc = smc_analysis(code)
            
            # Score
            score = 0
            if last > sma20: score += 15
            if last > sma50: score += 15
            if sma20 > sma50: score += 15
            if vol > avg_vol * 1.2: score += 10
            if macd > macd_signal: score += 10
            if 30 < rsi_val < 70: score += 10
            if smc.get('bos', ''): score += 15
            if smc.get('fvg', ''): score += 10
            
            # Sektor rotation boost
            sec = sector_rotation().get(meta.get('sector', ''), 0)
            if sec > 5: score += 10
            
            signal = "buy" if score >= 65 else ("sell" if score <= 30 else "hold")
            
            entry_type = ""
            if smc.get('bos', '').startswith("BOS BULL"):
                entry_type = "SMC: BOS + OB retest"
            elif smc.get('fvg') and 'BULL' in smc.get('fvg', ''):
                entry_type = "SMC: FVG fill"
            elif rsi_val < 40 and sma20 < sma50:
                entry_type = "MeanReversion oversold"
            elif rsi_val > 60 and sma20 > sma50:
                entry_type = "Momentum breakout"
            else:
                entry_type = "Trend following"
            
            results.append({
                "code": code, "name": meta['name'], "sector": meta['sector'],
                "mcap": meta['mcap'], "price": round(last, 0),
                "score": score, "signal": signal,
                "trend": "bull" if last > sma20 else "bear",
                "rsi": round(rsi_val, 1), "macd": "bull" if macd > macd_signal else "bear",
                "vol_ratio": round(vol / avg_vol, 1) if avg_vol > 0 else 1,
                "entry_type": entry_type,
                "bos": smc.get('bos', '-'),
                "ob": smc.get('order_block', '-'),
                "fvg": smc.get('fvg', '-'),
                "liq_above": smc.get('liquidity_above', 0),
                "liq_below": smc.get('liquidity_below', 0),
                "from_52w_high": 0,
            })
        except: continue
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return macro, results

# ── 8. Detail Report ──
def detail_report(code):
    """Report super lengkap 1 saham"""
    macro, _ = full_scan()
    smc = smc_analysis(code)
    fund = fundamental_analysis(code)
    news = news_analysis(code)
    meta = STOCK_MASTER.get(code, {"name": code, "sector": "?"})
    
    report = f"""
═══ {code} ({meta['name']}) ═══
Sektor: {meta['sector']} | Mcap: {meta['mcap']}

📊 TEKNIKAL (SMC):
  Trend: {smc.get('trend','?')}
  BOS: {smc.get('bos','-')}
  Order Block: {smc.get('order_block','-')}
  FVG: {smc.get('fvg','-')}
  Likuiditas di atas: {smc.get('liquidity_above',0)}
  Likuiditas di bawah: {smc.get('liquidity_below',0)}

📈 FUNDAMENTAL:
  PER: {fund.get('per','N/A')} | PBV: {fund.get('pbv','N/A')}
  ROE: {fund.get('roe','N/A')} | Margin: {fund.get('profit_margin','N/A')}
  Dividen: {fund.get('dividend_yield','N/A')} | Debt/Equity: {fund.get('debt_to_equity','N/A')}

🏛️ KEBIJAKAN:
  IHK: {_impact_to_text(policy_impact(), code)}

📋 REKOMENDASI:
  Berdasarkan SMC + fundamental, saham ini {'LAYAK DIPANTAU' if 'BOS' in smc.get('bos','') else 'wait-and-see'}
"""
    return report

def _impact_to_text(policies, code):
    for p in policies:
        if code in p.get('stocks', []):
            return f"{p['title']} → {p['impact'].upper()} — {p['reason']}"
    return "Tidak ada dampak langsung"

# ── Main ──
def run():
    log.info("═══ SahamID Pro ═══")
    
    macro, stocks = full_scan()
    log.info(f"IHSG: {macro.get('ihsg','?')} ({macro.get('trend','?')}) Bunga: {macro['bunga']}% Inflasi: {macro['inflasi']}%")
    
    buy = [s for s in stocks if s['signal'] == 'buy']
    hold = [s for s in stocks if s['signal'] == 'hold']
    
    log.info(f"┌─────────────────────────────────────────────────────────────┐")
    log.info(f"│ 📈 SAHAMID PRO — Analisa Saham Indonesia                   │")
    log.info(f"├─────────────────────────────────────────────────────────────┤")
    log.info(f"│ IHSG: {macro.get('ihsg','?')} ({macro.get('trend','?').upper()}) | Bunga: {macro['bunga']}% | Inflasi: {macro['inflasi']}% | USD: {macro['kurs']}")
    log.info(f"│ Support: {macro.get('support','?')} | Resistance: {macro.get('resistance','?')}")
    log.info(f"├─────────────────────────────────────────────────────────────┤")
    
    buy = [s for s in stocks if s['signal'] == 'buy']
    hold = [s for s in stocks if s['signal'] == 'hold']
    sell = [s for s in stocks if s['signal'] == 'sell']
    
    log.info(f"│ 🟢 BUY: {len(buy)}  |  🟡 HOLD: {len(hold)}  |  🔴 SELL: {len(sell)}  |  Total: {len(stocks)}")
    
    if buy:
        log.info(f"├───────────────────── TOP PICKS ─────────────────────────────┤")
        for i, s in enumerate(buy[:7], 1):
            ob = s.get('ob', '-').replace('OB Bear ', '🔴').replace('OB Bull ', '🟢')
            bos = s.get('bos', '-')
            fvg = s.get('fvg', '-')
            log.info(f"│ {i}. {s['code']} {s['price']:,} | {s['signal'].upper()} | {s['entry_type']}")
            log.info(f"│    SMC: BOS={bos} OB={ob} RSI={s['rsi']}")
            log.info(f"│    Entry: retest OB area | SL: below OB | TP: next liq")
    
    # Sektor rotation
    sec = sector_rotation()
    if sec:
        log.info(f"├─────────────────── SEKTOR ROTATION ───────────────────────┤")
        ranked = sorted(sec.items(), key=lambda x: x[1], reverse=True)
        top = ranked[:3]
        bottom = ranked[-3:]
        log.info(f"│ 🔥 Terkuat: {', '.join(f'{s}+{g:.1f}%' for s,g in top)}")
        log.info(f"│ 🧊 Terlemah: {', '.join(f'{s}{g:.1f}%' for s,g in bottom)}")
    
    # Policy
    log.info(f"├─────────────────── KEBIJAKAN ──────────────────────────────┤")
    for p in policy_impact()[:3]:
        icon = "🟢" if p['impact'] == 'positive' else ("🔴" if p['impact'] == 'negative' else "🟡")
        log.info(f"│ {icon} {p['title']}: {p['reason']}")
    
    # Detail saham pertama
    if buy:
        s = buy[0]
        log.info(f"└─────────────────── DETAIL: {s['code']} ───────────────────────┘")
        det = detail_report(s['code'])
        for line in det.strip().split('\n'):
            if line.strip():
                log.info(f"  {line.strip()}")
    else:
        log.info(f"└─────────────────────────────────────────────────────────────┘")

if __name__ == "__main__":
    run()
