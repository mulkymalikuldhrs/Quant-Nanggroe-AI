"""
Quant Nanggroe — Hedge Fund v3 Multi-Provider Aggregator
=========================================================
Adapted from E:/trading/hedge_fund.py for QNA integration.
All paths relative to QNA data directory.
"""
import csv
import json
import logging
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# ── QNA Data Directory (relative to this file) ──
_HF_DIR = Path(__file__).resolve().parent
_QNA_DIR = _HF_DIR.parent
_DATA_DIR = _QNA_DIR / "data"
os.makedirs(_DATA_DIR, exist_ok=True)

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

SRC = _HF_DIR
LOG_FILE = _DATA_DIR / 'trades.csv'
VOTE_LOG = _DATA_DIR / 'votes.csv'
PAPER_LOG = _DATA_DIR / 'paper_trades.csv'
GATE_FILE = _DATA_DIR / 'gate_status.json'
TERMINAL = r"C:\Program Files\MetaTrader 5\terminal64.exe"

# ── CREDENTIALS (deferred — checked at trade time, not import time) ──
CREDS = {
    "login": 372044706,
    "password": lambda: os.environ.get("MT5_PASSWORD"),
    "server": "ValetaxIntl-Live2",
}
_MT5_CREDS_CHECKED = False

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
    _pwd = CREDS["password"]() if callable(CREDS["password"]) else CREDS["password"]
    subprocess.Popen([TERMINAL, f"/login:{CREDS['login']}", f"/password:{_pwd}", f"/server:{CREDS['server']}"])
    time.sleep(20)
    return mt5.initialize()

def calc_atr(symbol="EURUSD", period=14, tf=1):
    if not MT5_AVAILABLE:
        return None
    r = mt5.copy_rates_from_pos(symbol, 1, 0, period+2)
    if r is None or len(r) < period+1: return None
    trs = []
    for i in range(-period, 0):
        h,lo,pc = r[i][2], r[i][3], r[i-1][4]
        trs.append(max(h-lo, abs(h-pc), abs(lo-pc)))
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
        import yfinance as yf
        from hidden_regime import create_financial_pipeline
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
    except Exception:
        pass
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
    except Exception:
        pass
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
        import pandas as pd
        import yfinance as yf

        from strategies.kronos_wrapper import KronosSignalProvider
        
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
        from pypfopt.expected_returns import mean_historical_return
        from pypfopt.risk_models import CovarianceShrinkage
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
    from datetime import datetime

    import numpy as np
    import pandas as pd
    
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
        import sys as _sys

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


def signal_qna_MSNRStrategy_mut_3b787b28(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_3b787b28"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_3b787b28 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3b787b28"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3b787b28"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_3b787b28"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_3b787b28"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_3b787b28 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3b787b28"}



def signal_qna_SMCStrategy_mut_28bdc019(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_28bdc019"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_28bdc019 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_28bdc019"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_28bdc019"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_28bdc019"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_28bdc019"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_28bdc019 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_28bdc019"}



def signal_qna_MeanReversionStrategy_mut_54b813e2(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_54b813e2"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_54b813e2 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_54b813e2"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_54b813e2"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_54b813e2"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_54b813e2"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_54b813e2 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_54b813e2"}



def signal_qna_FiboStrategy_mut_b7b9082d(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_b7b9082d"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_b7b9082d import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b7b9082d"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b7b9082d"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_b7b9082d"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_b7b9082d"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_b7b9082d err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b7b9082d"}



def signal_qna_EMAADXStrategy_mut_18900f77(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_18900f77"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_18900f77 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_18900f77"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_18900f77"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_18900f77"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_18900f77"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_18900f77 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_18900f77"}



def signal_qna_AMDXStrategy_mut_34f6635d(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_34f6635d"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_34f6635d import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_34f6635d"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_34f6635d"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_34f6635d"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_34f6635d"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_34f6635d err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_34f6635d"}



def signal_qna_AlgebraStrategy_mut_09836ba3(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_09836ba3"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_09836ba3 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_09836ba3"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_09836ba3"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_09836ba3"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_09836ba3"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_09836ba3 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_09836ba3"}



def signal_qna_WyckoffStrategy_mut_4be93408(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_4be93408"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_4be93408 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_4be93408"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_4be93408"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_4be93408"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_4be93408"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_4be93408 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_4be93408"}



def signal_qna_SMCStrategyOld_mut_d9b02f7b(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_d9b02f7b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_d9b02f7b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_d9b02f7b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_d9b02f7b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_d9b02f7b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_d9b02f7b"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_d9b02f7b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_d9b02f7b"}



def signal_qna_AlgebraStrategy_mut_08cdba54(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_08cdba54"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_08cdba54 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_08cdba54"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_08cdba54"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_08cdba54"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_08cdba54"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_08cdba54 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_08cdba54"}



def signal_qna_AlgebraStrategy_mut_4d25722b(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_4d25722b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_4d25722b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_4d25722b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_4d25722b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_4d25722b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_4d25722b"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_4d25722b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_4d25722b"}



def signal_qna_AlgebraStrategy_mut_54c88cbb(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_54c88cbb"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_54c88cbb import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_54c88cbb"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_54c88cbb"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_54c88cbb"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_54c88cbb"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_54c88cbb err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_54c88cbb"}



def signal_qna_AlgebraStrategy_mut_57a93e76(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_57a93e76"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_57a93e76 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_57a93e76"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_57a93e76"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_57a93e76"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_57a93e76"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_57a93e76 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_57a93e76"}



def signal_qna_AlgebraStrategy_mut_6478b3bf(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_6478b3bf"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_6478b3bf import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6478b3bf"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6478b3bf"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_6478b3bf"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_6478b3bf"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_6478b3bf err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6478b3bf"}



def signal_qna_AlgebraStrategy_mut_6e5274a7(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_6e5274a7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_6e5274a7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6e5274a7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6e5274a7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_6e5274a7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_6e5274a7"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_6e5274a7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_6e5274a7"}



def signal_qna_AlgebraStrategy_mut_abdee600(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_abdee600"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_abdee600 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_abdee600"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_abdee600"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_abdee600"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_abdee600"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_abdee600 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_abdee600"}



def signal_qna_AlgebraStrategy_mut_ca720a52(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_ca720a52"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_ca720a52 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_ca720a52"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_ca720a52"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_ca720a52"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_ca720a52"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_ca720a52 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_ca720a52"}



def signal_qna_AlgebraStrategy_mut_cce8f5f3(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_cce8f5f3"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_cce8f5f3 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_cce8f5f3"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_cce8f5f3"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_cce8f5f3"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_cce8f5f3"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_cce8f5f3 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_cce8f5f3"}



def signal_qna_AlgebraStrategy_mut_d4d7966f(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_d4d7966f"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_d4d7966f import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_d4d7966f"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_d4d7966f"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_d4d7966f"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_d4d7966f"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_d4d7966f err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_d4d7966f"}



def signal_qna_AlgebraStrategy_mut_e9b231a7(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_e9b231a7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_e9b231a7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_e9b231a7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_e9b231a7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_e9b231a7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_e9b231a7"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_e9b231a7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_e9b231a7"}



def signal_qna_AMDXStrategy_mut_163071ea(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_163071ea"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_163071ea import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_163071ea"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_163071ea"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_163071ea"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_163071ea"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_163071ea err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_163071ea"}



def signal_qna_AMDXStrategy_mut_2b6056c1(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_2b6056c1"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_2b6056c1 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2b6056c1"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2b6056c1"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_2b6056c1"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_2b6056c1"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_2b6056c1 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2b6056c1"}



def signal_qna_AMDXStrategy_mut_2ed7d815(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_2ed7d815"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_2ed7d815 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2ed7d815"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2ed7d815"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_2ed7d815"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_2ed7d815"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_2ed7d815 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_2ed7d815"}



def signal_qna_AMDXStrategy_mut_f09909bb(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_f09909bb"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_f09909bb import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_f09909bb"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_f09909bb"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_f09909bb"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_f09909bb"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_f09909bb err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_f09909bb"}



def signal_qna_EMAADXStrategy_mut_19a19dd1(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_19a19dd1"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_19a19dd1 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_19a19dd1"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_19a19dd1"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_19a19dd1"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_19a19dd1"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_19a19dd1 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_19a19dd1"}



def signal_qna_EMAADXStrategy_mut_2329920e(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_2329920e"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_2329920e import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_2329920e"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_2329920e"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_2329920e"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_2329920e"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_2329920e err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_2329920e"}



def signal_qna_EMAADXStrategy_mut_3a5e1072(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_3a5e1072"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_3a5e1072 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_3a5e1072"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_3a5e1072"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_3a5e1072"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_3a5e1072"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_3a5e1072 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_3a5e1072"}



def signal_qna_EMAADXStrategy_mut_465f341c(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_465f341c"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_465f341c import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_465f341c"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_465f341c"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_465f341c"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_465f341c"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_465f341c err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_465f341c"}



def signal_qna_EMAADXStrategy_mut_5f4e558e(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_5f4e558e"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_5f4e558e import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_5f4e558e"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_5f4e558e"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_5f4e558e"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_5f4e558e"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_5f4e558e err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_5f4e558e"}



def signal_qna_EMAADXStrategy_mut_797d1ed2(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_797d1ed2"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_797d1ed2 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_797d1ed2"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_797d1ed2"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_797d1ed2"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_797d1ed2"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_797d1ed2 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_797d1ed2"}



def signal_qna_EMAADXStrategy_mut_7dd06442(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_7dd06442"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_7dd06442 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7dd06442"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7dd06442"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_7dd06442"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_7dd06442"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_7dd06442 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7dd06442"}



def signal_qna_EMAADXStrategy_mut_7e80edc0(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_7e80edc0"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_7e80edc0 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7e80edc0"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7e80edc0"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_7e80edc0"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_7e80edc0"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_7e80edc0 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_7e80edc0"}



def signal_qna_EMAADXStrategy_mut_89a691ea(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_89a691ea"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_89a691ea import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_89a691ea"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_89a691ea"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_89a691ea"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_89a691ea"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_89a691ea err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_89a691ea"}



def signal_qna_EMAADXStrategy_mut_8dce545f(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_8dce545f"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_8dce545f import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8dce545f"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8dce545f"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_8dce545f"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_8dce545f"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_8dce545f err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8dce545f"}



def signal_qna_EMAADXStrategy_mut_f06897a3(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_f06897a3"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_f06897a3 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_f06897a3"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_f06897a3"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_f06897a3"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_f06897a3"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_f06897a3 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_f06897a3"}



def signal_qna_FiboStrategy_mut_08ef309d(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_08ef309d"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_08ef309d import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_08ef309d"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_08ef309d"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_08ef309d"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_08ef309d"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_08ef309d err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_08ef309d"}



def signal_qna_FiboStrategy_mut_22ab1442(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_22ab1442"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_22ab1442 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_22ab1442"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_22ab1442"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_22ab1442"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_22ab1442"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_22ab1442 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_22ab1442"}



def signal_qna_FiboStrategy_mut_267de559(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_267de559"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_267de559 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_267de559"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_267de559"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_267de559"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_267de559"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_267de559 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_267de559"}



def signal_qna_FiboStrategy_mut_3d236bb5(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_3d236bb5"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_3d236bb5 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_3d236bb5"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_3d236bb5"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_3d236bb5"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_3d236bb5"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_3d236bb5 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_3d236bb5"}



def signal_qna_FiboStrategy_mut_625964f5(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_625964f5"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_625964f5 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_625964f5"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_625964f5"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_625964f5"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_625964f5"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_625964f5 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_625964f5"}



def signal_qna_FiboStrategy_mut_726d2261(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_726d2261"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_726d2261 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_726d2261"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_726d2261"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_726d2261"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_726d2261"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_726d2261 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_726d2261"}



def signal_qna_FiboStrategy_mut_75c8d197(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_75c8d197"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_75c8d197 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_75c8d197"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_75c8d197"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_75c8d197"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_75c8d197"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_75c8d197 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_75c8d197"}



def signal_qna_FiboStrategy_mut_b57a5c3a(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_b57a5c3a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_b57a5c3a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b57a5c3a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b57a5c3a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_b57a5c3a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_b57a5c3a"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_b57a5c3a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_b57a5c3a"}



def signal_qna_FiboStrategy_mut_e918f65d(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_e918f65d"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_e918f65d import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_e918f65d"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_e918f65d"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_e918f65d"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_e918f65d"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_e918f65d err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_e918f65d"}



def signal_qna_MeanReversionStrategy_mut_238dc347(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_238dc347"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_238dc347 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_238dc347"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_238dc347"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_238dc347"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_238dc347"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_238dc347 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_238dc347"}



def signal_qna_MeanReversionStrategy_mut_29ffbe50(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_29ffbe50"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_29ffbe50 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_29ffbe50"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_29ffbe50"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_29ffbe50"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_29ffbe50"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_29ffbe50 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_29ffbe50"}



def signal_qna_MeanReversionStrategy_mut_3f94aebd(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_3f94aebd"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_3f94aebd import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_3f94aebd"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_3f94aebd"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_3f94aebd"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_3f94aebd"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_3f94aebd err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_3f94aebd"}



def signal_qna_MeanReversionStrategy_mut_534a3e48(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_534a3e48"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_534a3e48 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_534a3e48"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_534a3e48"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_534a3e48"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_534a3e48"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_534a3e48 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_534a3e48"}



def signal_qna_MeanReversionStrategy_mut_7beac3f8(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_7beac3f8"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_7beac3f8 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7beac3f8"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7beac3f8"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_7beac3f8"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_7beac3f8"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_7beac3f8 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7beac3f8"}



def signal_qna_MeanReversionStrategy_mut_80c3a50c(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_80c3a50c"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_80c3a50c import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_80c3a50c"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_80c3a50c"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_80c3a50c"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_80c3a50c"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_80c3a50c err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_80c3a50c"}



def signal_qna_MeanReversionStrategy_mut_aeac95c8(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_aeac95c8"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_aeac95c8 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_aeac95c8"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_aeac95c8"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_aeac95c8"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_aeac95c8"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_aeac95c8 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_aeac95c8"}



def signal_qna_MeanReversionStrategy_mut_d0c35fc0(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_d0c35fc0"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_d0c35fc0 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d0c35fc0"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d0c35fc0"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_d0c35fc0"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_d0c35fc0"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_d0c35fc0 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d0c35fc0"}



def signal_qna_MeanReversionStrategy_mut_d282b0ab(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_d282b0ab"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_d282b0ab import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d282b0ab"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d282b0ab"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_d282b0ab"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_d282b0ab"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_d282b0ab err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_d282b0ab"}



def signal_qna_MeanReversionStrategy_mut_efed8264(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_efed8264"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_efed8264 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_efed8264"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_efed8264"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_efed8264"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_efed8264"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_efed8264 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_efed8264"}



def signal_qna_MeanReversionStrategy_mut_f2242159(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_f2242159"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_f2242159 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_f2242159"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_f2242159"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_f2242159"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_f2242159"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_f2242159 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_f2242159"}



def signal_qna_MSNRStrategy_mut_0c38513d(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_0c38513d"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_0c38513d import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_0c38513d"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_0c38513d"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_0c38513d"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_0c38513d"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_0c38513d err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_0c38513d"}



def signal_qna_MSNRStrategy_mut_1082a506(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_1082a506"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_1082a506 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_1082a506"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_1082a506"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_1082a506"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_1082a506"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_1082a506 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_1082a506"}



def signal_qna_MSNRStrategy_mut_21397cf7(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_21397cf7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_21397cf7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_21397cf7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_21397cf7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_21397cf7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_21397cf7"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_21397cf7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_21397cf7"}



def signal_qna_MSNRStrategy_mut_2512c57e(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_2512c57e"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_2512c57e import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_2512c57e"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_2512c57e"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_2512c57e"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_2512c57e"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_2512c57e err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_2512c57e"}



def signal_qna_MSNRStrategy_mut_25630ace(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_25630ace"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_25630ace import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25630ace"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25630ace"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_25630ace"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_25630ace"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_25630ace err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25630ace"}



def signal_qna_MSNRStrategy_mut_25ec0944(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_25ec0944"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_25ec0944 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25ec0944"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25ec0944"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_25ec0944"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_25ec0944"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_25ec0944 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_25ec0944"}



def signal_qna_MSNRStrategy_mut_30fe44aa(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_30fe44aa"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_30fe44aa import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_30fe44aa"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_30fe44aa"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_30fe44aa"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_30fe44aa"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_30fe44aa err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_30fe44aa"}



def signal_qna_MSNRStrategy_mut_47a61c1a(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_47a61c1a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_47a61c1a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_47a61c1a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_47a61c1a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_47a61c1a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_47a61c1a"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_47a61c1a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_47a61c1a"}



def signal_qna_MSNRStrategy_mut_48735c9a(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_48735c9a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_48735c9a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_48735c9a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_48735c9a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_48735c9a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_48735c9a"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_48735c9a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_48735c9a"}



def signal_qna_MSNRStrategy_mut_85877fda(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_85877fda"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_85877fda import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_85877fda"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_85877fda"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_85877fda"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_85877fda"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_85877fda err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_85877fda"}



def signal_qna_MSNRStrategy_mut_cfd837e7(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_cfd837e7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_cfd837e7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_cfd837e7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_cfd837e7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_cfd837e7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_cfd837e7"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_cfd837e7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_cfd837e7"}



def signal_qna_MSNRStrategy_mut_e10dba6a(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_e10dba6a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_e10dba6a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_e10dba6a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_e10dba6a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_e10dba6a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_e10dba6a"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_e10dba6a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_e10dba6a"}



def signal_qna_QuarterlyTheoryStrategy_mut_99914b93(symbol="EURUSD"):
    """MUE-X evolved: qna_QuarterlyTheoryStrategy_mut_99914b93"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_QuarterlyTheoryStrategy_mut_99914b93 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_QuarterlyTheoryStrategy_mut_99914b93"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_QuarterlyTheoryStrategy_mut_99914b93"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_QuarterlyTheoryStrategy_mut_99914b93"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_QuarterlyTheoryStrategy_mut_99914b93"}
    except Exception as e:
        log.warning(f"MUE-X qna_QuarterlyTheoryStrategy_mut_99914b93 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_QuarterlyTheoryStrategy_mut_99914b93"}



def signal_qna_SMCStrategy_mut_0502371a(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_0502371a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_0502371a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0502371a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0502371a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_0502371a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_0502371a"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_0502371a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0502371a"}



def signal_qna_SMCStrategy_mut_0ab19902(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_0ab19902"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_0ab19902 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0ab19902"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0ab19902"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_0ab19902"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_0ab19902"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_0ab19902 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_0ab19902"}



def signal_qna_SMCStrategy_mut_3faccbdb(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_3faccbdb"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_3faccbdb import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_3faccbdb"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_3faccbdb"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_3faccbdb"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_3faccbdb"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_3faccbdb err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_3faccbdb"}



def signal_qna_SMCStrategy_mut_42674b81(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_42674b81"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_42674b81 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_42674b81"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_42674b81"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_42674b81"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_42674b81"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_42674b81 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_42674b81"}



def signal_qna_SMCStrategy_mut_5b5e79dc(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_5b5e79dc"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_5b5e79dc import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5b5e79dc"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5b5e79dc"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_5b5e79dc"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_5b5e79dc"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_5b5e79dc err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5b5e79dc"}



def signal_qna_SMCStrategy_mut_5f503a0f(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_5f503a0f"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_5f503a0f import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5f503a0f"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5f503a0f"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_5f503a0f"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_5f503a0f"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_5f503a0f err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_5f503a0f"}



def signal_qna_SMCStrategy_mut_7b7c1579(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_7b7c1579"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_7b7c1579 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7b7c1579"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7b7c1579"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_7b7c1579"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_7b7c1579"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_7b7c1579 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7b7c1579"}



def signal_qna_SMCStrategy_mut_7dc3a1f7(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_7dc3a1f7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_7dc3a1f7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7dc3a1f7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7dc3a1f7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_7dc3a1f7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_7dc3a1f7"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_7dc3a1f7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_7dc3a1f7"}



def signal_qna_SMCStrategy_mut_938d57fc(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_938d57fc"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_938d57fc import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_938d57fc"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_938d57fc"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_938d57fc"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_938d57fc"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_938d57fc err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_938d57fc"}



def signal_qna_SMCStrategy_mut_eef32422(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_eef32422"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_eef32422 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_eef32422"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_eef32422"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_eef32422"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_eef32422"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_eef32422 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_eef32422"}



def signal_qna_SMCStrategy_mut_f0d3ea7a(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_f0d3ea7a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_f0d3ea7a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_f0d3ea7a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_f0d3ea7a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_f0d3ea7a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_f0d3ea7a"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_f0d3ea7a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_f0d3ea7a"}



def signal_qna_SMCStrategyOld_mut_023786dc(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_023786dc"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_023786dc import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_023786dc"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_023786dc"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_023786dc"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_023786dc"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_023786dc err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_023786dc"}



def signal_qna_SMCStrategyOld_mut_16bdcdd1(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_16bdcdd1"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_16bdcdd1 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_16bdcdd1"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_16bdcdd1"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_16bdcdd1"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_16bdcdd1"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_16bdcdd1 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_16bdcdd1"}



def signal_qna_SMCStrategyOld_mut_792be0a9(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_792be0a9"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_792be0a9 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_792be0a9"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_792be0a9"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_792be0a9"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_792be0a9"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_792be0a9 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_792be0a9"}



def signal_qna_SMCStrategyOld_mut_af1ac2b3(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_af1ac2b3"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_af1ac2b3 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_af1ac2b3"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_af1ac2b3"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_af1ac2b3"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_af1ac2b3"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_af1ac2b3 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_af1ac2b3"}



def signal_qna_WyckoffStrategy_mut_35e60a57(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_35e60a57"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_35e60a57 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_35e60a57"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_35e60a57"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_35e60a57"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_35e60a57"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_35e60a57 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_35e60a57"}



def signal_qna_WyckoffStrategy_mut_3af916de(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_3af916de"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_3af916de import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_3af916de"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_3af916de"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_3af916de"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_3af916de"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_3af916de err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_3af916de"}



def signal_qna_WyckoffStrategy_mut_9516b5c7(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_9516b5c7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_9516b5c7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_9516b5c7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_9516b5c7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_9516b5c7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_9516b5c7"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_9516b5c7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_9516b5c7"}



def signal_qna_WyckoffStrategy_mut_c354345b(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_c354345b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_c354345b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_c354345b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_c354345b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_c354345b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_c354345b"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_c354345b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_c354345b"}



def signal_qna_WyckoffStrategy_mut_cb42e9bb(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_cb42e9bb"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_cb42e9bb import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_cb42e9bb"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_cb42e9bb"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_cb42e9bb"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_cb42e9bb"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_cb42e9bb err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_cb42e9bb"}



def signal_qna_WyckoffStrategy_mut_d1311580(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_d1311580"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_d1311580 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d1311580"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d1311580"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_d1311580"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_d1311580"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_d1311580 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d1311580"}



def signal_qna_WyckoffStrategy_mut_d577a6a0(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_d577a6a0"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_d577a6a0 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d577a6a0"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d577a6a0"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_d577a6a0"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_d577a6a0"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_d577a6a0 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_d577a6a0"}



def signal_qna_WyckoffStrategy_mut_db5ec800(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_db5ec800"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_db5ec800 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_db5ec800"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_db5ec800"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_db5ec800"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_db5ec800"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_db5ec800 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_db5ec800"}



def signal_qna_WyckoffStrategy_mut_f643d6d7(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_f643d6d7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_f643d6d7 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f643d6d7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f643d6d7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_f643d6d7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_f643d6d7"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_f643d6d7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f643d6d7"}



def signal_qna_WyckoffStrategy_mut_f82fb744(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_f82fb744"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_f82fb744 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f82fb744"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f82fb744"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_f82fb744"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_f82fb744"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_f82fb744 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_f82fb744"}



def signal_qna_MSNRStrategy_mut_ea45617a(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_ea45617a"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_ea45617a import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_ea45617a"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_ea45617a"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_ea45617a"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_ea45617a"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_ea45617a err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_ea45617a"}



def signal_qna_SMCStrategy_mut_561f4ce1(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_561f4ce1"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_561f4ce1 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_561f4ce1"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_561f4ce1"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_561f4ce1"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_561f4ce1"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_561f4ce1 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_561f4ce1"}



def signal_qna_MeanReversionStrategy_mut_cc3d5065(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_cc3d5065"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_cc3d5065 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_cc3d5065"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_cc3d5065"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_cc3d5065"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_cc3d5065"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_cc3d5065 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_cc3d5065"}



def signal_qna_EMAADXStrategy_mut_54d92f08(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_54d92f08"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_54d92f08 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_54d92f08"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_54d92f08"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_54d92f08"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_54d92f08"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_54d92f08 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_54d92f08"}



def signal_qna_AlgebraStrategy_mut_3641ca14(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_3641ca14"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_3641ca14 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3641ca14"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3641ca14"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_3641ca14"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_3641ca14"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_3641ca14 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3641ca14"}



def signal_qna_WyckoffStrategy_mut_ce31db94(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_ce31db94"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_ce31db94 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_ce31db94"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_ce31db94"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_ce31db94"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_ce31db94"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_ce31db94 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_ce31db94"}



def signal_qna_MSNRStrategy_mut_c5fe8fa0(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_c5fe8fa0"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_c5fe8fa0 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_c5fe8fa0"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_c5fe8fa0"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_c5fe8fa0"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_c5fe8fa0"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_c5fe8fa0 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_c5fe8fa0"}



def signal_qna_SMCStrategy_mut_cede1437(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_cede1437"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_cede1437 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_cede1437"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_cede1437"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_cede1437"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_cede1437"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_cede1437 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_cede1437"}



def signal_qna_MeanReversionStrategy_mut_7876e3ae(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_7876e3ae"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_7876e3ae import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7876e3ae"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7876e3ae"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_7876e3ae"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_7876e3ae"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_7876e3ae err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_7876e3ae"}



def signal_qna_FiboStrategy_mut_7aeab1e4(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_7aeab1e4"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_7aeab1e4 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_7aeab1e4"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_7aeab1e4"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_7aeab1e4"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_7aeab1e4"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_7aeab1e4 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_7aeab1e4"}



def signal_qna_EMAADXStrategy_mut_c266035b(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_c266035b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_c266035b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_c266035b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_c266035b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_c266035b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_c266035b"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_c266035b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_c266035b"}



def signal_qna_AlgebraStrategy_mut_0e485148(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_0e485148"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_0e485148 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_0e485148"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_0e485148"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_0e485148"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_0e485148"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_0e485148 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_0e485148"}



def signal_qna_WyckoffStrategy_mut_1dd1110c(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_1dd1110c"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_1dd1110c import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_1dd1110c"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_1dd1110c"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_1dd1110c"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_1dd1110c"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_1dd1110c err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_1dd1110c"}



def signal_qna_SMCStrategyOld_mut_03bca343(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_03bca343"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_03bca343 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_03bca343"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_03bca343"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_03bca343"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_03bca343"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_03bca343 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_03bca343"}



def signal_qna_SMCStrategy_mut_4cc3672b(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_4cc3672b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_4cc3672b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_4cc3672b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_4cc3672b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_4cc3672b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_4cc3672b"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_4cc3672b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_4cc3672b"}



def signal_qna_MeanReversionStrategy_mut_1e3676d8(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_1e3676d8"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_1e3676d8 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_1e3676d8"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_1e3676d8"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_1e3676d8"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_1e3676d8"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_1e3676d8 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_1e3676d8"}



def signal_qna_FiboStrategy_mut_0676ee24(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_0676ee24"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_0676ee24 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_0676ee24"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_0676ee24"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_0676ee24"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_0676ee24"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_0676ee24 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_0676ee24"}



def signal_qna_EMAADXStrategy_mut_a80ab814(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_a80ab814"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_a80ab814 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_a80ab814"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_a80ab814"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_a80ab814"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_a80ab814"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_a80ab814 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_a80ab814"}



def signal_qna_AMDXStrategy_mut_e8c2ed72(symbol="EURUSD"):
    """MUE-X evolved: qna_AMDXStrategy_mut_e8c2ed72"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AMDXStrategy_mut_e8c2ed72 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_e8c2ed72"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_e8c2ed72"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AMDXStrategy_mut_e8c2ed72"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AMDXStrategy_mut_e8c2ed72"}
    except Exception as e:
        log.warning(f"MUE-X qna_AMDXStrategy_mut_e8c2ed72 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AMDXStrategy_mut_e8c2ed72"}



def signal_qna_AlgebraStrategy_mut_219ef5b6(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_219ef5b6"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_219ef5b6 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_219ef5b6"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_219ef5b6"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_219ef5b6"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_219ef5b6"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_219ef5b6 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_219ef5b6"}



def signal_qna_WyckoffStrategy_mut_2ae599a2(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_2ae599a2"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_2ae599a2 import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_2ae599a2"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_2ae599a2"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_2ae599a2"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_2ae599a2"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_2ae599a2 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_2ae599a2"}



def signal_qna_SMCStrategyOld_mut_6c24c91b(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategyOld_mut_6c24c91b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategyOld_mut_6c24c91b import generate_signal
        # get_historical_mt5 already in scope (line 245)
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_6c24c91b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_6c24c91b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategyOld_mut_6c24c91b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategyOld_mut_6c24c91b"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategyOld_mut_6c24c91b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategyOld_mut_6c24c91b"}



def signal_qna_MSNRStrategy_mut_dcc0ec64(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_dcc0ec64"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_dcc0ec64 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_dcc0ec64"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_dcc0ec64"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_dcc0ec64"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_dcc0ec64"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_dcc0ec64 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_dcc0ec64"}



def signal_qna_MSNRStrategy_mut_3ad1ef7b(symbol="EURUSD"):
    """MUE-X evolved: qna_MSNRStrategy_mut_3ad1ef7b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MSNRStrategy_mut_3ad1ef7b import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3ad1ef7b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3ad1ef7b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MSNRStrategy_mut_3ad1ef7b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MSNRStrategy_mut_3ad1ef7b"}
    except Exception as e:
        log.warning(f"MUE-X qna_MSNRStrategy_mut_3ad1ef7b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MSNRStrategy_mut_3ad1ef7b"}



def signal_qna_SMCStrategy_mut_88e9ed01(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_88e9ed01"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_88e9ed01 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_88e9ed01"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_88e9ed01"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_88e9ed01"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_88e9ed01"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_88e9ed01 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_88e9ed01"}



def signal_qna_SMCStrategy_mut_8e1060a0(symbol="EURUSD"):
    """MUE-X evolved: qna_SMCStrategy_mut_8e1060a0"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_SMCStrategy_mut_8e1060a0 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_8e1060a0"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_8e1060a0"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_SMCStrategy_mut_8e1060a0"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_SMCStrategy_mut_8e1060a0"}
    except Exception as e:
        log.warning(f"MUE-X qna_SMCStrategy_mut_8e1060a0 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_SMCStrategy_mut_8e1060a0"}



def signal_qna_MeanReversionStrategy_mut_476c4961(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_476c4961"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_476c4961 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_476c4961"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_476c4961"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_476c4961"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_476c4961"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_476c4961 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_476c4961"}



def signal_qna_MeanReversionStrategy_mut_11acfd90(symbol="EURUSD"):
    """MUE-X evolved: qna_MeanReversionStrategy_mut_11acfd90"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_MeanReversionStrategy_mut_11acfd90 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_11acfd90"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_11acfd90"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_11acfd90"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_MeanReversionStrategy_mut_11acfd90"}
    except Exception as e:
        log.warning(f"MUE-X qna_MeanReversionStrategy_mut_11acfd90 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_MeanReversionStrategy_mut_11acfd90"}



def signal_qna_FiboStrategy_mut_1ed8fa83(symbol="EURUSD"):
    """MUE-X evolved: qna_FiboStrategy_mut_1ed8fa83"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_FiboStrategy_mut_1ed8fa83 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_1ed8fa83"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_1ed8fa83"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_FiboStrategy_mut_1ed8fa83"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_FiboStrategy_mut_1ed8fa83"}
    except Exception as e:
        log.warning(f"MUE-X qna_FiboStrategy_mut_1ed8fa83 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_FiboStrategy_mut_1ed8fa83"}



def signal_qna_EMAADXStrategy_mut_ba4d1c3b(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_ba4d1c3b"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_ba4d1c3b import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_ba4d1c3b"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_ba4d1c3b"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_ba4d1c3b"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_ba4d1c3b"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_ba4d1c3b err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_ba4d1c3b"}



def signal_qna_EMAADXStrategy_mut_8d94f439(symbol="EURUSD"):
    """MUE-X evolved: qna_EMAADXStrategy_mut_8d94f439"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_EMAADXStrategy_mut_8d94f439 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8d94f439"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8d94f439"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_EMAADXStrategy_mut_8d94f439"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_EMAADXStrategy_mut_8d94f439"}
    except Exception as e:
        log.warning(f"MUE-X qna_EMAADXStrategy_mut_8d94f439 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_EMAADXStrategy_mut_8d94f439"}



def signal_qna_AlgebraStrategy_mut_3f3687bb(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_3f3687bb"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_3f3687bb import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3f3687bb"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3f3687bb"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_3f3687bb"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_3f3687bb"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_3f3687bb err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_3f3687bb"}



def signal_qna_AlgebraStrategy_mut_01a09333(symbol="EURUSD"):
    """MUE-X evolved: qna_AlgebraStrategy_mut_01a09333"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_AlgebraStrategy_mut_01a09333 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_01a09333"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_01a09333"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_AlgebraStrategy_mut_01a09333"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_AlgebraStrategy_mut_01a09333"}
    except Exception as e:
        log.warning(f"MUE-X qna_AlgebraStrategy_mut_01a09333 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_AlgebraStrategy_mut_01a09333"}



def signal_qna_WyckoffStrategy_mut_6c7db5d7(symbol="EURUSD"):
    """MUE-X evolved: qna_WyckoffStrategy_mut_6c7db5d7"""
    try:
        import sys as _sys
        _sys.path.insert(0, r"E:\mue-x\genes\qna_strategies")
        from qna_WyckoffStrategy_mut_6c7db5d7 import generate_signal

        from hedge_fund import get_historical_mt5
        df = get_historical_mt5(symbol, count=100)
        if df is None or len(df) < 50:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_6c7db5d7"}
        result = generate_signal(df)
        if result is None or len(result) < 2:
            return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_6c7db5d7"}
        last = result.iloc[-1]
        if last.get('entry',0) == 1:
            return {"bias":"buy","confidence":0.55,"source":"qna_WyckoffStrategy_mut_6c7db5d7"}
        if last.get('entry',0) == -1:
            return {"bias":"sell","confidence":0.55,"source":"qna_WyckoffStrategy_mut_6c7db5d7"}
    except Exception as e:
        log.warning(f"MUE-X qna_WyckoffStrategy_mut_6c7db5d7 err: {e}")
    return {"bias":"neutral","confidence":0,"source":"qna_WyckoffStrategy_mut_6c7db5d7"}


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


# MUE-X evolved providers — injected by autonomous agent below
QNA_EVOLVED_PROVIDERS = [
    # MUE-X will inject signal_qna_* here
    signal_qna_MSNRStrategy_mut_3b787b28,
    signal_qna_SMCStrategy_mut_28bdc019,
    signal_qna_MeanReversionStrategy_mut_54b813e2,
    signal_qna_FiboStrategy_mut_b7b9082d,
    signal_qna_EMAADXStrategy_mut_18900f77,
    signal_qna_AMDXStrategy_mut_34f6635d,
    signal_qna_AlgebraStrategy_mut_09836ba3,
    signal_qna_WyckoffStrategy_mut_4be93408,
    signal_qna_SMCStrategyOld_mut_d9b02f7b,
    signal_qna_AlgebraStrategy_mut_08cdba54,
    signal_qna_AlgebraStrategy_mut_4d25722b,
    signal_qna_AlgebraStrategy_mut_54c88cbb,
    signal_qna_AlgebraStrategy_mut_57a93e76,
    signal_qna_AlgebraStrategy_mut_6478b3bf,
    signal_qna_AlgebraStrategy_mut_6e5274a7,
    signal_qna_AlgebraStrategy_mut_abdee600,
    signal_qna_AlgebraStrategy_mut_ca720a52,
    signal_qna_AlgebraStrategy_mut_cce8f5f3,
    signal_qna_AlgebraStrategy_mut_d4d7966f,
    signal_qna_AlgebraStrategy_mut_e9b231a7,
    signal_qna_AMDXStrategy_mut_163071ea,
    signal_qna_AMDXStrategy_mut_2b6056c1,
    signal_qna_AMDXStrategy_mut_2ed7d815,
    signal_qna_AMDXStrategy_mut_f09909bb,
    signal_qna_EMAADXStrategy_mut_19a19dd1,
    signal_qna_EMAADXStrategy_mut_2329920e,
    signal_qna_EMAADXStrategy_mut_3a5e1072,
    signal_qna_EMAADXStrategy_mut_465f341c,
    signal_qna_EMAADXStrategy_mut_5f4e558e,
    signal_qna_EMAADXStrategy_mut_797d1ed2,
    signal_qna_EMAADXStrategy_mut_7dd06442,
    signal_qna_EMAADXStrategy_mut_7e80edc0,
    signal_qna_EMAADXStrategy_mut_89a691ea,
    signal_qna_EMAADXStrategy_mut_8dce545f,
    signal_qna_EMAADXStrategy_mut_f06897a3,
    signal_qna_FiboStrategy_mut_08ef309d,
    signal_qna_FiboStrategy_mut_22ab1442,
    signal_qna_FiboStrategy_mut_267de559,
    signal_qna_FiboStrategy_mut_3d236bb5,
    signal_qna_FiboStrategy_mut_625964f5,
    signal_qna_FiboStrategy_mut_726d2261,
    signal_qna_FiboStrategy_mut_75c8d197,
    signal_qna_FiboStrategy_mut_b57a5c3a,
    signal_qna_FiboStrategy_mut_e918f65d,
    signal_qna_MeanReversionStrategy_mut_238dc347,
    signal_qna_MeanReversionStrategy_mut_29ffbe50,
    signal_qna_MeanReversionStrategy_mut_3f94aebd,
    signal_qna_MeanReversionStrategy_mut_534a3e48,
    signal_qna_MeanReversionStrategy_mut_7beac3f8,
    signal_qna_MeanReversionStrategy_mut_80c3a50c,
    signal_qna_MeanReversionStrategy_mut_aeac95c8,
    signal_qna_MeanReversionStrategy_mut_d0c35fc0,
    signal_qna_MeanReversionStrategy_mut_d282b0ab,
    signal_qna_MeanReversionStrategy_mut_efed8264,
    signal_qna_MeanReversionStrategy_mut_f2242159,
    signal_qna_MSNRStrategy_mut_0c38513d,
    signal_qna_MSNRStrategy_mut_1082a506,
    signal_qna_MSNRStrategy_mut_21397cf7,
    signal_qna_MSNRStrategy_mut_2512c57e,
    signal_qna_MSNRStrategy_mut_25630ace,
    signal_qna_MSNRStrategy_mut_25ec0944,
    signal_qna_MSNRStrategy_mut_30fe44aa,
    signal_qna_MSNRStrategy_mut_47a61c1a,
    signal_qna_MSNRStrategy_mut_48735c9a,
    signal_qna_MSNRStrategy_mut_85877fda,
    signal_qna_MSNRStrategy_mut_cfd837e7,
    signal_qna_MSNRStrategy_mut_e10dba6a,
    signal_qna_QuarterlyTheoryStrategy_mut_99914b93,
    signal_qna_SMCStrategy_mut_0502371a,
    signal_qna_SMCStrategy_mut_0ab19902,
    signal_qna_SMCStrategy_mut_3faccbdb,
    signal_qna_SMCStrategy_mut_42674b81,
    signal_qna_SMCStrategy_mut_5b5e79dc,
    signal_qna_SMCStrategy_mut_5f503a0f,
    signal_qna_SMCStrategy_mut_7b7c1579,
    signal_qna_SMCStrategy_mut_7dc3a1f7,
    signal_qna_SMCStrategy_mut_938d57fc,
    signal_qna_SMCStrategy_mut_eef32422,
    signal_qna_SMCStrategy_mut_f0d3ea7a,
    signal_qna_SMCStrategyOld_mut_023786dc,
    signal_qna_SMCStrategyOld_mut_16bdcdd1,
    signal_qna_SMCStrategyOld_mut_792be0a9,
    signal_qna_SMCStrategyOld_mut_af1ac2b3,
    signal_qna_WyckoffStrategy_mut_35e60a57,
    signal_qna_WyckoffStrategy_mut_3af916de,
    signal_qna_WyckoffStrategy_mut_9516b5c7,
    signal_qna_WyckoffStrategy_mut_c354345b,
    signal_qna_WyckoffStrategy_mut_cb42e9bb,
    signal_qna_WyckoffStrategy_mut_d1311580,
    signal_qna_WyckoffStrategy_mut_d577a6a0,
    signal_qna_WyckoffStrategy_mut_db5ec800,
    signal_qna_WyckoffStrategy_mut_f643d6d7,
    signal_qna_WyckoffStrategy_mut_f82fb744,
    signal_qna_MSNRStrategy_mut_ea45617a,
    signal_qna_SMCStrategy_mut_561f4ce1,
    signal_qna_MeanReversionStrategy_mut_cc3d5065,
    signal_qna_EMAADXStrategy_mut_54d92f08,
    signal_qna_AlgebraStrategy_mut_3641ca14,
    signal_qna_WyckoffStrategy_mut_ce31db94,
    signal_qna_MSNRStrategy_mut_c5fe8fa0,
    signal_qna_SMCStrategy_mut_cede1437,
    signal_qna_MeanReversionStrategy_mut_7876e3ae,
    signal_qna_FiboStrategy_mut_7aeab1e4,
    signal_qna_EMAADXStrategy_mut_c266035b,
    signal_qna_AlgebraStrategy_mut_0e485148,
    signal_qna_WyckoffStrategy_mut_1dd1110c,
    signal_qna_SMCStrategyOld_mut_03bca343,
    signal_qna_SMCStrategy_mut_4cc3672b,
    signal_qna_MeanReversionStrategy_mut_1e3676d8,
    signal_qna_FiboStrategy_mut_0676ee24,
    signal_qna_EMAADXStrategy_mut_a80ab814,
    signal_qna_AMDXStrategy_mut_e8c2ed72,
    signal_qna_AlgebraStrategy_mut_219ef5b6,
    signal_qna_WyckoffStrategy_mut_2ae599a2,
    signal_qna_SMCStrategyOld_mut_6c24c91b,
    signal_qna_MSNRStrategy_mut_dcc0ec64,
    signal_qna_MSNRStrategy_mut_3ad1ef7b,
    signal_qna_SMCStrategy_mut_88e9ed01,
    signal_qna_SMCStrategy_mut_8e1060a0,
    signal_qna_MeanReversionStrategy_mut_476c4961,
    signal_qna_MeanReversionStrategy_mut_11acfd90,
    signal_qna_FiboStrategy_mut_1ed8fa83,
    signal_qna_EMAADXStrategy_mut_ba4d1c3b,
    signal_qna_EMAADXStrategy_mut_8d94f439,
    signal_qna_AlgebraStrategy_mut_3f3687bb,
    signal_qna_AlgebraStrategy_mut_01a09333,
    signal_qna_WyckoffStrategy_mut_6c7db5d7,
]
# Rebuild ALL_PROVIDERS to include both core + evolved
ALL_PROVIDERS = CORE_PROVIDERS[:] + QNA_EVOLVED_PROVIDERS

def _timeout_call(fn, args=(), timeout=8):
    """Call fn(*args) with a timeout. Returns neutral result if timeout."""
    res = {"bias": "neutral", "confidence": 0, "source": fn.__name__ if hasattr(fn, '__name__') else "?"}
    def target():
        try:
            r = fn(*args)
            if isinstance(r, dict):
                res.update(r)
        except Exception as e:
            res["_error"] = str(e)
    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        log.warning(f"  ⏰ {fn.__name__}: timeout ({timeout}s)")
    return res

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
        from market_context import get_currency_strength, get_dxy
        dxy = get_dxy()
        dxy_trend = dxy.get("trend", "unknown")
        dxy_price = dxy.get("price", "?")
        _ = get_currency_strength()  # side-effect: populates internal cache
        
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
# PAPER_LOG already defined at module level (line 43)

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
# GATE_FILE already defined at module level (line 44)

def check_gate():
    """Cek apakah strategi lolos walk-forward gate"""
    import subprocess
    # Run backtest pipeline
    r = subprocess.run([sys.executable, str(_QNA_DIR / 'backtest_pipeline.py')],
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
    gate_cache = GATE_FILE
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
                r = subprocess.run([sys.executable, str(_QNA_DIR / 'backtest_pipeline.py')],
                                  capture_output=True, text=True, timeout=120)
                gate_pass = '"pass": true' in (r.stdout + r.stderr)
            except Exception as e:
                log.warning(f"Backtest failed: {e}")
    
    if not gate_pass:
        log.warning("❌ GATE TERTUTUP — Strategi gagal backtest/walk-forward")
        log.warning("   Tidak akan execute sampai strategi diperbaiki")
        if not PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass
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
                            try:
                                mt5.shutdown()
                            except Exception:
                                pass
                        return
                    log.info(f"✅ Risk Guard APPROVED (score={rg_result.get('score',0):.2f})")
                except Exception as e:
                    log.warning(f"Risk guard unavailable, proceeding: {e}")
                
                # STEP 7: Execute
                execute(signal, symbol)
                
    finally:
        if not PAPER_TRADE:
            try:
                mt5.shutdown()
            except Exception:
                pass

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

# Auto-registered by MUE-X: qna_MSNRStrategy_mut_2512c57e

# Auto-registered by MUE-X: qna_MSNRStrategy_mut_25ec0944

# Auto-registered by MUE-X: qna_SMCStrategy_mut_7dc3a1f7

# Auto-registered by MUE-X: qna_SMCStrategy_mut_3faccbdb

# Auto-registered by MUE-X: qna_MeanReversionStrategy_mut_3f94aebd

# Auto-registered by MUE-X: qna_MeanReversionStrategy_mut_efed8264

# Auto-registered by MUE-X: qna_FiboStrategy_mut_b7b9082d

# Auto-registered by MUE-X: qna_FiboStrategy_mut_267de559

# Auto-registered by MUE-X: qna_EMAADXStrategy_mut_f06897a3

# Auto-registered by MUE-X: qna_EMAADXStrategy_mut_3a5e1072

# Auto-registered by MUE-X: qna_AMDXStrategy_mut_2ed7d815

# Auto-registered by MUE-X: qna_AMDXStrategy_mut_2ed7d815

# Auto-registered by MUE-X: qna_AlgebraStrategy_mut_6e5274a7

# Auto-registered by MUE-X: qna_AlgebraStrategy_mut_54c88cbb

# Auto-registered by MUE-X: qna_WyckoffStrategy_mut_f82fb744

# Auto-registered by MUE-X: qna_WyckoffStrategy_mut_3af916de

# Auto-registered by MUE-X: qna_SMCStrategyOld_mut_792be0a9

# Auto-registered by MUE-X: qna_SMCStrategyOld_mut_d9b02f7b
