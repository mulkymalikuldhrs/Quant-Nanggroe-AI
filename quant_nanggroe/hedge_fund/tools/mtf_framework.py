"""
Multi-Timeframe Trading Framework
Support: Intraday 1/2, Swing 1/2, Scalping — semua pasangan timeframe
"""
import logging
import sys
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

_HF_TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HF_TOOLS_DIR))
SRC = _HF_TOOLS_DIR
log = logging.getLogger('mtf')

# ── Timeframe Mapping ──
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1, "M3": mt5.TIMEFRAME_M3, "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
}

# ── Trading Styles ──
STYLES = {
    "intraday1": {
        "name": "Intraday 1",
        "htf": ["H4", "H1", "M15"],  # chain: H4 bias → H1 confirm → M15 entry
        "ltf": "M15",
        "desc": "HTF bias H4>H1>M15, konfirmasi entry + SL placement"
    },
    "intraday2": {
        "name": "Intraday 2",
        "htf": ["H1", "M15", "M3"],
        "ltf": "M3",
        "desc": "HTF H1>M15>M3/M1, entry lebih cepat"
    },
    "swing1": {
        "name": "Swing 1",
        "htf": ["W1", "D1", "H1"],
        "ltf": "H1",
        "desc": "HTF W1>D1>H1, posisi multi-hari"
    },
    "swing2": {
        "name": "Swing 2",
        "htf": ["D1", "H4", "M15"],
        "ltf": "M15",
        "desc": "HTF D1>H4>M15, swing jangka pendek"
    },
    "scalping": {
        "name": "Scalping",
        "htf": ["M15", "M5", "M1"],
        "ltf": "M1",
        "desc": "M15>M5>M1, entry cepat exit cepat"
    },
}

# ── Data Loader (multi-timeframe) ──
def load_mtf(symbol="EURUSD", bars=500):
    """Load data for ALL timeframes"""
    result = {}
    for name, tf in TIMEFRAMES.items():
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is not None and len(rates) > 20:
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            # Rename untuk konsistensi
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            result[name] = df
    return result

# ── HTF Bias Analyzer ──
def htf_bias(df_htf):
    """Higher Timeframe Bias — tren utama dari timeframe tertinggi"""
    if df_htf is None or len(df_htf) < 30: return "neutral"
    c = df_htf['close']
    # EMA 20/50 untuk tren
    ema20 = c.ewm(span=20).mean()
    ema50 = c.ewm(span=50).mean()
    # Market structure
    hh = c.rolling(20).max()
    ll = c.rolling(20).min()
    
    last = c.iloc[-1]
    if ema20.iloc[-1] > ema50.iloc[-1] and last > ema20.iloc[-1]:
        return "bull"
    elif ema20.iloc[-1] < ema50.iloc[-1] and last < ema20.iloc[-1]:
        return "bear"
    # Check for HH/HL
    if last >= hh.iloc[-5]: return "bull"
    if last <= ll.iloc[-5]: return "bear"
    return "neutral"

# ── Multi-Timeframe Signal ──
def mtf_signal(mtf_data, style_name, strategy_func):
    """
    Chain: HTF bias → konfirmasi → entry di LTF
    strategy_func(df) returns {'signal':1/-1/0, 'confidence':0-1}
    """
    style = STYLES.get(style_name)
    if not style: return {"bias": "neutral", "confidence": 0}
    
    htf_chain = style['htf']
    ltf_name = style['ltf']
    
    # STEP 1: HTF bias dari timeframe tertinggi
    htf_bias_result = htf_bias(mtf_data.get(htf_chain[0]))
    if htf_bias_result == "neutral":
        # Coba timeframe kedua
        htf_bias_result = htf_bias(mtf_data.get(htf_chain[1]))
    
    # STEP 2: Konfirmasi dari timeframe menengah
    confirm = strategy_func(mtf_data.get(htf_chain[1])) if len(htf_chain) > 1 else {"signal": 1}
    
    # STEP 3: Entry signal dari LTF
    entry = strategy_func(mtf_data.get(ltf_name))
    
    # STEP 4: Final decision
    bias = "neutral"
    conf = 0
    
    if htf_bias_result == "bull" and entry.get('signal', 0) == 1:
        bias = "buy"
        conf = entry.get('confidence', 0.5) * 1.0
    elif htf_bias_result == "bear" and entry.get('signal', 0) == -1:
        bias = "sell"
        conf = entry.get('confidence', 0.5) * 1.0
    elif entry.get('signal', 0) != 0:
        # LTF entry without HTF confirmation = lower confidence
        bias = "buy" if entry['signal'] == 1 else "sell"
        conf = entry.get('confidence', 0.3) * 0.5
    
    return {
        "bias": bias,
        "confidence": round(conf, 2),
        "style": style_name,
        "htf_bias": htf_bias_result,
        "entry_signal": entry.get('signal', 0),
        "htf_chain": htf_chain,
        "ltf": ltf_name,
    }

# ── Strategy Wrapper (ubah strategy registry → signal dict) ──
def strategy_wrapper(strategy_name, **params):
    """Wrap strategy registry jadi fungsi signal untuk MTF"""
    from quant_nanggroe.engine.strategies import get_strategy_metadata as get_strategy
    
    def wrapper(df):
        if df is None or len(df) < 60: return {"signal": 0, "confidence": 0}
        try:
            strat = get_strategy(strategy_name, **params)
            signals = strat.generate_signals(df)
            # Check last 10 bars for any signal (not just last bar)
            recent = signals.tail(10)
            non_zero = recent[recent['entry'] != 0]
            if len(non_zero) > 0:
                last_sig = non_zero.iloc[-1]
                entry = last_sig['entry']
                # Boost confidence jika signal recent (within last 3 bars)
                idx_pos = len(recent) - 1
                for i in range(len(recent)-1, -1, -1):
                    if recent.iloc[i]['entry'] != 0:
                        idx_pos = len(recent) - 1 - i
                        break
                confidence = max(0.3, 0.65 - idx_pos * 0.1)
                return {"signal": entry, "confidence": min(1.0, confidence)}
            return {"signal": 0, "confidence": 0}
        except:
            return {"signal": 0, "confidence": 0}
    return wrapper

# ── Test All Styles for a Strategy ──
def test_strategy_all_styles(strategy_name, symbol="EURUSD", **params):
    """Test 1 strategy across all 5 trading styles"""
    log.info(f"Testing {strategy_name} on ALL styles for {symbol}")
    
    if not mt5.initialize():
        log.error("MT5 unavailable"); return
    
    mtf_data = load_mtf(symbol)
    mt5.shutdown()
    
    func = strategy_wrapper(strategy_name, **params)
    results = {}
    
    for style_name in STYLES:
        sig = mtf_signal(mtf_data, style_name, func)
        results[style_name] = sig
        log.info(f"  {STYLES[style_name]['name']}: {sig['bias']} (conf={sig['confidence']}, HTF={sig['htf_bias']})")
    
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    
    print("═══ Multi-Timeframe Framework ═══\n")
    for name, style in STYLES.items():
        print(f"  {name:12s}: {style['desc']}")
    
    print("\nTesting Wyckoff on all styles...")
    r = test_strategy_all_styles("WyckoffStrategy", lookback=50, volume_mult=1.3)
