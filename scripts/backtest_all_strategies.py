"""
QNA WAR PLAN — Phase 2: Backtest ALL registered strategies.
Gate: Sharpe>0.5, Return>0%, MaxDD>-25% on EURUSD=X (6mo daily).
Vectorized generate_signals when possible, bar-by-bar fallback otherwise.
"""
import sys, json, logging, time, threading
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

_HERE = Path(__file__).resolve().parent.parent
SRC = _HERE / 'results'
RESULT = SRC
RESULT.mkdir(parents=True, exist_ok=True)
HERE = _HERE
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

raw = yf.download("EURUSD=X", period="6mo", interval="1d", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.columns = [c.lower() for c in raw.columns]
df = raw[['open','high','low','close','volume']].dropna()
N = len(df)
print(f"Data: {N} bars (6mo daily EURUSD)")

from quant_nanggroe.engine.strategies.registry import StrategyRegistry
strategies = StrategyRegistry.list_strategies()
print(f"Registered: {len(strategies)} strategies")

def compute(signals, data):
    close = data['close'].values
    trades, pos, entry = [], 0, 0.0
    for i in range(1, len(close)):
        sig = int(signals.iloc[i]) if i < len(signals) else 0
        if sig == 1 and pos == 0: pos = 1; entry = close[i]
        elif sig == -1 and pos == 0: pos = -1; entry = close[i]
        elif sig == -1 and pos == 1: trades.append((close[i]-entry)/entry); pos = 0
        elif sig == 1 and pos == -1: trades.append((entry-close[i])/entry); pos = 0
    if not trades:
        return None
    a = np.array(trades)
    ret = float(np.prod(1+a)-1)*100
    sharpe = float(np.mean(a)/np.std(a)*np.sqrt(252)) if np.std(a)>0 else 0
    eq = np.cumprod(1+a); rmx = np.maximum.accumulate(eq)
    dd = float(np.min((eq-rmx)/rmx)*100)
    w = a[a>0]
    wr = float(len(w)/len(a)*100) if len(a)>0 else 0
    return {"return":round(ret,2),"sharpe":round(sharpe,3),"maxdd":round(dd,2),"trades":len(a),"wr":round(wr,1)}

def extract_signals(name, inst):
    """Return pd.Series of signals (0/1/-1) or None."""
    signals = pd.Series(0, index=df.index)
    # Try vectorized first
    if hasattr(inst, 'generate_signals') and callable(inst.generate_signals):
        try:
            result = inst.generate_signals(df)
            if isinstance(result, pd.DataFrame):
                for col in ('entry', 'signal', 'position', 'signals'):
                    if col in result.columns:
                        signals = result[col].reindex(df.index).fillna(0)
                        return signals
                return None
            elif isinstance(result, pd.Series):
                return result.reindex(df.index).fillna(0)
            elif isinstance(result, np.ndarray):
                return pd.Series(result, index=df.index)
        except Exception:
            pass
    # Bar-by-bar fallback
    if hasattr(inst, 'generate_signal') and callable(inst.generate_signal):
        warm = 50
        for i in range(warm, N):
            win = inst.generate_signal(df.iloc[:i+1])
            if win is None: continue
            # StrategySignal
            direction = getattr(win, 'direction', None)
            if direction is not None:
                d = str(direction).lower()
                if 'buy' in d: signals.iloc[i] = 1
                elif 'sell' in d: signals.iloc[i] = -1
                continue
            # pd.Series fallback
            if isinstance(win, pd.Series):
                signals.iloc[i] = win.iloc[-1] if len(win) > 0 else 0
                continue
            # Old signal_type fallback
            if hasattr(win, 'signal_type'):
                st = win.signal_type.value if hasattr(win.signal_type, 'value') else str(win.signal_type)
                if st == 'buy': signals.iloc[i] = 1
                elif st == 'sell': signals.iloc[i] = -1
        return signals
    return None

results = []
failed = []
skipped = []
for idx, name in enumerate(strategies):
    t0 = time.time()
    cls = StrategyRegistry.get(name)
    if not cls:
        failed.append(name); continue
    try:
        instance = cls()
    except Exception as e:
        failed.append(name)
        print(f"[{idx+1}/{len(strategies)}] {name:30s} INIT-FAIL ({e})")
        continue
    try:
        signals = extract_signals(name, instance)
    except Exception as e:
        failed.append(name)
        print(f"[{idx+1}/{len(strategies)}] {name:30s} FAIL ({e})")
        continue
    if signals is None:
        skipped.append(name)
        print(f"[{idx+1}/{len(strategies)}] {name:30s} SKIP (no-signal-col)")
        continue
    elapsed = round(time.time()-t0, 1)
    m = compute(signals, df)
    if m is None:
        skipped.append(name)
        results.append({"strategy":name,"return":0,"sharpe":0,"maxdd":0,"trades":0,"wr":0,"pass":False,"sec":elapsed,"notes":"no_trades"})
        print(f"[{idx+1}/{len(strategies)}] {name:30s} SKIP no-trades ({elapsed}s)")
        continue
    passed = m['sharpe'] > 0.5 and m['return'] > 0 and m['maxdd'] > -25
    results.append({"strategy":name, **m, "pass": passed, "sec":elapsed})
    tag = "PASS" if passed else "FAIL"
    print(f"[{idx+1}/{len(strategies)}] {name:30s} {tag} SR={m['sharpe']:+.2f} Ret={m['return']:+.2f}% DD={m['maxdd']:.1f}% T={m['trades']} ({elapsed}s)")

passed_cnt = sum(1 for r in results if r.get('pass'))
report = {
    "timestamp": datetime.now().isoformat(),
    "symbol": "EURUSD",
    "period": "6mo daily",
    "total": len(results),
    "pass": passed_cnt,
    "fail": len(results) - passed_cnt,
    "skipped_no_trades": len(skipped),
    "failed_import": len(failed),
    "results": sorted(results, key=lambda x: x['sharpe'], reverse=True),
}
out = RESULT / "gate_status.json"
out.write_text(json.dumps(report, indent=2))
print(f"\n{'='*50}")
print(f"Gate: {passed_cnt}/{len(results)} pass")
print(f"Skipped: {len(skipped)} | Failed: {len(failed)}")
print(f"Saved: {out}")
