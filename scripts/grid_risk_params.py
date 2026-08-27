"""Grid-search QNA risk params on REAL data (BTC-USD 1h, 365d via yfinance).

Tunes the strategy-AGNOSTIC risk layer:
  - kelly_fraction (fractional Kelly factor applied to raw Kelly)
  - sl_atr_mult   (SL distance = mult * ATR)
  - rr            (TP = rr * SL distance)

Uses two independent signal generators on the SAME real price path so the
picked params are robust across regimes (mean-reversion + trend-follow).
Evidence only — no mock. Report best combo by Sharpe subject to
gate (Ret>0, DD>-25%, Sharpe>0.5).
"""
from __future__ import annotations
import sys, numpy as np, pandas as pd
sys.path.insert(0, r"D:/repositories/Quant-Nanggroe-AI-worktree")

try:
    import yfinance as yf
except Exception as e:
    print("NO_YFINANCE", e); sys.exit(2)

def load():
    df = yf.download("BTC-USD", period="365d", interval="1h", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        close = df[("Close",)] if ("Close",) in df.columns else df.xs("Close", axis=1, level=0)
    else:
        close = df["Close"]
    df = close.squeeze().to_frame("close")
    df = df.dropna()
    df["ret"] = df["close"].pct_change()
    # ATR(14)
    h = df["close"]; l = df["close"]; c = df["close"].shift(1)
    tr = pd.concat([(h-l).abs(), (h-c).abs(), (l-c).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    return df.dropna()

def signals(df):
    # Mean-reversion: z-score of 20-bar return
    r = df["ret"].rolling(20).mean(); s = df["ret"].rolling(20).std()
    z = (df["ret"] - r) / s
    mr = np.where(z > 2, -1, np.where(z < -2, 1, 0))
    # Trend-follow: 20/50 EMA cross
    e1 = df["close"].ewm(span=20).mean(); e2 = df["close"].ewm(span=50).mean()
    tf = np.where(e1 > e2, 1, np.where(e1 < e2, -1, 0))
    return {"mr": mr, "tf": tf}

def backtest(df, sig, kelly_f, sl_mult, rr):
    MAXRISK = 0.005  # constitutional MAX_RISK_PER_TRADE
    eq = 10000.0; equity = [eq]; trades = 0
    pos = 0; entry = 0.0; sl = 0.0; tp = 0.0; units = 0.0
    closes = df["close"].values; highs = df["close"].values; lows = df["close"].values
    atr = df["atr"].values
    n = len(closes)
    for i in range(1, n):
        p = closes[i-1]
        # check exit on prior position using this bar's range
        if pos != 0:
            hi = highs[i]; lo = lows[i]
            hit_sl = (pos == 1 and lo <= sl) or (pos == -1 and hi >= sl)
            hit_tp = (pos == 1 and hi >= tp) or (pos == -1 and lo <= tp)
            if hit_tp or hit_sl:
                px = tp if hit_tp else sl
                pnl = (px - entry) * units if pos == 1 else (entry - px) * units
                eq += pnl; trades += 1
                pos = 0
        # new signal
        s = sig[i]
        if s != 0 and pos == 0 and atr[i] > 0:
            entry = closes[i]
            dist = sl_mult * atr[i]
            sl = entry - dist if s == 1 else entry + dist
            tp = entry + dist * rr if s == 1 else entry - dist * rr
            # kelly-based risk: kelly_f fraction of equity, capped at MAXRISK
            risk = min(kelly_f, MAXRISK) * eq
            units = risk / dist
            pos = s
        equity.append(eq)
    eqc = pd.Series(equity)
    rets = eqc.pct_change().dropna()
    if rets.std() == 0:
        return dict(sharpe=0, ret=0, dd=-99, trades=trades)
    sharpe = rets.mean() / rets.std() * np.sqrt(365*24)
    total_ret = eqc.iloc[-1]/eqc.iloc[0] - 1
    dd = (eqc/eqc.cummax() - 1).min()
    return dict(sharpe=sharpe, ret=total_ret, dd=dd, trades=trades)

def main():
    df = load()
    sigs = signals(df)
    grid_k = [0.10, 0.25, 0.50]
    grid_sl = [1.0, 1.2, 1.5, 2.0, 2.5]
    grid_rr = [2.0, 2.5, 3.0]
    rows = []
    for k in grid_k:
        for slm in grid_sl:
            for rr in grid_rr:
                res = {name: backtest(df, s, k, slm, rr) for name, s in sigs.items()}
                sh = min(r["sharpe"] for r in res.values())  # worst-case robustness
                ret = min(r["ret"] for r in res.values())
                dd = min(r["dd"] for r in res.values())
                rows.append((k, slm, rr, sh, ret, dd,
                             sum(r["trades"] for r in res.values())))
    # gate: sharpe>0.5, ret>0, dd>-0.25 ; rank by worst-case sharpe
    ok = [r for r in rows if r[3] > 0.5 and r[4] > 0 and r[5] > -0.25]
    ok.sort(key=lambda r: -r[3])
    print("TOP5 (kelly,sl_mult,rr,worst_sharpe,min_ret,min_dd,trades):")
    for r in ok[:5]:
        print(f"  k={r[0]} sl={r[1]} rr={r[2]} SR={r[3]:.3f} RET={r[4]:.3f} DD={r[5]:.3f} n={r[6]}")
    if ok:
        b = ok[0]
        print(f"BEST kelly={b[0]} sl_mult={b[1]} rr={b[2]}")
    else:
        print("NO_COMBO_PASSED_GATE")

if __name__ == "__main__":
    main()
