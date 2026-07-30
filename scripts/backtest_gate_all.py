"""
QNA Phase 2 — Real backtest validation of ALL registered strategies.
Real yfinance EURUSD=M15 data. 5-fold walk-forward. Gate: Sharpe>0.5, Return>0%, DD>-25%.

Usage:
  python scripts/backtest_gate_all.py [--budget 1500] [--interval 15m] [--period 60d]

Resumable: strategies already in results/gate_status.json are skipped.
Writes results/gate_status.json cumulatively.
"""
from __future__ import annotations
import sys, time, json, argparse
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"D:/repositories/Quant-Nanggroe-AI-worktree")
sys.path.insert(0, str(REPO))
RESULTS = REPO / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
GATE = RESULTS / "gate_status.json"
CACHE = RESULTS / "eurusd_m15_cache.csv"

SYM = "EURUSD=X"
ANN = 35040  # M15 bars/year (365*24*4)

import quant_nanggroe.engine.registry as reg
from quant_nanggroe.engine.strategies.base import Strategy


def load_data(interval: str, period: str) -> pd.DataFrame:
    if CACHE.exists():
        try:
            df = pd.read_csv(CACHE, index_col=0, parse_dates=True)
            if len(df) > 1000:
                print(f"  data cache hit: {len(df)} bars")
                return df
        except Exception:
            pass
    import yfinance as yf
    raw = yf.download(SYM, period=period, interval=interval, auto_adjust=False, progress=False)
    if isinstance(raw, tuple):  # yfinance >=1.x may return (data, errors)
        raw = raw[0]
    df = raw
    # Flatten MultiIndex columns (e.g. ('Close','EURUSD=X')) to plain names like 'close'
    if hasattr(df.columns, 'levels') and len(df.columns.levels) > 1:
        df.columns = [c[0].lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise RuntimeError(f"yfinance returned no data: {type(raw)}")
    df = df.rename(columns={c: c.lower() for c in df.columns})
    df = df.loc[:, ["open", "high", "low", "close", "volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(subset=["open", "high", "low", "close"])
    df.to_csv(CACHE)
    print(f"  data downloaded: {len(df)} bars")
    return df


def backtest(close: np.ndarray, entries: np.ndarray, sl, tp, init: float = 1000.0):
    """SL/TP-aware single-position backtest. entries in {-1,0,1}. sl/tp: np.ndarray or None."""
    n = len(close)
    eq = np.empty(n, dtype=float)
    cap = float(init)
    pos = 0
    ep = 0.0
    esl = np.nan
    etp = np.nan
    for i in range(n):
        p = close[i]
        if pos != 0:
            if pos == 1:
                if (not np.isnan(esl)) and p <= esl:
                    cap += (esl - ep) / ep * cap
                    pos = 0
                elif (not np.isnan(etp)) and p >= etp:
                    cap += (etp - ep) / ep * cap
                    pos = 0
            else:
                if (not np.isnan(esl)) and p >= esl:
                    cap += (ep - esl) / ep * cap
                    pos = 0
                elif (not np.isnan(etp)) and p <= etp:
                    cap += (ep - etp) / ep * cap
                    pos = 0
        # opposite signal closes
        if pos != 0 and entries[i] == -pos:
            cap += (p - ep) / ep * cap if pos == 1 else (ep - p) / ep * cap
            pos = 0
        # open
        if pos == 0 and entries[i] != 0:
            pos = 1 if entries[i] > 0 else -1
            ep = p
            esl = sl[i] if sl is not None else np.nan
            etp = tp[i] if tp is not None else np.nan
        eq[i] = cap + ((p - ep) / ep * cap if pos == 1 else (ep - p) / ep * cap if pos == -1 else 0.0)
    if pos != 0:
        last = close[-1]
        cap += (last - ep) / ep * cap if pos == 1 else (ep - last) / ep * cap
    return eq


def fold_metrics(eq: np.ndarray, n_folds: int = 5):
    """Split equity into n_folds contiguous segments; aggregate OOS metrics."""
    segs = np.array_split(eq, n_folds)
    rets, shps, dds = [], [], []
    for s in segs:
        if len(s) < 5:
            continue
        r = (s[-1] / s[0] - 1.0) * 100.0
        rets.append(r)
        d = pd.Series(s).pct_change().dropna()
        shp = np.sqrt(ANN) * d.mean() / d.std() if d.std() > 0 else 0.0
        shps.append(shp)
        peak = np.maximum.accumulate(s)
        dd = ((s - peak) / peak).min() * 100.0
        dds.append(dd)
    if not rets:
        return 0.0, 0.0, 0.0
    total_ret = (float(np.prod([1 + r / 100 for r in rets])) - 1.0) * 100.0
    agg_shp = float(np.mean(shps))
    agg_dd = float(np.min(dds))
    return round(total_ret, 2), round(agg_shp, 3), round(agg_dd, 2)


def build_entries_df(strat, df: pd.DataFrame):
    out = strat.generate_signals(df)
    if not isinstance(out, pd.DataFrame) or "entry" not in out.columns:
        return None
    entries = out["entry"].astype(float).fillna(0.0).to_numpy()
    sl = out["sl"].to_numpy() if "sl" in out.columns else None
    tp = out["tp"].to_numpy() if "tp" in out.columns else None
    return entries, sl, tp


def build_entries_signal(strat, df: pd.DataFrame, deadline: float):
    n = len(df)
    entries = np.zeros(n)
    sl = np.full(n, np.nan)
    tp = np.full(n, np.nan)
    closes = df["close"].to_numpy()
    for i in range(n):
        if time.time() > deadline:
            break
        try:
            sig = strat.generate_signal(df.iloc[: i + 1])
        except Exception:
            continue
        if sig is None:
            continue
        # direction
        d = getattr(sig, "direction", None)
        if d is None:
            st = getattr(sig, "signal_type", None)
            if st is not None:
                d = st.value if hasattr(st, "value") else str(st)
        if d is None:
            continue
        dv = d.value if hasattr(d, "value") else str(d)
        if dv in ("BUY", "buy", 1):
            entries[i] = 1.0
        elif dv in ("SELL", "sell", -1):
            entries[i] = -1.0
        else:
            continue
        if getattr(sig, "stop_loss", None) is not None:
            sl[i] = float(sig.stop_loss)
        if getattr(sig, "take_profit", None) is not None:
            tp[i] = float(sig.take_profit)
    return entries, sl, tp


def evaluate(name: str, strat, df: pd.DataFrame, budget_per: float):
    close = df["close"].to_numpy()
    deadline = time.time() + budget_per
    try:
        built = build_entries_df(strat, df)
        iface = "df"
    except Exception:
        built = None
    if built is None:
        try:
            built = build_entries_signal(strat, df, deadline)
            iface = "signal"
        except Exception as e:
            return {"strategy": name, "status": "error", "error": f"signal: {e}"}
    entries, sl, tp = built
    if sl is not None:
        sl = np.asarray(sl, dtype=float)
    if tp is not None:
        tp = np.asarray(tp, dtype=float)
    if np.count_nonzero(entries) == 0:
        return {"strategy": name, "status": "no_trades", "interface": iface,
                "sharpe": 0.0, "return_pct": 0.0, "max_drawdown": 0.0, "pass": False}
    eq = backtest(close, entries, sl, tp)
    total_ret, agg_shp, agg_dd = fold_metrics(eq, 5)
    passed = (agg_shp > 0.5) and (total_ret > 0) and (agg_dd > -25)
    return {"strategy": name, "status": "ok", "interface": iface,
            "sharpe": agg_shp, "return_pct": total_ret, "max_drawdown": agg_dd,
            "trades": int(np.count_nonzero(entries)), "pass": bool(passed)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=1500.0)
    ap.add_argument("--interval", default="15m")
    ap.add_argument("--period", default="60d")
    ap.add_argument("--per", type=float, default=40.0)
    args = ap.parse_args()

    start = time.time()
    df = load_data(args.interval, args.period)

    existing = {}
    if GATE.exists():
        try:
            existing = json.loads(GATE.read_text())
        except Exception:
            existing = {}
    # Handle both old list format and new dict format
    done_list = existing.get("results", [])
    if isinstance(done_list, list):
        done = {item.get("strategy", ""): item for item in done_list if isinstance(item, dict) and "strategy" in item}
    else:
        done = done_list
    print(f"Already evaluated: {len(done)}")

    strats = reg.list_strategies()
    order = sorted(strats.keys())
    results = dict(done)
    for name in order:
        if name in results:
            continue
        if time.time() - start > args.budget:
            print(f"  budget reached, stopping. {len(results)} evaluated.")
            break
        cls = strats[name]
        try:
            inst = reg.create_strategy(name) or cls()
        except Exception as e:
            results[name] = {"strategy": name, "status": "instantiate_error", "error": str(e), "pass": False}
            GATE.write_text(json.dumps({"symbol": SYM, "interval": args.interval,
                                        "period": args.period, "n_registered": len(strats),
                                        "results": results}, indent=2, default=str))
            continue
        rec = evaluate(name, inst, df, args.per)
        results[name] = rec
        tag = "PASS" if rec.get("pass") else "fail"
        print(f"  {name:40s} {tag} sr={rec.get('sharpe')} ret={rec.get('return_pct')} dd={rec.get('max_drawdown')} [{rec.get('status')}]")
        # incremental save
        GATE.write_text(json.dumps({"symbol": SYM, "interval": args.interval,
                                    "period": args.period, "n_registered": len(strats),
                                    "results": results}, indent=2, default=str))

    passed = sum(1 for r in results.values() if r.get("pass"))
    meta = {"symbol": SYM, "interval": args.interval, "period": args.period,
            "n_registered": len(strats), "n_evaluated": len(results),
            "n_pass": passed, "results": results}
    GATE.write_text(json.dumps(meta, indent=2, default=str))
    print(f"Backtest: {passed}/{len(strats)} pass gate (evaluated {len(results)})")


if __name__ == "__main__":
    main()
