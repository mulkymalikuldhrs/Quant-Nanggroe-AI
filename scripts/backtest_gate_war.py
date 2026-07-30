"""QNA WAR PLAN Phase 2 — Real Backtest Validation (gate_status.json).

Backtests every registered strategy on REAL yfinance EURUSD 15m data.
Walk-forward 5-fold per strategy. Gate: Sharpe>0.5, Return>0%, DD>-25%.
Fail-closed: if real data fetch fails, abort (NO random-walk fallback).
Writes results/gate_status.json with {strategy, sharpe, return_pct, max_dd_pct, wf_sharpe, pass}.
"""
import sys, os, json, time, traceback
from pathlib import Path
from datetime import datetime

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
sys.path.insert(0, ROOT)
os.environ["PYTHONPATH"] = ROOT

import numpy as np
import pandas as pd
import yfinance as yf
from quant_nanggroe.engine.strategies.registry import list_strategies

W = 300  # trailing window for singular generate_signal strategies (keeps per-bar O(n))


def load_real_eurusd():
    """REAL EURUSD 15m via yfinance. Fail-closed — no synthetic fallback."""
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


def to_int_sign(v):
    if v is None:
        return 0
    if isinstance(v, str):
        s = v.lower()
        if s in ("buy", "long", "1", "b"):
            return 1
        if s in ("sell", "short", "-1", "s"):
            return -1
        return 0
    return int(np.sign(v))


def signal_series(inst, df):
    """Return np.array of -1/0/1 aligned to df rows. None if no usable signal."""
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
        for i, v in enumerate(arr):
            if i >= n:
                break
            sig[i] = to_int_sign(v)
        return sig
    # singular generate_signal — per-bar with trailing window
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
        sig[i] = to_int_sign(d)
    return sig


def backtest_series(close, sig, initial=10000.0, sl=0.02):
    eq = initial
    peak = initial
    maxdd = 0.0
    trades = 0
    wins = 0
    pnl_list = []
    pos_open = False
    pos_price = 0.0
    pos_qty = 0.0
    pos_side = 1.0
    for i in range(1, len(close)):
        price = close[i]
        s = sig[i]
        if not pos_open and s != 0:
            pos_open = True
            pos_side = float(s)
            pos_price = price
            pos_qty = eq * 0.95 / price
        elif pos_open:
            ret = (price - pos_price) / pos_price * pos_side
            ceq = eq * (1 + ret)
            peak = max(peak, ceq)
            dd = (ceq - peak) / peak
            maxdd = min(maxdd, dd)
            if (s != 0 and np.sign(s) != np.sign(pos_side)) or ret <= -sl or i == len(close) - 1:
                pnl = (price - pos_price) * pos_qty * pos_side
                eq += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                pnl_list.append(pnl)
                pos_open = False
    if trades == 0:
        return None
    ret_pct = (eq - initial) / initial * 100
    wr = wins / max(trades, 1)
    mean = np.mean(pnl_list)
    std = np.std(pnl_list) if len(pnl_list) > 1 else 0.0
    sharpe = (mean / max(std, 1e-9)) * np.sqrt(252) if std > 0 else 0.0
    return {"return_pct": ret_pct, "sharpe": sharpe, "max_dd_pct": maxdd * 100, "win_rate": wr * 100, "trades": trades}


def walk_forward(close, sig, n_folds=5, test_ratio=0.3):
    n = len(close)
    fold_size = int(n * test_ratio)
    sharpes = []
    for f in range(n_folds):
        ts = n - fold_size * (n_folds - f)
        te = ts + fold_size
        if ts < int(n * 0.1) or te > n:
            continue
        r = backtest_series(close[ts:te], sig[ts:te])
        if r:
            sharpes.append(r["sharpe"])
    return float(np.mean(sharpes)) if sharpes else 0.0


def gate(m):
    if m is None:
        return False
    return m["sharpe"] > 0.5 and m["return_pct"] > 0 and m["max_dd_pct"] > -25


def main():
    t0 = time.time()
    lock = Path(ROOT) / "results" / ".bt_lock"
    lock.parent.mkdir(exist_ok=True)
    if lock.exists():
        age = time.time() - lock.stat().st_mtime
        if age < 7200:  # another run active < 2h
            print(f"SKIP: lock fresh ({age:.0f}s old)")
            return
    lock.write_text(str(os.getpid()))
    try:
        df = load_real_eurusd()
        close = df["close"].values.astype(float)
        strategies = list_strategies()
        results = []
        for name, cls in strategies.items():
            try:
                inst = cls()
            except Exception:
                results.append({"strategy": name, "sharpe": 0.0, "return_pct": 0.0,
                                "max_dd_pct": 0.0, "wf_sharpe": 0.0, "pass": False, "status": "instantiate_error"})
                continue
            sig = signal_series(inst, df)
            if sig is None:
                results.append({"strategy": name, "sharpe": 0.0, "return_pct": 0.0,
                                "max_dd_pct": 0.0, "wf_sharpe": 0.0, "pass": False, "status": "no_signal"})
                continue
            m = backtest_series(close, sig)
            if m is None:
                results.append({"strategy": name, "sharpe": 0.0, "return_pct": 0.0,
                                "max_dd_pct": 0.0, "wf_sharpe": 0.0, "pass": False, "status": "flat"})
                continue
            wf = walk_forward(close, sig)
            passed = gate(m)
            results.append({
                "strategy": name,
                "sharpe": round(float(m["sharpe"]), 3),
                "return_pct": round(float(m["return_pct"]), 2),
                "max_dd_pct": round(float(m["max_dd_pct"]), 2),
                "wf_sharpe": round(wf, 3),
                "pass": bool(passed),
                "status": "ok",
            })
        out = {
            "timestamp": datetime.now().isoformat(),
            "symbol": "EURUSD",
            "timeframe": "M15",
            "bars": len(df),
            "source": "yfinance EURUSD=X (real, 60d)",
            "registered": len(strategies),
            "archive_registered": sum(1 for k in strategies if k.startswith("archive_")),
            "passed": sum(1 for r in results if r["pass"]),
            "results": results,
        }
        out_path = Path(ROOT) / "results" / "gate_status.json"
        out_path.write_text(json.dumps(out, indent=2, default=str))
        print(f"DONE {len(strategies)} strategies in {time.time()-t0:.0f}s | PASSED={out['passed']}/{len(strategies)} | wrote {out_path}")
    finally:
        try:
            lock.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
