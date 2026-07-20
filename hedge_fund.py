"""
Hedge Fund v3 — semua tools voting
"""
import sys, json, time, logging, threading, subprocess, csv, os
from pathlib import Path
from datetime import datetime, timedelta
import MetaTrader5 as mt5

SRC = Path(r'E:/trading')
LOG_FILE = SRC / 'data' / 'trades.csv'
VOTE_LOG = SRC / 'data' / 'votes.csv'
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
CREDS = {"login": 372044706, "password": os.environ.get("MT5_PASSWORD", "@15September"), "server": "ValetaxIntl-Live2"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('hf')

def connect(timeout=15):
    r = [False]
    def t(): r[0] = mt5.initialize()
    th = threading.Thread(target=t); th.daemon = True; th.start(); th.join(timeout)
    if th.is_alive(): return False
    return r[0]

def ensure_terminal():
    subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True)
    time.sleep(2)
    subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{CREDS['password']}", f"/server:{CREDS['server']}"])
    time.sleep(20)
    return mt5.initialize()

def calc_atr(symbol="EURUSD", period=14, tf=mt5.TIMEFRAME_M1):
    r = mt5.copy_rates_from_pos(symbol, tf, 0, period+2)
    if r is None or len(r) < period+1: return None
    trs = []
    for i in range(-period, 0):
        h,l,pc = r[i][2], r[i][3], r[i-1][4]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs)

# ── SIGNAL PROVIDERS ──
# Each returns {"bias":"buy"|"sell"|"neutral", "confidence":0-1, "source":"name"}

def signal_sma(symbol="EURUSD"):
    r = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
    if r is None or len(r) < 50: return {"bias":"neutral","confidence":0,"source":"sma"}
    c = [x[4] for x in r]
    s20,s50 = sum(c[-20:])/20, sum(c[-50:])/50
    if s20 > s50: return {"bias":"buy","confidence":0.6,"source":"sma"}
    if s20 < s50: return {"bias":"sell","confidence":0.6,"source":"sma"}
    return {"bias":"neutral","confidence":0,"source":"sma"}

def signal_aihf(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/ai-hedge-fund')
        from src.main import run_hedge_fund
        res = run_hedge_fund({"symbol": symbol})
        b = "neutral" if res.get("decision","hold")=="hold" else res["decision"]
        return {"bias":b,"confidence":res.get("confidence",0.5),"source":"aihf"}
    except Exception as e:
        log.warning(f"AIHF err: {e}")
        return {"bias":"neutral","confidence":0,"source":"aihf"}

def signal_hidden(symbol="EURUSD"):
    try:
        sys.path.insert(0, 'E:/hidden-regime')
        from hidden_regime import create_financial_pipeline
        p = create_financial_pipeline()
        res = p.run(symbol)
        m = {"bull":"buy","bear":"sell"}
        return {"bias":m.get(res.get("regime","neutral"),"neutral"),
                "confidence":res.get("confidence",0.3),"source":"hidden"}
    except Exception as e:
        log.warning(f"Hidden err: {e}")
        return {"bias":"neutral","confidence":0,"source":"hidden"}

def signal_tradingagents(symbol="EURUSD"):
    """TradingAgents — multi-agent decision via propagate()"""
    try:
        sys.path.insert(0, 'E:/tradingagents')
        from tradingagents.default_config import DEFAULT_CONFIG
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        # Butuh format tanggal. Gunakan hari ini.
        today = datetime.now().strftime("%Y-%m-%d")
        ta = TradingAgentsGraph(debug=False, config=DEFAULT_CONFIG.copy())
        _, decision = ta.propagate(symbol.replace("EURUSD","EURUSD=X"), today)
        # decision: {"action": "buy/sell/hold", "quantity": N}
        if isinstance(decision, dict):
            bias = decision.get("action","hold")
            if bias == "hold": bias = "neutral"
            return {"bias":bias,"confidence":0.5,"source":"tradingagents"}
        return {"bias":"neutral","confidence":0,"source":"tradingagents"}
    except Exception as e:
        log.warning(f"TradingAgents err: {e}")
        return {"bias":"neutral","confidence":0,"source":"tradingagents"}

def signal_aitrader(symbol="EURUSD"):
    """AI-Trader Node.js"""
    try:
        r = subprocess.run(["node","src/index.js",f"--symbol={symbol}"],
                          cwd="E:/AI-Trader",capture_output=True,text=True,timeout=15)
        out = r.stdout.lower()
        if "buy" in out: return {"bias":"buy","confidence":0.5,"source":"aitrader"}
        if "sell" in out: return {"bias":"sell","confidence":0.5,"source":"aitrader"}
    except: pass
    return {"bias":"neutral","confidence":0,"source":"aitrader"}

def signal_langalpha(symbol="EURUSD"):
    """LangAlpha research"""
    try:
        sys.path.insert(0, 'E:/LangAlpha')
        from ptc_cli.main import research
        res = research(symbol)
        if res and isinstance(res, dict):
            b = res.get("signal","neutral")
            if b == "hold": b = "neutral"
            return {"bias":b,"confidence":res.get("confidence",0.4),"source":"langalpha"}
    except: pass
    return {"bias":"neutral","confidence":0,"source":"langalpha"}

# ── HISTORICAL DATA ──
def get_historical_mt5(symbol="EURUSD", count=100, tf=mt5.TIMEFRAME_M15):
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None: return None
    import pandas as pd
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

def signal_wyckoff(symbol="EURUSD"):
    """Wyckoff Volume Spread — Sharpe 3.0"""
    try:
        import sys as _sys, pandas as _pd
        _sys.path.insert(0, str(SRC))
        from strategy_registry import WyckoffStrategy
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 60: return {"bias":"neutral","confidence":0,"source":"wyckoff"}
        strat = WyckoffStrategy(lookback=50, volume_mult=1.3)
        signals = strat.generate_signals(df)
        last = signals.iloc[-1]
        if last.get('entry',0) == 1:  return {"bias":"buy","confidence":0.65,"source":"wyckoff"}
        if last.get('entry',0) == -1: return {"bias":"sell","confidence":0.65,"source":"wyckoff"}
    except Exception as e:
        log.warning(f"Wyckoff err: {e}")
    return {"bias":"neutral","confidence":0,"source":"wyckoff"}

# ── AGGREGATOR ──
ALL_PROVIDERS = [
    signal_wyckoff,    # 🏆 Wyckoff Volume Spread (Sharpe 3.0)
]

def aggregate(symbol="EURUSD"):
    votes = []
    results = []
    for provider in ALL_PROVIDERS:
        try:
            v = provider(symbol)
            results.append(v)
            if v["bias"] != "neutral":
                votes.append(v)
                log.info(f"  ✅ {v['source']}: {v['bias']}")
            else:
                log.info(f"  ➖ {v['source']}: neutral")
        except Exception as e:
            log.warning(f"  ❌ {provider.__name__}: {e}")
    
    buys = sum(1 for v in votes if v["bias"] == "buy")
    sells = sum(1 for v in votes if v["bias"] == "sell")
    total = len(votes)
    
    log.info(f"  📊 Vote: {buys} buys / {sells} sells / {total} voters")
    
    # Log vote — check if file needs header BEFORE opening
    needs_header = not VOTE_LOG.exists() or VOTE_LOG.stat().st_size == 0
    with open(VOTE_LOG, 'a', newline='') as f:
        w = csv.writer(f)
        if needs_header:
            w.writerow(["time","symbol","buys","sells","total","providers","result"])
        provider_names = ",".join(v["source"] for v in votes)
        result = "buy" if buys > sells else "sell" if sells > buys else "neutral"
        w.writerow([datetime.now().isoformat(), symbol, buys, sells, total, provider_names, result])
    
    if buys > sells and buys >= 1:
        return {"bias":"buy","confidence":buys/total,"votes":votes}
    if sells > buys and sells >= 1:
        return {"bias":"sell","confidence":sells/total,"votes":votes}
    return {"bias":"neutral","confidence":0,"votes":votes}

# ── TRAILING ──
def trail_sl(pos, tf=mt5.TIMEFRAME_M1):
    rates = mt5.copy_rates_from_pos(pos.symbol, tf, 0, 15)
    if rates is None or len(rates) < 10: return None
    highs = [r[2] for r in rates[-10:]]; lows = [r[3] for r in rates[-10:]]
    if pos.type == 0 and max(highs[-5:]) > max(highs[:5]): return pos.price_open
    if pos.type == 1 and min(lows[-5:]) < min(lows[:5]): return pos.price_open
    return None

# ── Execute ──
def execute(sig):
    sym = "EURUSD"; t = mt5.symbol_info_tick(sym)
    
    # Dynamic lot sizing based on balance
    a = mt5.account_info()
    bal = a.balance if a else 1000
    # $100 → 0.01-0.02 | $200 → 0.02-0.03 | $500 → 0.05-0.10 | $1000 → 0.10-0.20
    lot_min = max(0.01, round(bal / 10000, 2))
    lot_max = max(0.02, round(bal / 5000, 2))
    lot = round(lot_min + (lot_max - lot_min) * sig.get("confidence", 0.5), 2)
    lot = min(lot, lot_max)  # cap
    log.info(f"   Balance=${bal:.0f} → Lot={lot} (range {lot_min}-{lot_max})")
    
    atr = calc_atr(sym) or 0.0010; sd = max(atr*2, 0.0010)
    if sig["bias"] == "buy":
        p,sl,tp,ot = t.ask, round(t.ask-sd,5), round(t.ask+sd*2,5), mt5.ORDER_TYPE_BUY
    else:
        p,sl,tp,ot = t.bid, round(t.bid+sd,5), round(t.bid-sd*2,5), mt5.ORDER_TYPE_SELL
    req = {"action":mt5.TRADE_ACTION_DEAL,"symbol":sym,"volume":lot,"type":ot,
           "price":p,"sl":sl,"tp":tp,"deviation":10,"magic":20260718,
           "comment":f"HFv3 {sig['bias']}","type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.ORDER_FILLING_IOC}
    res = mt5.order_send(req)
    if res and res.retcode == 10009:
        log.info(f"✅ {sig['bias'].upper()} {lot} {sym} @ {p:.5f} SL={sl} TP={tp}")
        with open(LOG_FILE, 'a', newline='') as f:
            w = csv.writer(f)
            if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
                w.writerow(["time","action","symbol","lot","price","sl","tp","atr","providers","result"])
            srcs = ",".join(v["source"] for v in sig.get("votes",[]))
            w.writerow([datetime.now().isoformat(), f"open_{sig['bias']}", sym, lot, p, sl, tp, round(atr,6), srcs, "executed"])
        return res.order
    log.warning(f"Order fail: {res.retcode if res else 'NONE'} {res.comment if res else ''}")
    return None

# ── MAIN ──
# ── GATE: Backtest required before execution ──
GATE_FILE = SRC / 'results' / 'gate_status.json'

def check_gate():
    """Cek apakah strategi lolos walk-forward gate"""
    import subprocess
    # Run backtest pipeline
    r = subprocess.run([sys.executable, str(SRC / 'backtest_pipeline.py')],
                       capture_output=True, text=True, timeout=120)
    # Parse result from stdout
    if '"pass": true' in r.stdout or '"pass": true' in r.stderr:
        return True
    # Check gate file
    if GATE_FILE.exists():
        data = json.loads(GATE_FILE.read_text())
        return data.get("pass", False)
    return False

def run_once():
    log.info("═══════════ Hedge Fund v3 — GATED ═══════════")
    
    # STEP 0: Connect MT5
    if not connect() and not ensure_terminal():
        log.error("MT5 unavailable"); return
    
    # STEP 1: Backtest gate (cache 24 jam)
    gate_cache = SRC / 'results' / 'gate_status.json'
    gate_pass = False
    if gate_cache.exists():
        age = time.time() - gate_cache.stat().st_mtime
        if age < 86400:  # < 24 jam
            gate_pass = json.loads(gate_cache.read_text()).get("pass", False)
    
    if not gate_pass:
        log.info("🔬 Running backtest + walk-forward...")
        import subprocess
        r = subprocess.run([sys.executable, str(SRC / 'backtest_pipeline.py')],
                          capture_output=True, text=True, timeout=120)
        gate_pass = '"pass": true' in (r.stdout + r.stderr)
    
    if not gate_pass:
        log.warning("❌ GATE TERTUTUP — Strategi gagal backtest/walk-forward")
        log.warning("   Tidak akan execute sampai strategi diperbaiki")
        mt5.shutdown(); return
    
    log.info("✅ GATE LULUS — Strategi siap eksekusi")
    try:
        a = mt5.account_info(); log.info(f"💰 ${a.balance:.2f}")
        pos = mt5.positions_get()
        if pos:
            for p in pos:
                log.info(f"📌 OPEN: {p.symbol} {'BUY' if p.type==0 else 'SELL'} PnL=${p.profit:.2f}")
                ns = trail_sl(p)
                if ns and (p.sl is None or abs(ns-p.sl) > 0.00001):
                    if p.type == 0 and ns > (p.sl or 0):
                        r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                        if r and r.retcode == 10009: log.info(f"  🔼 Trail→{ns:.5f}")
                    elif p.type == 1 and ns < (p.sl or 999):
                        r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                        if r and r.retcode == 10009: log.info(f"  🔽 Trail→{ns:.5f}")
        else:
            log.info("📊 Voting: Wyckoff Volume Spread Analysis")
            signal = aggregate()
            log.info(f"🏆 DECISION: {signal['bias']}")
            if signal["bias"] in ("buy","sell"):
                execute(signal)
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    run_once()
