"""
Market Context — fundamental + sentiment data untuk adaptive trading
DXY, Yield, COT, Currency Strength, Sentiment, News Impact
"""
import sys, json, logging
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

SRC = Path(r'E:/trading')
log = logging.getLogger('context')

CACHE = SRC / 'data' / 'context_cache'
CACHE.mkdir(parents=True, exist_ok=True)

def _cached(key, max_age=3600):
    p = CACHE / f"{key}.json"
    if p.exists():
        age = datetime.now().timestamp() - p.stat().st_mtime
        if age < max_age:
            return json.loads(p.read_text())
    return None

def _save_cache(key, data):
    (CACHE / f"{key}.json").write_text(json.dumps(data, default=str))

# ── 1. DXY (Dollar Index) via yfinance ──
def get_dxy():
    """DXY dari Yahoo Finance"""
    cached = _cached('dxy', 3600)
    if cached: return cached
    try:
        import yfinance as yf
        dx = yf.Ticker("DX-Y.NYB")
        hist = dx.history(period="5d", interval="1h")
        if len(hist) > 0:
            latest = hist.iloc[-1]
            result = {
                "price": round(latest['Close'], 2),
                "change": round(latest['Close'] - hist.iloc[-2]['Close'], 2) if len(hist) > 1 else 0,
                "trend": "bull" if latest['Close'] > hist['Close'].rolling(20).mean().iloc[-1] else "bear",
                "timestamp": str(hist.index[-1]),
            }
            _save_cache('dxy', result)
            return result
    except Exception as e:
        log.warning(f"DXY error: {e}")
    return {"price": 0, "change": 0, "trend": "neutral"}

# ── 2. US 10Y Yield via yfinance ──
def get_yield():
    """US 10Y Treasury yield from yfinance (^TNX)"""
    cached = _cached('yield_10y', 3600)
    if cached: return cached
    try:
        import yfinance as yf
        tnx = yf.Ticker("^TNX")
        hist = tnx.history(period="5d", interval="1h")
        if len(hist) > 0:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Close']
            trend = "up" if len(hist) > 3 and latest['Close'] > hist['Close'].iloc[-3] else "down"
            result = {
                "yield": round(latest['Close'], 2),
                "change": round(latest['Close'] - prev, 2),
                "trend": trend,
                "timestamp": str(hist.index[-1]),
            }
            _save_cache('yield_10y', result)
            return result
    except Exception as e:
        log.warning(f"Yield error: {e}")
    return {"yield": 0, "change": 0, "trend": "neutral"}

# ── 3. Commitments of Traders (EURUSD) ──
def get_cot():
    """COT analysis — falls back to estimated data from yfinance positioning"""
    cached = _cached('cot', 86400)
    if cached: return cached
    
    # Default fallback
    result = {
        "EURUSD": {"net": 0, "source": "unavailable"},
        "GBPUSD": {"net": 0, "source": "unavailable"},
        "XAU": {"net": 0, "oi": 0, "source": "unavailable"},
        "XAG": {"net": 0, "oi": 0, "source": "unavailable"},
    }
    
    # Try CFTC Socrata API (all futures including gold/silver)
    try:
        import urllib.request, json, re
        url = "https://publicreporting.cftc.gov/resource/yywx-7w5s.json?$limit=20"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read())
            if rows and len(rows) > 0:
                for r in rows:
                    market = r.get('market_and_exchange_names', '')
                    if 'EURO FX' in market:
                        result["EURUSD"] = {
                            "net": int(r.get('long_form', 0)) - int(r.get('short_form', 0)),
                            "long": int(r.get('long_form', 0)),
                            "short": int(r.get('short_form', 0)),
                            "source": "cftc",
                            "bias": "bullish" if int(r.get('long_form', 0)) > int(r.get('short_form', 0)) else "bearish"
                        }
                    elif 'GOLD' in market.upper() and 'SILVER' not in market.upper():
                        result["XAU"] = {
                            "net": int(r.get('long_form', 0)) - int(r.get('short_form', 0)),
                            "long": int(r.get('long_form', 0)),
                            "short": int(r.get('short_form', 0)),
                            "oi": int(r.get('open_interest_all', 0)),
                            "source": "cftc",
                            "bias": "bullish" if int(r.get('long_form', 0)) > int(r.get('short_form', 0)) else "bearish"
                        }
                    elif 'SILVER' in market.upper():
                        result["XAG"] = {
                            "net": int(r.get('long_form', 0)) - int(r.get('short_form', 0)),
                            "long": int(r.get('long_form', 0)),
                            "short": int(r.get('short_form', 0)),
                            "oi": int(r.get('open_interest_all', 0)),
                            "source": "cftc",
                            "bias": "bullish" if int(r.get('long_form', 0)) > int(r.get('short_form', 0)) else "bearish"
                        }
                _save_cache('cot', result)
                return result
    except Exception as e:
        log.warning(f"COT API: {e}")
    
    # Fallback: DXY-based estimation for XAU/XAG
    try:
        import yfinance as yf
        dxy = yf.Ticker("DX-Y.NYB")
        h = dxy.history(period="10d")
        if len(h) > 5:
            dxy_trend = "bear" if h['Close'].iloc[-1] < h['Close'].iloc[-5] else "bull"
            result["EURUSD"] = {"net": 15000 if dxy_trend == "bear" else -8000, "source": "estimated", "bias": "bullish" if dxy_trend == "bear" else "bearish"}
            result["GBPUSD"] = {"net": 5000 if dxy_trend == "bear" else -3000, "source": "estimated", "bias": "bullish" if dxy_trend == "bear" else "bearish"}
            # XAU inverse correlation with DXY (~-0.8 historically)
            result["XAU"] = {"net": 25000 if dxy_trend == "bear" else -12000, "oi": 450000, "source": "estimated", "bias": "bullish" if dxy_trend == "bear" else "bearish"}
            result["XAG"] = {"net": 8000 if dxy_trend == "bear" else -4000, "oi": 150000, "source": "estimated", "bias": "bullish" if dxy_trend == "bear" else "bearish"}
            _save_cache('cot', result)
    except: pass
    
    return result

# ── 4. Central Bank Sentiment (Hawkish / Dovish) ──
def get_hawkish_dovish():
    """Simplified central bank sentiment gauge based on recent policy stance"""
    cached = _cached('hawk_dove', 86400)
    if cached: return cached
    try:
        import urllib.request, json, re
        from urllib.parse import quote
        # Fetch latest Fed fund futures to gauge sentiment
        import yfinance as yf
        fed_futures = yf.Ticker("ZF=F")
        hist = fed_futures.history(period="5d")
        rate_bias = "neutral"
        sensitivity = 0
        if len(hist) > 1:
            chg = hist.iloc[-1]['Close'] - hist.iloc[-2]['Close']
            sensitivity = round(chg, 2)
            # Rate futures down = hawkish (rates expected up), up = dovish
            rate_bias = "hawkish" if chg < -0.05 else ("dovish" if chg > 0.05 else "neutral")

        result = {
            "fed": {"bias": rate_bias, "sensitivity": sensitivity, "last_rate": 4.50},
            "ecb": {"bias": "neutral", "last_rate": 3.65},
            "overall": rate_bias,
            "timestamp": datetime.now().isoformat(),
        }
        _save_cache('hawk_dove', result)
        return result
    except Exception as e:
        log.warning(f"Hawkish/dovish error: {e}")
    return {"fed": {"bias": "neutral", "last_rate": 4.50}, "ecb": {"bias": "neutral", "last_rate": 3.65}, "overall": "neutral"}

# ── 5. Geopolitical Risk Score ──
def get_geopolitics():
    """Simplified geopolitical risk score (0-100) from news sentiment sampling"""
    cached = _cached('geopolitics', 3600)
    if cached: return cached
    try:
        import urllib.request, json
        # Use GDACS (Global Disaster Alert) or simple news scoring
        # For a lightweight approach, sample a known news feed
        score = 30  # default moderate-low
        label = "low"
        try:
            import yfinance as yf
            # VIX as proxy for fear/disruption
            vix = yf.Ticker("^VIX")
            hv = vix.history(period="5d")
            if len(hv) > 0:
                vix_close = hv.iloc[-1]['Close']
                if vix_close > 30:
                    score = min(80, 50 + int((vix_close - 30) * 2))
                    label = "high"
                elif vix_close > 20:
                    score = min(50, 30 + int((vix_close - 20) * 3))
                    label = "moderate"
                else:
                    score = 15 + int(vix_close * 0.5)
                    label = "low"
        except Exception:
            pass

        result = {
            "score": score,
            "label": label,
            "vix_proxy": True,
            "timestamp": datetime.now().isoformat(),
        }
        _save_cache('geopolitics', result)
        return result
    except Exception as e:
        log.warning(f"Geopolitics error: {e}")
    return {"score": 30, "label": "low", "source": "default"}

# ── 6. Currency Strength (simplified) ──
def currency_strength():
    """Perbandingan kekuatan mata uang via yfinance pairs"""
    cached = _cached('fx_strength', 3600)
    if cached: return cached
    try:
        import yfinance as yf
        pairs = {
            "USD": "DX-Y.NYB", "EUR": "EURUSD=X", "GBP": "GBPUSD=X",
            "JPY": "USDJPY=X", "AUD": "AUDUSD=X", "CHF": "USDCHF=X",
            "CAD": "USDCAD=X", "NZD": "NZDUSD=X"
        }
        strength = {}
        for name, ticker in pairs.items():
            try:
                t = yf.Ticker(ticker)
                h = t.history(period="2d")
                if len(h) >= 2:
                    chg = (h.iloc[-1]['Close'] - h.iloc[-2]['Close']) / h.iloc[-2]['Close'] * 100
                    strength[name] = round(chg, 2)
            except: pass
        
        if strength:
            _save_cache('fx_strength', strength)
        return strength
    except Exception as e:
        log.warning(f"FX strength error: {e}")
    return {}

# ── 7. Sentiment (VIX-based) ──
def market_sentiment():
    """Market sentiment dari VIX fear index"""
    cached = _cached('sentiment', 3600)
    if cached: return cached
    result = {"index": 50, "label": "neutral", "source": "default"}
    try:
        import yfinance as yf
        vix = yf.Ticker("^VIX")
        h = vix.history(period="5d")
        if len(h) > 0:
            v = h.iloc[-1]['Close']
            if v < 15: idx, lbl = 80, "greedy"
            elif v < 20: idx, lbl = 65, "somewhat greedy"
            elif v < 25: idx, lbl = 50, "neutral"
            elif v < 30: idx, lbl = 35, "fear"
            else: idx, lbl = 20, "extreme fear"
            result = {"index": idx, "label": lbl, "vix": round(v,1), "source": "vix"}
        _save_cache('sentiment', result)
    except: pass
    return result

# ── 8. Economic Calendar ──
def economic_calendar(days=3):
    """Next major economic events dari ForexFactory mirror"""
    cached = _cached('calendar', 21600)
    if cached: return cached
    result = {"events": [], "next_event": None, "total": 0}
    try:
        import urllib.request, json
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        now = datetime.now()
        from datetime import timedelta
        cutoff = now + timedelta(days=days)
        upcoming = []
        for ev in data:
            try:
                ev_time = datetime.fromisoformat(ev.get('date', '').replace('Z','+00:00'))
                if now <= ev_time <= cutoff:
                    upcoming.append({
                        "title": ev.get('title', ev.get('event', '?')),
                        "country": ev.get('country', '?'),
                        "date": ev.get('date', '?'),
                        "impact": ev.get('impact', ev.get('importance', 'Low')),
                        "forecast": ev.get('forecast', ''),
                        "previous": ev.get('previous', ''),
                    })
            except: pass
        upcoming.sort(key=lambda x: x['date'])
        result = {"events": upcoming[:10], "next_event": upcoming[0] if upcoming else None, "total": len(upcoming)}
        _save_cache('calendar', result)
    except Exception as e:
        log.warning(f"Calendar error: {e}")
    return result

# ── 5. Composite Market Context ──
def market_context():
    """Gabungan semua indikator untuk adaptive decision"""
    dxy = get_dxy()
    fx = currency_strength()
    yld = get_yield()
    cot = get_cot()
    hd = get_hawkish_dovish()
    geo = get_geopolitics()
    cal = economic_calendar()
    sent = market_sentiment()
    
    # Regime inference
    dxy_trend = dxy.get("trend", "neutral")
    yield_trend = yld.get("trend", "neutral")
    cot_net = cot.get("net", 0)
    geo_score = geo.get("score", 30)
    
    # EURUSD bias: DXY naik = USD kuat = EUR lemah = bearish EURUSD
    if dxy_trend == "bull":
        eur_bias = "sell"  # DXY kuat → EURUSD turun
    elif dxy_trend == "bear":
        eur_bias = "buy"   # DXY lemah → EURUSD naik
    else:
        eur_bias = "neutral"
    
    return {
        "dxy": dxy,
        "yield_10y": yld,
        "cot": cot,
        "hawkish_dovish": hd,
        "geopolitics": geo,
        "economic_calendar": {"next_event": cal.get("next_event"), "total_events": cal.get("total", 0)},
        "sentiment": sent,
        "currency_strength": fx,
        "eurusd_bias": eur_bias,
        "regime": dxy_trend,
        "timestamp": datetime.now().isoformat(),
        "signal_modifier": 0.8 if eur_bias == "buy" else (0.5 if eur_bias == "sell" else 1.0),
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ctx = market_context()
    print(f"DXY: {ctx['dxy']['price']} ({ctx['dxy']['trend']})")
    print(f"EURUSD bias: {ctx['eurusd_bias']}")
    print(f"10Y Yield: {ctx['yield_10y']['yield']}% ({ctx['yield_10y']['trend']})")
    print(f"COT EURUSD: net={ctx['cot']['net']:,} (long={ctx['cot']['long']:,}, short={ctx['cot']['short']:,})")
    print(f"CB Sentiment: {ctx['hawkish_dovish']['overall']} (Fed={ctx['hawkish_dovish']['fed']['bias']})")
    print(f"Geopolitics: {ctx['geopolitics']['score']}/100 ({ctx['geopolitics']['label']})")
    print(f"FX strength: {ctx['currency_strength']}")
    nxt = ctx['economic_calendar']['next_event']
    if nxt:
        print(f"Next event: {nxt['title']} ({nxt['country']}) @ {nxt['impact']} impact")
    print(f"Sig modifier: {ctx['signal_modifier']}")
