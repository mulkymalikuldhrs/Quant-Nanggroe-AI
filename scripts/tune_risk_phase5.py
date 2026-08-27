"""QNA WAR PLAN Phase 5 - Real risk-parameter tuning (fangbot/OpenFang).

Grid-search GLOBAL risk knobs on REAL EURUSD 15m (yfinance, fail-closed):
  - Kelly fraction (per-trade risk, capped at constitutional 0.5%)
  - SL multiplier (x ATR) -> HARD_STOP_ATR_MULTIPLIER
  - TP multiplier (x ATR)
Supports BOTH strategy APIs: generate_signals (vectorized) and
generate_signal (per-bar, trailing window) -- matching backtest_gate_war.py.
Scans the LIVE (non-archive) strategy suite, keeps gate-passers (Sharpe>0.5,
Ret>0, DD>-25%), grid-tunes risk on the top 3, applies majority-best to globals.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
sys.path.insert(0, ROOT)
os.environ["PYTHONPATH"] = ROOT

import numpy as np
import pandas as pd
import yfinance as yf

from quant_nanggroe.engine.registry import list_strategies

MIN_TRADES = 30
GATE_SHARPE = 0.5
GATE_RET = 0.0
GATE_DD = -25.0
W = 250  # trailing window for per-bar strategies

KELLY_GRID = [0.001, 0.0025, 0.005]
SL_ATR_GRID = [2.0, 2.5, 3.0, 4.0]
TP_ATR_GRID = [3.0, 4.0, 5.0, 6.0]


def load_real_eurusd():
    df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
    if df is None or len(df) == 0:
        raise RuntimeError("yfinance returned no EURUSD data")
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "date"
    if len(df) < 300:
        raise RuntimeError(f"too few bars: {len(df)}")
    return df


def atr_arr(df, n=14):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().values


def to_int(v):
    if v is None: return 0
    if isinstance(v, str):
        s = v.lower()
        return 1 if s in ("buy", "long", "1", "b") else (-1 if s in ("sell", "short", "-1", "s") else 0)
    try:
        d = getattr(v, "value", v)
        return int(np.sign(d))
    except Exception:
        return 0


def signal_series(inst, df):
    n = len(df)
    sig = np.zeros(n, dtype=int)
    if hasattr(inst, "generate_signals"):
        try:
            res = inst.generate_signals(df)
        except Exception:
            return None
        if res is None:
            return None
        if hasattr(res, "columns"):
            col = next((c for c in ["signal", "side", "direction", "action"] if c in res.columns), None)
            if col is None:
                return None
            arr = res[col].values
        else:
            arr = np.asarray(res).flatten()
        for i, v in enumerate(arr[:n]):
            sig[i] = to_int(v)
        return sig
    # per-bar API
    if hasattr(inst, "generate_signal"):
        for i in range(1, n):
            lo = max(0, i - W)
            try:
                s = inst.generate_signal(df.iloc[lo:i + 1])
            except Exception:
                continue
            if s is None:
                continue
            d = getattr(s, "direction", None)
            if hasattr(d, "value"):
                d = d.value
            sig[i] = to_int(d)
        return sig
    return None


def backtest(df, sig, atr_v, kelly, sl_atr, tp_atr, initial=10000.0):
    close = df["close"].values.astype(float)
    n = len(close)
    eq = initial; peak = initial; maxdd = 0.0; trades = 0; wins = 0; pnl = []
    pos = False; side = 0.0; entry = 0.0; units = 0.0; sl = 0.0; tp = 0.0
    for i in range(1, n):
        s = sig[i]; p = close[i]
        if not pos and s != 0:
            a = atr_v[i]
            if not np.isfinite(a) or a <= 0:
                continue
            sl = entry - s * sl_atr * a
            tp = entry + s * tp_atr * a
            units = (eq * kelly) / (sl_atr * a)
            pos = True; side = float(s); entry = p
            continue
        if pos:
            hit_tp = (side > 0 and p >= tp) or (side < 0 and p <= tp)
            hit_sl = (side > 0 and p <= sl) or (side < 0 and p >= sl)
            exit_p = p
            if hit_tp: exit_p = tp
            elif hit_sl: exit_p = sl
            rev = (s != 0 and np.sign(s) != np.sign(side))
            if hit_tp or hit_sl or rev or i == n - 1:
                pl = (exit_p - entry) * units * side
                eq += pl; trades += 1; wins += 1 if pl > 0 else 0; pnl.append(pl)
                peak = max(peak, eq); maxdd = min(maxdd, (eq - peak) / peak)
                pos = False
    if trades == 0:
        return None
    ret = (eq - initial) / initial * 100
    wr = wins / trades
    mean = np.mean(pnl); std = np.std(pnl) if trades > 1 else 0.0
    sharpe = (mean / std) * np.sqrt(252) if std > 0 else 0.0
    return {"sharpe": sharpe, "return_pct": ret, "max_dd_pct": maxdd * 100, "win_rate": wr * 100, "trades": trades}


def main():
    t0 = time.time()
    df = load_real_eurusd()
    av = atr_arr(df)
    all_str = list_strategies()
    live = {k: v for k, v in all_str.items() if not k.startswith("archive_")}
    print(f"data_bars={len(df)} live_strategies={len(live)}", flush=True)

    baseline_passers = []
    for name, cls in live.items():
        try:
            inst = cls()
        except Exception:
            continue
        sig = signal_series(inst, df)
        if sig is None:
            continue
        nz = int((sig != 0).sum())
        if nz < 5:
            continue
        m = backtest(df, sig, av, 0.0025, 2.5, 4.0)
        if m and m["trades"] >= MIN_TRADES and m["sharpe"] > GATE_SHARPE and m["return_pct"] > GATE_RET and m["max_dd_pct"] > GATE_DD:
            baseline_passers.append((name, m["sharpe"]))
            print(f"  PASS {name} sharpe={m['sharpe']:.2f} ret={m['return_pct']:.1f}% dd={m['max_dd_pct']:.1f}% wr={m['win_rate']:.0f}% t={m['trades']}", flush=True)
    baseline_passers.sort(key=lambda x: x[1], reverse=True)
    top = [p[0] for p in baseline_passers[:3]]
    print(f"gate_passers={len(baseline_passers)} top3={top}", flush=True)

    recs = {}; per_best = []
    for name in top:
        cls = live[name]
        try:
            inst = cls()
        except Exception:
            continue
        sig = signal_series(inst, df)
        if sig is None:
            continue
        best = None
        for kelly in KELLY_GRID:
            for sl in SL_ATR_GRID:
                for tp in TP_ATR_GRID:
                    m = backtest(df, sig, av, kelly, sl, tp)
                    if not m:
                        continue
                    if m["sharpe"] > GATE_SHARPE and m["return_pct"] > GATE_RET and m["max_dd_pct"] > GATE_DD:
                        if best is None or m["sharpe"] > best["sharpe"]:
                            best = {"kelly": kelly, "sl_atr": sl, "tp_atr": tp, **m}
        if best:
            per_best.append(best); recs[name] = best
            print(f"  BEST {name}: sharpe={best['sharpe']:.2f} kelly={best['kelly']} sl={best['sl_atr']} tp={best['tp_atr']} ret={best['return_pct']:.1f}% dd={best['max_dd_pct']:.1f}%", flush=True)

    if per_best:
        g = {
            "kelly_fraction": float(np.median([b["kelly"] for b in per_best])),
            "sl_atr_multiplier": float(np.median([b["sl_atr"] for b in per_best])),
            "tp_atr_multiplier": float(np.median([b["tp_atr"] for b in per_best])),
            "n_strategies": len(per_best), "per_strategy": recs,
        }
    else:
        g = {"kelly_fraction": 0.0025, "sl_atr_multiplier": 2.5, "tp_atr_multiplier": 4.0, "n_strategies": 0, "per_strategy": {}}

    out = {
        "timestamp": datetime.now().isoformat(), "symbol": "EURUSD", "timeframe": "M15",
        "gate_passers_total": len(baseline_passers), "top3": top,
        "global_recommendation": g, "baseline": {"kelly": 0.0025, "sl_atr": 2.5, "tp_atr": 4.0},
        "elapsed_s": round(time.time() - t0, 1),
    }
    Path(ROOT, "results").mkdir(exist_ok=True)
    with open(Path(ROOT, "results", "tune_risk_phase5.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("DONE", json.dumps(g), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
