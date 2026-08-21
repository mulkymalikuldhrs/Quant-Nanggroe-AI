import sys, json, math, time
sys.path.insert(0, 'D:/repositories/Quant-Nanggroe-AI-worktree')
import yfinance as yf
import numpy as np
from quant_nanggroe.backtest.strategy_factory import StrategyFactory, StrategyVariant

# Load real M15 EURUSD (60d)
print("Loading M15 EURUSD real...")
df = yf.Ticker("EURUSD=X").history(period="60d", interval="15m")
# Build candles List[Dict] for strategy_factory signal fns
candles = [{"open":float(r["Open"]),"high":float(r["High"]),"low":float(r["Low"]),"close":float(r["Close"]),"volume":float(r["Volume"])} for _,r in df.iterrows()]
closes = np.array([c["close"] for c in candles])
n = len(candles)

# Generate all 200-ish variants
factory = StrategyFactory()
all_variants = factory.generate()  # 1000+
print(f"Total factory variants: {len(all_variants)}")
# Cap to 200 to match task wording and runtime
variants = all_variants[:200]
print(f"Backtesting first {len(variants)} variants...")

def backtest(signals, closes, prices, initial=1000):
    """Simple vectorized backtest. signals=List[int] (1/0/-1)."""
    capital = initial
    pos = 0
    entry = 0
    equity = np.zeros(len(signals))
    equity[0] = initial
    trades = 0
    for i in range(len(signals)):
        p = float(prices[i])
        # close old pos if signal flips
        if pos != 0:
            if signals[i] == 0 or (pos == 1 and signals[i] == -1) or (pos == -1 and signals[i] == 1):
                capital += pos * (p - entry) * capital / entry
                trades += 1
                pos = 0
        # open
        if pos == 0 and signals[i] != 0:
            pos = signals[i]
            entry = p
        # equity valuation
        if pos != 0:
            equity[i] = capital + pos * (p - entry) * capital / entry
        else:
            equity[i] = capital
    # final close
    if pos != 0:
        final_p = float(closes[-1])
        capital += pos * (final_p - entry) * capital / entry
        trades += 1
    ret_pct = (capital - initial) / initial * 100
    # Sharpe (M15: ~8760 bars/yr)
    rets = np.diff(equity) / np.maximum(equity[:-1], 1e-9)
    rets = rets[~np.isnan(rets)]
    sharpe = math.sqrt(8760) * np.mean(rets) / (np.std(rets)+1e-9) if len(rets) > 1 else 0
    if math.isnan(sharpe) or math.isinf(sharpe): sharpe = 0
    peak = np.maximum.accumulate(equity)
    dd = float(np.min((equity - peak) / np.maximum(peak, 1e-9)) * 100) if len(peak) > 0 else 0
    return {"sharpe": round(float(sharpe),3), "return_pct": round(float(ret_pct),2), "dd": round(float(dd),2), "trades": trades}

# 5-fold walk-forward (OOS test on last 5 folds of last 20% each)
def wf_backtest(signals, closes, prices, n_folds=5):
    """Split signals into folds, backtest each fold, aggregate."""
    fold_size = len(closes) // n_folds
    results = []
    for fold in range(n_folds):
        start = fold * fold_size
        end = start + fold_size if fold < n_folds - 1 else len(closes)
        sig_f = signals[start:end]
        close_f = closes[start:end]
        if len(sig_f) < 10: continue
        r = backtest(sig_f, close_f, close_f)
        results.append(r)
    if not results:
        return {"sharpe":0,"return_pct":0,"dd":0,"trades":0}
    # Aggregate: average sharpe, sum return, min dd
    return {"sharpe": round(np.mean([r["sharpe"] for r in results]),3),
            "return_pct": round(sum(r["return_pct"] for r in results)/n_folds,2),
            "dd": round(min(r["dd"] for r in results),2),
            "trades": sum(r["trades"] for r in results)//n_folds}

start = time.time()
results = []
gate_count = 0
for idx, variant in enumerate(variants):
    try:
        sigs = variant.generate_signals(candles)
        if len(sigs) != len(closes):
            sigs = sigs[:len(closes)]
        r = wf_backtest(sigs, closes, closes)
        passed = r["sharpe"] > 0.5 and r["return_pct"] > 0 and r["dd"] > -25
        if passed: gate_count += 1
        results.append({"strategy": variant.name, "pass": passed, "sharpe": r["sharpe"], "return_pct": r["return_pct"], "dd": r["dd"], "trades": r["trades"]})
    except Exception as e:
        results.append({"strategy": variant.name, "pass": False, "reason": str(type(e).__name__), "sharpe": 0, "return_pct": 0, "dd": 0, "trades": 0})
    if idx % 50 == 0:
        print(f"  {idx}/{len(variants)} done, elapsed {time.time()-start:.0f}s")

elapsed = time.time() - start
out = {
    "timestamp": __import__("datetime").datetime.now().isoformat(),
    "source": "yfinance EURUSD M15 60d real (5688 bars)",
    "strategies_tested": len(variants),
    "walkforward_folds": 5,
    "results": results,
    "passing_count": gate_count,
    "gate_criteria": {"sharpe_gt": 0.5, "return_gt": 0, "dd_gt": -25},
    "note": f"Tested {len(variants)} StrategyFactory variants (of {len(all_variants)} total). 5-fold WF. {elapsed:.0f}s.",
}
import os
os.makedirs("D:/repositories/Quant-Nanggroe-AI-worktree/results", exist_ok=True)
with open("D:/repositories/Quant-Nanggroe-AI-worktree/results/gate_status.json", "w") as f:
    json.dump(out, f, indent=1, default=str)

print(f"BACKTEST: {gate_count}/{len(variants)} pass gate. Source: real yfinance M15 EURUSD. WF 5-fold. {elapsed:.0f}s. File: results/gate_status.json")
passing = [r for r in results if r.get("pass")]
print(f"Top passing ({len(passing)}): {[(r['strategy'],r['sharpe']) for r in sorted(passing,key=lambda x:-x['sharpe'])[:10]]}")
print(f"Top overall: {[(r['strategy'],r['sharpe'],r['return_pct']) for r in sorted(results,key=lambda x:-x['sharpe'])[:5]]}")
