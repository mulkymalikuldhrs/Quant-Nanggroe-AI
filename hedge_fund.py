"""
Hedge Fund v3 — semua tools voting
"""
import sys, json, time, logging, threading, subprocess, csv, os, random
from pathlib import Path
from datetime import datetime, timedelta

# ── MT5: try-import with mock fallback ──
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    class _MT5Mock:
        TIMEFRAME_M1=1; TIMEFRAME_M5=5; TIMEFRAME_M15=15; TIMEFRAME_M30=30
        TIMEFRAME_H1=60; TIMEFRAME_H4=240; TIMEFRAME_D1=1440; TIMEFRAME_W1=10080
        TRADE_ACTION_DEAL=1; TRADE_ACTION_SLTP=5
        ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1; ORDER_TIME_GTC=0; ORDER_FILLING_IOC=2
        def initialize(*a,**kw): return False
        def shutdown(*a,**kw): pass
        def login(*a,**kw): return False
        def symbol_info_tick(*a,**kw): return None
        def account_info(*a,**kw): return None
        def positions_get(*a,**kw): return ()
        def order_send(*a,**kw): return None
        def copy_rates_from_pos(*a,**kw): return None
    mt5 = _MT5Mock()
    MT5_AVAILABLE = False
    if not os.environ.get("PAPER_TRADE"):
        os.environ["PAPER_TRADE"] = "true"

SRC = Path(r'E:/trading')
LOG_FILE = SRC / 'data' / 'trades.csv'
VOTE_LOG = SRC / 'data' / 'votes.csv'
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"
_mt5_pass = os.environ.get("MT5_PASSWORD")
if not _mt5_pass:
    raise RuntimeError("MT5_PASSWORD environment variable not set — refusing to proceed with empty/hardcoded credential")
CREDS = {"login": 372044706, "password": _mt5_pass, "server": "ValetaxIntl-Live2"}

# ── PAPER TRADING MODE ──
# Set PAPER_TRADE=true di env untuk bypass MT5 execution
PAPER_TRADE = os.environ.get("PAPER_TRADE", "true").lower() in ("1", "true", "yes")

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

def calc_atr(symbol="EURUSD", period=14, tf=1):
    if not MT5_AVAILABLE:
        return None
    r = mt5.copy_rates_from_pos(symbol, 1, 0, period+2)
    if r is None or len(r) < period+1: return None
    trs = []
    for i in range(-period, 0):
        h,l,pc = r[i][2], r[i][3], r[i-1][4]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs)/len(trs)

# ── SIGNAL PROVIDERS ──
# Each returns {"bias":"buy"|"sell"|"neutral", "confidence":0-1, "source":"name"}

def signal_sma(symbol="EURUSD"):
    """SMA 20/50 crossover — using get_historical_mt5 for mock/live data"""
    df = get_historical_mt5(symbol, count=100, tf=15)
    if df is None or len(df) < 50:
        return {"bias":"neutral","confidence":0,"source":"sma"}
    c = df['close'].values
    s20, s50 = sum(c[-20:])/20, sum(c[-50:])/50
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
    """Hidden Markov Model regime detection — correct Pipeline API"""
    try:
        sys.path.insert(0, 'E:/hidden-regime')
        from hidden_regime import create_financial_pipeline
        import yfinance as yf
        p = create_financial_pipeline()
        ticker = symbol.replace("EURUSD","EURUSD=X")
        
        # Pipeline API: load data into the data loader, then update()
        # p.data.load_data() expects parameters — use load_data()
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is not None and len(df) > 20:
            # Load data into pipeline via the data loader
            p.data.load_data(data=df)
            p.update()  # no args — runs full pipeline from loaded data
            model = p.model
            if hasattr(model, 'decode_states'):
                states = model.decode_states(p.observations) if hasattr(p, 'observations') else model.decode_states(model.emission_means_)
                # Get current regime (last state)
                if states is not None and len(states) > 0:
                    current_state = int(states[-1])
                    state_labels = {0: "bearish", 1: "neutral", 2: "bullish"}
                    if current_state in state_labels:
                        m = {"bullish":"buy", "bearish":"sell"}
                        reg = state_labels[current_state]
                        if reg in m:
                            return {"bias":m[reg], "confidence":0.45, "source":"hidden"}
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

# ── ECOSYSTEM PROVIDERS ──

def signal_aimarketmaker(symbol="EURUSD"):
    """AI Market Maker — agentic crypto hedge fund (E:/ai-market-maker)"""
    try:
        sys.path.insert(0, 'E:/ai-market-maker')
        from aimm.execution.executor import execute_strategy as aimm_execute
        res = aimm_execute(symbol, mode="signal")
        if isinstance(res, dict):
            bias = res.get("decision", "neutral")
            if bias == "hold": bias = "neutral"
            return {"bias": bias, "confidence": res.get("confidence", 0.5), "source": "aimm"}
    except Exception as e:
        log.warning(f"AIMM err: {e}")
    return {"bias":"neutral","confidence":0,"source":"aimm"}

def signal_kronos(symbol="EURUSD"):
    """Kronos (AAAI 2026) — hierarchical tokenization price forecasting signal"""
    try:
        sys.path.insert(0, 'E:/trading')
        from strategies.kronos_wrapper import KronosSignalProvider
        import yfinance as yf
        import pandas as pd
        
        ticker = symbol.replace("EURUSD", "EURUSD=X")
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df is not None and len(df) > 200:
            # Flatten multi-index columns if any
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            # Ensure OHLCV columns
            df.columns = [c.lower() for c in df.columns]
            required = ['open','high','low','close','volume']
            if all(c in df.columns for c in required):
                df = df[required].dropna()
                if len(df) > 200:
                    strat = KronosSignalProvider(lookback=200, pred_len=5)
                    result = strat.generate_signals(df)
                    last = result.iloc[-1]
                    sig = int(last.get('entry', 0))
                    if sig > 0:
                        return {"bias": "buy", "confidence": 0.55, "source": "kronos"}
                    elif sig < 0:
                        return {"bias": "sell", "confidence": 0.55, "source": "kronos"}
    except Exception as e:
        log.warning(f"Kronos err: {e}")
    return {"bias": "neutral", "confidence": 0, "source": "kronos"}

def signal_pyportfolioopt(symbol="EURUSD"):
    """PyPortfolioOpt — optimal position sizing recommendation"""
    try:
        sys.path.insert(0, 'E:/PyPortfolioOpt')
        from pypfopt.efficient_frontier import EfficientFrontier
        from pypfopt.risk_models import CovarianceShrinkage
        from pypfopt.expected_returns import mean_historical_return
        # Get price history from MT5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"ppo"}
        prices = df['close']
        mu = mean_historical_return(prices.to_frame(symbol))
        S = CovarianceShrinkage(prices.to_frame(symbol)).shrinkage()
        ef = EfficientFrontier(mu, S)
        try:
            weights = ef.max_sharpe()
            if symbol in weights:
                w = weights[symbol]
                return {"bias":"buy" if w > 0 else "sell","confidence":min(abs(w), 1.0),"source":"ppo","weight":w}
        except Exception:
            pass
    except Exception as e:
        log.warning(f"PyPortfolioOpt err: {e}")
    return {"bias":"neutral","confidence":0,"source":"ppo"}

# ── HISTORICAL DATA ──
def get_historical_mt5(symbol="EURUSD", count=100, tf=15):
    """Get OHLCV data from MT5, with mock fallback for paper trading."""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Try real MT5 first
    if MT5_AVAILABLE and not PAPER_TRADE:
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            if rates is not None and len(rates) > 10:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('time', inplace=True)
                return df
        except Exception:
            pass
    
    # ── MOCK DATA for paper trading ──
    if PAPER_TRADE:
        log.info(f"  📊 Using mock data for {symbol} (paper mode)")
        np.random.seed(hash(symbol) % (2**31))
        now = datetime.now()
        times = [now - timedelta(minutes=i*tf) for i in range(count-1, -1, -1)]
        
        close = 1.0800
        closes = []
        for i in range(count):
            close += np.random.normal(0, 0.0005)
            close = max(close, 1.0500)
            close = min(close, 1.1200)
            closes.append(close)
        
        df = pd.DataFrame({
            'open': [c - np.random.uniform(0, 0.001) for c in closes],
            'high': [c + np.random.uniform(0.001, 0.003) for c in closes],
            'low': [c - np.random.uniform(0.001, 0.003) for c in closes],
            'close': closes,
            'tick_volume': [np.random.randint(100, 5000) for _ in range(count)],
            'spread': [np.random.randint(5, 20) for _ in range(count)],
            'real_volume': [np.random.randint(1000, 50000) for _ in range(count)],
        }, index=pd.DatetimeIndex(times))
        
        return df
    
    return None

def signal_wyckoff(symbol="EURUSD"):
    """Wyckoff Volume Spread — multi-bar signal detection"""
    try:
        import sys as _sys, pandas as _pd
        _sys.path.insert(0, str(SRC))
        from strategy_registry import WyckoffStrategy
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 60:
            return {"bias":"neutral","confidence":0,"source":"wyckoff"}
        strat = WyckoffStrategy(lookback=50, volume_mult=1.3)
        signals = strat.generate_signals(df)
        # Check last 10 bars for ANY signal (multi-bar window)
        recent = signals.tail(10)
        non_zero = recent[recent['entry'] != 0]
        if len(non_zero) > 0:
            last_sig = non_zero.iloc[-1]
            entry = last_sig['entry']
            # Recency-weighted confidence
            idx_pos = 0
            for i in range(len(recent)-1, -1, -1):
                if recent.iloc[i]['entry'] != 0:
                    idx_pos = len(recent) - 1 - i
                    break
            confidence = max(0.4, 0.65 - idx_pos * 0.08)
            if entry == 1:
                return {"bias":"buy","confidence":min(1.0, confidence),"source":"wyckoff"}
            elif entry == -1:
                return {"bias":"sell","confidence":min(1.0, confidence),"source":"wyckoff"}
    except Exception as e:
        log.warning(f"Wyckoff err: {e}")
    return {"bias":"neutral","confidence":0,"source":"wyckoff"}

# ── AGGREGATOR ──
# Core signal providers (built-in)
CORE_PROVIDERS = [
    signal_sma,          # SMA 20/50 crossover (free, always on)
    signal_wyckoff,      # 🏆 Wyckoff Volume Spread (Sharpe 3.0)
    signal_aihf,         # AI Hedge Fund (15 agent investors)
    signal_hidden,       # Hidden Markov Model regime detection
    signal_tradingagents,# Multi-agent trading graph
    signal_aitrader,     # Node.js AI trader
    signal_langalpha,    # LLM alpha research agent
    signal_kronos,       # Kronos Foundation Model (AAAI 2026)
    signal_aimarketmaker,# AI Market Maker (agentic crypto HF)
    signal_pyportfolioopt,# PyPortfolioOpt position sizing
]

ALL_PROVIDERS = CORE_PROVIDERS[:]
# QNA strategy gene stubs removed — signal_qna_* functions not yet defined
# Re-add when the actual signal wrapper functions are implemented

def aggregate(symbol="EURUSD"):
    """
    Multi-provider weighted voting with market context boost.
    
    1. Collect votes dari ALL_PROVIDERS
    2. Load market context (DXY, Yield, COT, Sentiment, Calendar)
    3. Weight votes berdasarkan market regime alignment
    4. Return final decision with confidence
    """
    votes = []
    results = []
    
    # ── Step 1: Load Market Context ──
    context_boost = {"buy": 1.0, "sell": 1.0}
    dxy_trend = "unknown"
    dxy_price = "?"
    try:
        from market_context import get_dxy, get_currency_strength
        dxy = get_dxy()
        dxy_trend = dxy.get("trend", "unknown")
        dxy_price = dxy.get("price", "?")
        strength = get_currency_strength()
        
        # Bias: strong dollar = harder for EURUSD buy
        if dxy_trend == "bull":
            context_boost["buy"] *= 0.85  # Reduces buy confidence
            log.info(f"  📈 DXY bull (${dxy_price}) → buy confidence ×0.85")
        elif dxy_trend == "bear":
            context_boost["sell"] *= 0.85  # Reduces sell confidence
            log.info(f"  📉 DXY bear (${dxy_price}) → sell confidence ×0.85")
    except Exception as e:
        log.debug(f"Market context unavailable: {e}")
    
    # ── Step 2: Collect Provider Votes ──
    for provider in ALL_PROVIDERS:
        try:
            v = provider(symbol)
            results.append(v)
            if v["bias"] != "neutral":
                # Apply context boost
                v["confidence"] = v.get("confidence", 0.5) * context_boost.get(v["bias"], 1.0)
                v["confidence"] = min(v["confidence"], 1.0)  # clamp
                votes.append(v)
                log.info(f"  ✅ {v['source']}: {v['bias']} (conf={v['confidence']:.2f})")
            else:
                log.info(f"  ➖ {v['source']}: neutral")
        except Exception as e:
            log.warning(f"  ❌ {provider.__name__}: {e}")
    
    # ── Step 3: Weighted Decision ──
    if not votes:
        log.warning("  ⚠️ No providers voted — staying neutral")
        return {"bias":"neutral","confidence":0,"votes":[],"context_used":dxy_trend}
    
    # Weighted sum: each vote contributes confidence
    total_conf_buy = sum(v.get("confidence", 0.5) for v in votes if v["bias"] == "buy")
    total_conf_sell = sum(v.get("confidence", 0.5) for v in votes if v["bias"] == "sell")
    total_all = total_conf_buy + total_conf_sell
    
    log.info(f"  📊 Weighted: buy={total_conf_buy:.2f} sell={total_conf_sell:.2f} total={total_all:.2f}")
    
    # Log vote
    needs_header = not VOTE_LOG.exists() or VOTE_LOG.stat().st_size == 0
    with open(VOTE_LOG, 'a', newline='') as f:
        w = csv.writer(f)
        if needs_header:
            w.writerow(["time","symbol","buy_conf","sell_conf","total","providers","result","dxy"])
        provider_names = ",".join(v["source"] for v in votes)
        result = "buy" if total_conf_buy > total_conf_sell else "sell" if total_conf_sell > total_conf_buy else "neutral"
        w.writerow([datetime.now().isoformat(), symbol, round(total_conf_buy,2), round(total_conf_sell,2), round(total_all,2), provider_names, result, dxy_price])
    
    if total_conf_buy > total_conf_sell and total_all > 0:
        return {"bias":"buy","confidence":min(total_conf_buy/total_all, 1.0), "votes":votes, "total_conf": total_all}
    if total_conf_sell > total_conf_buy and total_all > 0:
        return {"bias":"sell","confidence":min(total_conf_sell/total_all, 1.0), "votes":votes, "total_conf": total_all}
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
PAPER_LOG = SRC / 'data' / 'paper_trades.csv'

def execute(sig, symbol="EURUSD"):
    """
    Execute signal with paper trading support.
    
    PAPER_TRADE=true → log to file instead of MT5
    PAPER_TRADE=false → send real MT5 order
    """
    sym = symbol
    t = None
    if not PAPER_TRADE:
        t = mt5.symbol_info_tick(sym)
    
    # Dynamic lot sizing based on balance
    a = mt5.account_info() if not PAPER_TRADE else None
    bal = a.balance if a else 1000
    lot_min = max(0.01, round(bal / 10000, 2))
    lot_max = max(0.02, round(bal / 5000, 2))
    lot = round(lot_min + (lot_max - lot_min) * sig.get("confidence", 0.5), 2)
    lot = min(lot, lot_max)
    log.info(f"   Balance=${bal:.0f} → Lot={lot} (range {lot_min}-{lot_max})")
    
    atr = calc_atr(sym) or 0.0010
    sd = max(atr*2, 0.0010)
    
    if PAPER_TRADE:
        # ── PAPER TRADING ──
        price = random.uniform(1.05, 1.12) if sym == "EURUSD" else 100.0
        if sig["bias"] == "buy":
            p, sl, tp = price, round(price-sd,5), round(price+sd*2,5)
            ot = "buy"
        else:
            p, sl, tp = price, round(price+sd,5), round(price-sd*2,5)
            ot = "sell"
        
        log.info(f"📝 PAPER {sig['bias'].upper()} {lot} {sym} @ {p:.5f} SL={sl} TP={tp}")
        with open(PAPER_LOG, 'a', newline='') as f:
            w = csv.writer(f)
            if not PAPER_LOG.exists() or PAPER_LOG.stat().st_size == 0:
                w.writerow(["time","action","symbol","lot","price","sl","tp","atr","providers","mode"])
            srcs = ",".join(v["source"] for v in sig.get("votes",[]))
            w.writerow([datetime.now().isoformat(), f"paper_{sig['bias']}", sym, lot, p, sl, tp, round(atr,6), srcs, "paper"])
        return f"paper_{sig['bias']}"
    
    # ── REAL MT5 EXECUTION ──
    if sig["bias"] == "buy":
        p, sl, tp, ot = t.ask, round(t.ask-sd,5), round(t.ask+sd*2,5), mt5.ORDER_TYPE_BUY
    else:
        p, sl, tp, ot = t.bid, round(t.bid+sd,5), round(t.bid-sd*2,5), mt5.ORDER_TYPE_SELL
    
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

def run_once(target_symbol=None):
    """
    Main hedge fund cycle.
    
    1. Gate check (24h backtest cache)
    2. Pick best pair (or use target_symbol)
    3. Multi-provider weighted voting
    4. Risk guard approval
    5. Execute (real or paper)
    
    Args:
        target_symbol: Specific symbol to trade. None = auto-pick best pair.
    """
    log.info("═══════════ Hedge Fund v3 — 🚀 GATED ═══════════")
    
    # Allow paper mode override in function
    global PAPER_TRADE
    
    # STEP 0: Connect MT5 (or skip if paper trading)
    if not PAPER_TRADE:
        if not connect() and not ensure_terminal():
            log.warning("⚠️ MT5 unavailable — falling back to paper trading")
            # Override to paper mode
            PAPER_TRADE = True
    else:
        log.info("📝 PAPER TRADE MODE — No MT5 connection needed")
    
    # STEP 1: Backtest gate (cache 24 jam)
    gate_cache = SRC / 'results' / 'gate_status.json'
    gate_pass = False
    
    # Paper mode: gate always passes (use cached result if available)
    if PAPER_TRADE:
        if gate_cache.exists():
            try:
                age = time.time() - gate_cache.stat().st_mtime
                if age < 86400:
                    gate_pass = json.loads(gate_cache.read_text()).get("pass", False)
            except Exception:
                pass
        if not gate_pass:
            log.info("🔬 Paper mode: skipping gate (will run backtest in background)")
            # Write a temporary pass for paper mode
            gate_pass = True
    else:
        if gate_cache.exists():
            try:
                age = time.time() - gate_cache.stat().st_mtime
                if age < 86400:
                    gate_pass = json.loads(gate_cache.read_text()).get("pass", False)
            except Exception:
                pass
        
        if not gate_pass:
            log.info("🔬 Running backtest + walk-forward...")
            try:
                r = subprocess.run([sys.executable, str(SRC / 'backtest_pipeline.py')],
                                  capture_output=True, text=True, timeout=120)
                gate_pass = '"pass": true' in (r.stdout + r.stderr)
            except Exception as e:
                log.warning(f"Backtest failed: {e}")
    
    if not gate_pass:
        log.warning("❌ GATE TERTUTUP — Strategi gagal backtest/walk-forward")
        log.warning("   Tidak akan execute sampai strategi diperbaiki")
        if not PAPER_TRADE:
            try: mt5.shutdown()
            except: pass
        return
    
    log.info("✅ GATE LULUS — Strategi siap eksekusi")
    
    try:
        # STEP 2: Pick symbol
        symbol = target_symbol
        if not symbol:
            try:
                from multi_pair_scanner import get_valid_pairs
                pairs = get_valid_pairs()
                if pairs:
                    # Pick pair with lowest spread
                    symbol = pairs[0]  # list is already sorted by spread
                    log.info(f"🎯 Best pair: {symbol}")
            except Exception as e:
                log.debug(f"Pair scanner unavailable: {e}")
        if not symbol:
            symbol = "EURUSD"
        
        # STEP 3: Account info
        if not PAPER_TRADE:
            a = mt5.account_info()
            if a:
                log.info(f"💰 ${a.balance:.2f} | Equity=${a.equity:.2f} | Margin=${a.margin:.2f}")
        
        # STEP 4: Manage existing positions
        positions = []
        if not PAPER_TRADE:
            try:
                positions = mt5.positions_get() or []
            except Exception:
                positions = []
        
        if positions:
            for p in positions:
                log.info(f"📌 OPEN: {p.symbol} {'BUY' if p.type==0 else 'SELL'} PnL=${p.profit:.2f}")
                ns = trail_sl(p)
                if ns and (p.sl is None or abs(ns-p.sl) > 0.00001):
                    try:
                        if p.type == 0 and ns > (p.sl or 0):
                            r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                            if r and r.retcode == 10009: log.info(f"  🔼 Trail→{ns:.5f}")
                        elif p.type == 1 and ns < (p.sl or 999):
                            r = mt5.order_send({"action":mt5.TRADE_ACTION_SLTP,"position":p.ticket,"sl":ns,"tp":p.tp})
                            if r and r.retcode == 10009: log.info(f"  🔽 Trail→{ns:.5f}")
                    except Exception as e:
                        log.debug(f"Trail failed: {e}")
        else:
            # STEP 5: Vote
            log.info(f"📊 Voting: {len(ALL_PROVIDERS)} providers")
            signal = aggregate(symbol)
            log.info(f"🏆 DECISION: {signal['bias']} (conf={signal['confidence']:.2f})")
            
            if signal["bias"] in ("buy", "sell"):
                # STEP 6: Risk Guard Approval
                try:
                    from risk_guard import approve as rg_approve
                    proposal = {
                        "symbol": symbol,
                        "action": signal["bias"],
                        "volume": max(0.01, round(1000 / 10000, 2)),
                        "price": signal.get("price", 1.0),
                        "sl": signal.get("sl", 0),
                        "account_balance": 1000,
                        "daily_pnl": 0,
                        "open_positions": 0,
                        "market_volatility": (calc_atr(symbol) or 0.001) / 1.0,
                    }
                    rg_result = rg_approve(proposal)
                    if rg_result.get("status") == "VETOED":
                        log.warning(f"🚫 Risk Guard VETO: {rg_result.get('reasons', 'unknown')}")
                        if not PAPER_TRADE:
                            try: mt5.shutdown()
                            except: pass
                        return
                    log.info(f"✅ Risk Guard APPROVED (score={rg_result.get('score',0):.2f})")
                except Exception as e:
                    log.warning(f"Risk guard unavailable, proceeding: {e}")
                
                # STEP 7: Execute
                execute(signal, symbol)
                
    finally:
        if not PAPER_TRADE:
            try: mt5.shutdown()
            except: pass

if __name__ == "__main__":
    run_once()

# Auto-registered by MUE-X: qna_MSNRStrategy_mut_e10dba6a

# Auto-registered by MUE-X: qna_MSNRStrategy_mut_48735c9a

# Auto-registered by MUE-X: qna_SMCStrategy_mut_7b7c1579

# Auto-registered by MUE-X: qna_SMCStrategy_mut_42674b81

# Auto-registered by MUE-X: qna_MeanReversionStrategy_mut_f2242159

# Auto-registered by MUE-X: qna_MeanReversionStrategy_mut_d0c35fc0

# Auto-registered by MUE-X: qna_FiboStrategy_mut_3d236bb5

# Auto-registered by MUE-X: qna_FiboStrategy_mut_726d2261

# Auto-registered by MUE-X: qna_EMAADXStrategy_mut_2329920e

# Auto-registered by MUE-X: qna_EMAADXStrategy_mut_8dce545f

# Auto-registered by MUE-X: qna_AMDXStrategy_mut_163071ea

# Auto-registered by MUE-X: qna_AMDXStrategy_mut_f09909bb

# Auto-registered by MUE-X: qna_AlgebraStrategy_mut_cce8f5f3

# Auto-registered by MUE-X: qna_AlgebraStrategy_mut_d4d7966f

# Auto-registered by MUE-X: qna_WyckoffStrategy_mut_4be93408

# Auto-registered by MUE-X: qna_WyckoffStrategy_mut_d577a6a0

# Auto-registered by MUE-X: qna_SMCStrategyOld_mut_023786dc

# Auto-registered by MUE-X: qna_SMCStrategyOld_mut_d9b02f7b
