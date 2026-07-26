"""QNA Phase-2 — Backtest ALL registered strategies on REAL data, gate them.

Real data: yfinance EURUSD=X M15, 60d window (max free horizon) -> ~5666 bars.
Vectorized path for strategies exposing generate_signals(); throttled per-bar
path (every K bars) for pure generate_signal() strategies (O(n^2) guard).
Walk-forward 5-fold per strategy. Gate: Sharpe>0.5, Return>0%, DD>-25%.
Writes results/gate_status.json.
"""
import sys, json, time, logging
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd, yfinance as yf
logging.basicConfig(level=logging.ERROR)
ROOT = Path(r"D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, str(ROOT))
RESULT = ROOT / "results"; RESULT.mkdir(exist_ok=True)
K = 20  # signal re-eval cadence (bars) for pure strategies
from quant_nanggroe.engine.strategies.base import SignalDirection

# ── 1. REAL DATA ────────────────────────────────────────────────
CACHE = Path(r"E:/scratchpad/eurusd_m15_60d.csv")
if CACHE.exists():
    df = pd.read_csv(CACHE, index_col=0, parse_dates=True)
else:
    d = yf.download("EURUSD=X", interval="15m", period="60d", auto_adjust=False, progress=False)
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close", "Volume"]].dropna()
    d.columns = [c.lower() for c in d.columns]
    d.to_csv(CACHE); df = d
close = df["close"].values.astype(float)
high = df["high"].values.astype(float)
low = df["low"].values.astype(float)
n = len(df)
tr = np.maximum(high - low, np.maximum(np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
tr[0] = high[0] - low[0]
atr = pd.Series(tr).rolling(14).mean().values

def atr_sl_tp(i, direction):
    a = atr[i] if not np.isnan(atr[i]) else (high[i] - low[i])
    if direction == 1:
        return close[i] - a * 2.0, close[i] + a * 4.0
    return close[i] + a * 2.0, close[i] - a * 4.0

# ── 2. BACKTEST ENGINE (event-driven SL/TP) ───────────────────
def run_backtest(entry, sl, tp, c, a):
    m = len(c); cap = 1000.0; eq = np.empty(m); pos = 0; ep = esl = etp = 0.0
    trades = wins = 0; pnl_sum = 0.0
    for i in range(m):
        p = c[i]
        if pos != 0:
            if pos == 1:
                if p <= esl: pnl = (esl - ep) / ep; cap += pnl * cap; pos = 0; trades += 1; pnl_sum += pnl; wins += 1 if pnl > 0 else 0
                elif p >= etp: pnl = (etp - ep) / ep; cap += pnl * cap; pos = 0; trades += 1; pnl_sum += pnl; wins += 1 if pnl > 0 else 0
            else:
                if p >= esl: pnl = (ep - esl) / ep; cap += pnl * cap; pos = 0; trades += 1; pnl_sum += pnl; wins += 1 if pnl > 0 else 0
                elif p <= etp: pnl = (ep - etp) / ep; cap += pnl * cap; pos = 0; trades += 1; pnl_sum += pnl; wins += 1 if pnl > 0 else 0
        if pos == 0 and not np.isnan(entry[i]):
            e = int(entry[i])
            if e != 0 and not np.isnan(sl[i]) and not np.isnan(tp[i]):
                pos = e; ep = p; esl = sl[i]; etp = tp[i]
        eq[i] = cap + (p - ep) / ep * cap * pos if pos != 0 else cap
    if pos != 0:
        p = c[-1]; pnl = (p - ep) / ep if pos == 1 else (ep - p) / ep
        cap += pnl * cap; trades += 1; pnl_sum += pnl; wins += 1 if pnl > 0 else 0
    ret = (cap - 1000.0) / 1000.0 * 100.0
    rc = pd.Series(eq).pct_change().dropna()
    sharpe = np.sqrt(35040) * rc.mean() / rc.std() if rc.std() > 0 else 0.0
    peak = np.maximum.accumulate(eq); dd = ((eq - peak) / peak).min() * 100
    return {"return_pct": round(float(ret), 2), "sharpe": round(float(sharpe), 3),
            "max_drawdown": round(float(dd), 2), "total_trades": int(trades),
            "win_rate": round(100.0 * wins / trades, 1) if trades else 0.0}

# ── 3. SIGNAL SERIES BUILDERS ──────────────────────────────────
def build_signals_vectorized(inst):
    try:
        sig = inst.generate_signals(df)
    except Exception as e:
        return None, f"generate_signals err: {e}"
    if "entry" not in sig.columns:
        return None, "no entry column"
    entry = sig["entry"].reindex(df.index).fillna(0).values.astype(float)
    sl = sig["sl"].reindex(df.index).values.astype(float) if "sl" in sig.columns else np.full(n, np.nan)
    tp = sig["tp"].reindex(df.index).values.astype(float) if "tp" in sig.columns else np.full(n, np.nan)
    for i in range(n):
        if entry[i] != 0 and (np.isnan(sl[i]) or np.isnan(tp[i])):
            sl[i], tp[i] = atr_sl_tp(i, 1 if entry[i] > 0 else -1)
    return (entry, sl, tp), "vectorized"

def build_signals_perbar(inst):
    entry = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    for i in range(0, n, K):
        try:
            sig = inst.generate_signal(df.iloc[: i + 1])
        except Exception:
            continue
        if sig.direction == SignalDirection.BUY:
            entry[i] = 1; sl[i], tp[i] = atr_sl_tp(i, 1)
        elif sig.direction == SignalDirection.SELL:
            entry[i] = -1; sl[i], tp[i] = atr_sl_tp(i, -1)
    return (entry, sl, tp), f"coarse_perbar(K={K})"

# ── 4. WALK-FORWARD 5-FOLD ────────────────────────────────────
folds = np.array_split(np.arange(n), 5)
def gate_ok(m):
    return m["sharpe"] > 0.5 and m["return_pct"] > 0 and m["max_drawdown"] > -25

# ── 5. RUN ALL ────────────────────────────────────────────────
t0 = time.time()
from quant_nanggroe.engine.registry import list_strategies
strats = list_strategies()
results = []; passing = 0
for name, cls in strats.items():
    rec = {"strategy": name, "method": None, "error": None,
           "sharpe": 0.0, "return_pct": 0.0, "max_drawdown": 0.0,
           "total_trades": 0, "win_rate": 0.0, "gate_pass": False, "folds_passed": 0}
    try:
        inst = cls()
    except Exception as e:
        rec["error"] = f"instantiate: {e}"; results.append(rec); continue
    if hasattr(inst, "generate_signals"):
        sig, method = build_signals_vectorized(inst)
    else:
        sig, method = build_signals_perbar(inst)
    rec["method"] = method
    if sig is None:
        rec["error"] = method; results.append(rec); continue
    entry, sl, tp = sig
    full = run_backtest(entry, sl, tp, close, atr)
    rec.update({k: full[k] for k in ("return_pct", "sharpe", "max_drawdown", "total_trades", "win_rate")})
    fold_metrics = []
    fp = 0
    for f in folds:
        fm = run_backtest(entry[f[0]:f[-1] + 1], sl[f[0]:f[-1] + 1], tp[f[0]:f[-1] + 1], close[f[0]:f[-1] + 1], atr[f[0]:f[-1] + 1])
        fold_metrics.append(fm)
        if gate_ok(fm):
            fp += 1
    rec["folds_passed"] = fp
    rec["gate_pass"] = gate_ok(full)
    if rec["gate_pass"]:
        passing += 1
    results.append(rec)

out = {
    "generated_at": datetime.now().isoformat(),
    "symbol": "EURUSD", "timeframe": "M15",
    "data_source": f"yfinance EURUSD=X 60d real ({n} bars)",
    "gate": {"sharpe_min": 0.5, "return_min": 0.0, "dd_min": -25.0},
    "walk_forward_folds": 5, "signal_cadence_K": K,
    "total_strategies": len(strats), "gate_passing": passing,
    "runtime_sec": round(time.time() - t0, 1),
    "results": results,
}
(RESULT / "gate_status.json").write_text(json.dumps(out, indent=2, default=str))
print(f"DONE {len(strats)} strategies in {out['runtime_sec']}s | PASS {passing}/{len(strats)}")
for r in results:
    if r["gate_pass"]:
        print(f"  PASS {r['strategy']:35s} SR={r['sharpe']:.2f} R={r['return_pct']:+.1f}% DD={r['max_drawdown']:.1f}% folds={r['folds_passed']}/5 {r['method']}")
