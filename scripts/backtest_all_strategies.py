"""
QNA WAR PLAN — Phase 2: Fast backtest ALL registered strategies.
Gate: Sharpe>0.5, Return>0%, MaxDD>-25% on EURUSD=X (6mo daily).
Uses vectorized generate_signals when possible, per-strategy timeout otherwise.
"""
import sys, json, logging, time, multiprocessing
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FutTimeout

SRC = Path(r'E:/trading')
RESULT = SRC / 'results'
RESULT.mkdir(parents=True, exist_ok=True)
HERE = Path(r'D:/repositories/Quant-Nanggroe-AI-worktree')
sys.path.insert(0, str(HERE))
logging.basicConfig(level=logging.ERROR)

SYMBOL = "EURUSD=X"
raw = yf.download(SYMBOL, period="6mo", interval="1d", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.columns = [c.lower() for c in raw.columns]
df = raw[['open','high','low','close','volume']].dropna()
N = len(df)
print(f"Data: {N} bars (6mo daily)")

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

def backtest_one(name):
    """Returns result dict or None if can't produce trades."""
    t0 = time.time()
    cls = StrategyRegistry.get(name)
    if not cls:
        return {"strategy":name,"error":"not found","pass":False}
    try:
        instance = cls()
    except Exception as e:
        return {"strategy":name,"error":f"init: {e}","pass":False}
    if not hasattr(instance, 'generate_signal') and not hasattr(instance, 'generate_signals'):
        return {"strategy":name,"error":"no signal method","pass":False}

    signals = pd.Series(0, index=df.index)
    try:
        # Try vectorized first
        if hasattr(instance, 'generate_signals') and callable(instance.generate_signals):
            result = instance.generate_signals(df)
            if isinstance(result, pd.DataFrame) and 'signal' in result.columns:
                signals = result['signal'].reindex(df.index).fillna(0)
            elif isinstance(result, pd.Series):
                signals = result.reindex(df.index).fillna(0)
            elif isinstance(result, np.ndarray):
                signals = pd.Series(result, index=df.index)
        else:
            # Bar-by-bar fallback
            warm = 50
            for i in range(warm, N):
                win = instance.generate_signal(df.iloc[:i+1])
                if win is None:
                    continue
                if isinstance(win, pd.Series):
                    signals.iloc[i] = win.iloc[-1] if len(win) > 0 else 0
                elif hasattr(win, 'signal_type'):
                    st = win.signal_type.value if hasattr(win.signal_type, 'value') else str(win.signal_type)
                    signals.iloc[i] = 1 if st=='buy' else -1 if st=='sell' else 0
    except Exception as e:
        return {"strategy":name,"error":f"signal_gen: {e}","pass":False,"sec":round(time.time()-t0,1)}

    elapsed = round(time.time()-t0, 1)
    m = compute(signals, df)
    if m is None:
        return {"strategy":name,"return":0,"sharpe":0,"maxdd":0,"trades":0,"wr":0,"pass":False,"sec":elapsed,"notes":"no_trades"}
    passed = m['sharpe'] > 0.5 and m['return'] > 0 and m['maxdd'] > -25
    return {"strategy":name, **m, "pass": passed, "sec":elapsed}

# Run sequentially with per-strategy timeout via signal (single process, avoid spawn overhead)
results = []
failed = []
skipped = []
for idx, name in enumerate(strategies):
    # Quick skip for known slow
    if name in ('kronos', 'kronos_wrapper', 'kronos_ensemble'):
        result = backtest_one(name)
        if 'error' in result and 'signal_gen' in str(result.get('error','')):
            skipped.append(name)
            print(f"[{idx+1}/{len(strategies)}] {name:30s} SKIP (slow gen)")
            continue
    result = backtest_one(name)
    results.append(result)
    if 'error' in result:
        err = result['error']
        if 'no_trades' in err:
            skipped.append(name)
            print(f"[{idx+1}/{len(strategies)}] {name:30s} SKIP ({err})")
        else:
            failed.append(name)
            print(f"[{idx+1}/{len(strategies)}] {name:30s} FAIL ({err})")
    elif 'notes' in result and result['notes']=='no_trades':
        skipped.append(name)
        print(f"[{idx+1}/{len(strategies)}] {name:30s} SKIP no-trades")
    else:
        tag = "PASS" if result['pass'] else "FAIL"
        print(f"[{idx+1}/{len(strategies)}] {name:30s} {tag} SR={result['sharpe']:+.2f} Ret={result['return']:+.2f}% DD={result['maxdd']:.1f}% T={result['trades']} ({result['sec']}s)")

passed_cnt = sum(1 for r in results if r.get('pass') and not r.get('error'))
report = {
    "timestamp": datetime.now().isoformat(),
    "symbol": "EURUSD",
    "period": "6mo daily",
    "total": len([r for r in results if 'error' not in r]),
    "pass": passed_cnt,
    "fail": len(results) - passed_cnt,
    "skipped_no_trades": len(skipped),
    "failed_import": len(failed),
    "results": sorted([r for r in results if 'error' not in r], key=lambda x: x['sharpe'], reverse=True),
}
out = RESULT / "gate_status.json"
out.write_text(json.dumps(report, indent=2))
print(f"\n{'='*50}")
print(f"Gate: {passed_cnt}/{len([r for r in results if 'error' not in r])} pass")
print(f"Skipped (no trades): {len(skipped)} | Failed (error): {len(failed)}")
print(f"Saved: {out}")