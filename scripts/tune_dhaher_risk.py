"""QNA WAR PLAN Phase 5 - Real risk-param tune on dhaher_system (the only
strategy emitting vectorized entry+sl+tp on real EURUSD 15m).

Tunes the THREE task params against REAL data (yfinance, fail-closed):
  - dynamic lot sizing  : risk_per_trade in {0.001, 0.0025, 0.005}  (<=0.5% constitutional)
  - SL multiplier       : atr_mult      in {1.0, 1.2, 1.5, 2.0}
  - TP multiplier       : rr_min        in {2.0, 2.5, 3.0, 4.0}  (TP = sl_dist * rr_min)
Backtest honors the strategy's native sl/tp columns (real exit logic, no mock).
Gate: Sharpe>0.5, Return>0, DD>-25%. Best = gate-passers max Sharpe; fallback
keeps current defaults if nothing passes.
"""
from __future__ import annotations
import sys, os, json, time, traceback
from pathlib import Path
from datetime import datetime

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
sys.path.insert(0, ROOT)
os.environ["PYTHONPATH"] = ROOT

import numpy as np
import pandas as pd
import yfinance as yf
from quant_nanggroe.engine.registry import list_strategies

GATE_SHARPE = 0.5
GATE_RET = 0.0
GATE_DD = -25.0

RISK_GRID = [0.001, 0.0025, 0.005]
SL_GRID = [1.0, 1.2, 1.5, 2.0]
RR_GRID = [2.0, 2.5, 3.0, 4.0]


def load_real():
    df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
    if df is None or len(df) == 0:
        raise RuntimeError("yfinance returned no EURUSD data")
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "date"
    if len(df) < 200:
        raise RuntimeError(f"too few bars: {len(df)}")
    return df


def backtest_native(df, r, rp):
    """Backtest honoring strategy native entry/sl/tp columns. Single position."""
    close = df["close"].values.astype(float)
    n = len(close)
    entry = r["entry"].values.astype(float)
    psl = r["sl"].values.astype(float)
    ptp = r["tp"].values.astype(float)
    eq = 10000.0; peak = eq; maxdd = 0.0; trades = 0; wins = 0; pnl = []
    pos = False; side = 0.0; entry_p = 0.0; stop_p = 0.0
    for i in range(1, n):
        e = entry[i]; p = close[i]; s = psl[i]; t = ptp[i]
        if not pos and e != 0:
            if not np.isfinite(s) or s == 0:
                continue
            dist = abs(e - s)
            if dist <= 0:
                continue
            units = (eq * rp) / dist
            pos = True; side = float(e); entry_p = e; stop_p = s
            continue
        if pos:
            hit_tp = (side > 0 and p >= t) or (side < 0 and p <= t)
            hit_sl = (side > 0 and p <= stop_p) or (side < 0 and p >= stop_p)
            rev = (e != 0 and np.sign(e) != np.sign(side))
            if hit_tp or hit_sl or rev or i == n - 1:
                exit_p = t if hit_tp else (stop_p if hit_sl else p)
                pl = (exit_p - entry_p) * units * side
                eq += pl; trades += 1; wins += 1 if pl > 0 else 0; pnl.append(pl)
                peak = max(peak, eq); maxdd = min(maxdd, (eq - peak) / peak)
                pos = False
    if trades == 0:
        return None
    ret = (eq - 10000.0) / 10000.0 * 100
    wr = wins / trades
    mean = np.mean(pnl); std = np.std(pnl) if trades > 1 else 0.0
    sharpe = (mean / std) * np.sqrt(252) if std > 0 else 0.0
    return {"sharpe": float(sharpe), "return_pct": float(ret), "max_dd_pct": float(maxdd * 100),
            "win_rate": float(wr * 100), "trades": int(trades)}


def main():
    t0 = time.time()
    df = load_real()
    S = list_strategies()
    cls = S["dhaher_system"]
    print(f"bars={len(df)}", flush=True)

    results = []
    baseline = {"risk_per_trade": 0.01, "atr_mult": 1.2, "rr_min": 2.5}
    for rp in RISK_GRID:
        for slm in SL_GRID:
            for rrm in RR_GRID:
                try:
                    inst = cls(risk_per_trade=rp, atr_mult=slm, rr_min=rrm, min_confluence=2)
                    r = inst.generate_signals(df)
                except Exception as e:
                    print(f"  ERR rp={rp} sl={slm} rr={rrm}: {e}", flush=True)
                    continue
                if r is None or "entry" not in r.columns:
                    continue
                m = backtest_native(df, r, rp)
                if m is None:
                    continue
                passed = (m["sharpe"] > GATE_SHARPE and m["return_pct"] > GATE_RET and m["max_dd_pct"] > GATE_DD)
                results.append({"rp": rp, "sl": slm, "rr": rrm, **m, "pass": passed})
                print(f"  rp={rp} sl={slm} rr={rrm} -> sh={m['sharpe']:.2f} ret={m['return_pct']:.1f}% dd={m['max_dd_pct']:.1f}% wr={m['win_rate']:.0f}% t={m['trades']} pass={'Y' if passed else 'N'}", flush=True)

    passers = [x for x in results if x["pass"]]
    passers.sort(key=lambda x: x["sharpe"], reverse=True)
    best = passers[0] if passers else (results[0] if results else None)

    out = {
        "timestamp": datetime.now().isoformat(),
        "symbol": "EURUSD", "timeframe": "M15", "bars": len(df),
        "baseline": baseline,
        "best": best,
        "passers": len(passers), "total_combos": len(results),
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(ROOT, "results").mkdir(exist_ok=True)
    with open(Path(ROOT, "results", "tune_dhaher_risk.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("DONE best=", json.dumps(best) if best else "NONE", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
