"""Walk-forward validation batch for all registered strategies (real Yahoo data).

Persists:
  - data/strategy_stats/<name>.json  (schema autonomous loop reads)
  - data/walk_forward_registry.json  (WalkForwardRegistry.to_json)
"""
import json, math, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

STATS_DIR = ROOT / "data" / "strategy_stats"
STATS_DIR.mkdir(parents=True, exist_ok=True)
REG_PATH = ROOT / "data" / "walk_forward_registry.json"
CACHE = ROOT / "data" / "cached_ohlcv"
CACHE.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTC-USD"

def get_data():
    cache_file = CACHE / "BTC-USD_1d.csv"
    if cache_file.exists():
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        if len(df) > 300:
            return df
    import yfinance as yf
    raw = yf.download(SYMBOL, period="730d", interval="1d", progress=False, auto_adjust=True)
    if raw is None or len(raw) < 300:
        raise SystemExit("Yahoo download failed or too little data")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]
    df = raw[["open", "high", "low", "close", "volume"]].dropna()
    df.index.name = "date"
    df.to_csv(cache_file)
    return df

def _sig_method(strat):
    if callable(getattr(strat, "generate_signals", None)):
        return "generate_signals", "per_bar"
    if callable(getattr(strat, "generate_signal", None)):
        return "generate_signal", "regime"
    return None, None

def _norm_sig(sig):
    if sig is None:
        return 0
    if isinstance(sig, str):
        s = sig.lower()
        return 1 if s in ("buy", "long", "1", "b") else (-1 if s in ("sell", "short", "-1", "s") else 0)
    try:
        return int(np.sign(float(sig)))
    except Exception:
        return 0

def backtest(strat, df, method, mode, initial=10000.0):
    """Return metrics dict or None."""
    if mode == "per_bar":
        try:
            res = getattr(strat, method)(df)
        except Exception:
            return None
        if res is None or len(res) == 0:
            return None
        if hasattr(res, "columns"):
            col = next((c for c in ("signal", "side", "direction", "action") if c in res.columns), None)
            if col is None:
                return None
            signals = res[col].values
        else:
            signals = np.asarray(res).flatten()
    else:  # regime: single signal for whole slice
        try:
            sig = getattr(strat, method)(df)
        except Exception:
            return None
        if sig is None:
            return None
        d = getattr(sig, "direction", None) or getattr(sig, "signal_type", None)
        if hasattr(d, "value"):
            d = d.value
        d = str(d or "").lower()
        if d not in ("buy", "sell"):
            return None
        signals = np.full(len(df), 1 if d == "buy" else -1)

    equity = initial; peak = initial; max_dd = 0.0
    trades = 0; wins = 0; pnl_list = []
    pos_open = False; pos_price = 0.0; pos_qty = 0.0; pos_side = 1.0
    closes = df["close"].values
    n = len(df)
    for i in range(1, n):
        price = float(closes[i])
        sig = _norm_sig(signals[i]) if i < len(signals) else 0
        if not pos_open and sig != 0:
            pos_open = True; pos_side = 1.0 if sig > 0 else -1.0
            pos_price = price; pos_qty = equity * 0.95 / price
        elif pos_open:
            ret = (price - pos_price) / pos_price * pos_side
            cur = equity * (1 + ret)
            peak = max(peak, cur)
            max_dd = min(max_dd, (cur - peak) / peak)
            if (sig != 0 and sig != pos_side) or ret <= -0.02 or i == n - 1:
                pnl = (price - pos_price) * pos_qty * pos_side
                equity += pnl; trades += 1
                if pnl > 0: wins += 1
                pnl_list.append(pnl); pos_open = False
    if trades == 0:
        return None
    # Sharpe on fractional per-trade returns (annualized approx)
    rets = np.array(pnl_list) / initial
    if len(rets) > 1:
        sharpe = float(np.mean(rets) / max(np.std(rets), 1e-6) * math.sqrt(252))
    else:
        sharpe = float(np.sign(rets[0]) * min(abs(rets[0]) * math.sqrt(252) * 10, 3.0))
    sharpe = max(min(sharpe, 20.0), -20.0)
    return {
        "sharpe": round(float(sharpe), 4),
        "return_pct": round((equity - initial) / initial * 100, 2),
        "max_drawdown": round(float(max_dd), 4),
        "win_rate": round(wins / trades, 4),
        "total_trades": trades,
        "total_pnl": round(equity - initial, 2),
        "equity": round(equity, 2),
    }

def main():
    from quant_nanggroe.engine.strategies import create_strategy, list_strategies
    from quant_nanggroe.engine.strategy.registry import WalkForwardRegistry, WalkForwardResult

    df = get_data()
    print(f"Data: {SYMBOL} {len(df)} daily bars {df.index[0].date()} .. {df.index[-1].date()}")

    names = sorted(list_strategies())
    print(f"Strategies registered: {len(names)}")

    # walk-forward folds: rolling train 252 / test 63
    TRAIN, TEST = 252, 63
    folds = []
    start = 0
    while start + TRAIN + TEST <= len(df):
        folds.append((start, start + TRAIN, start + TRAIN, min(start + TRAIN + TEST, len(df))))
        start += TEST
    print(f"WF folds: {len(folds)}")

    reg = WalkForwardRegistry()
    written = 0; validated = 0; failed = []
    t0 = time.time()
    for idx, name in enumerate(names):
        try:
            strat = create_strategy(name)
        except Exception as e:
            failed.append((name, f"create failed: {e}")); strat = None
        if strat is None:
            failed.append((name, "create returned None"))
            continue
        method, mode = _sig_method(strat)
        if method is None:
            failed.append((name, "no signal method"))
            continue

        # full-sample backtest (in-sample reference)
        full = backtest(strat, df, method, mode)

        reg.register(name, description="WF validated on BTC-USD daily (Yahoo)", timeframe="1d",
                     asset_classes=["crypto"])
        oos_sharpes = []; wf_records = 0
        for wi, (ts, te, os_, oe) in enumerate(folds):
            train_df = df.iloc[ts:te]; test_df = df.iloc[os_:oe]
            try:
                s2 = create_strategy(name)
                is_m = backtest(s2, train_df, method, mode)
                s3 = create_strategy(name)
                oos_m = backtest(s3, test_df, method, mode)
            except Exception:
                continue
            if oos_m is None:
                continue
            is_m = is_m or {"sharpe": 0.0, "return_pct": 0.0, "max_drawdown": 0.0}
            r = WalkForwardResult(
                window_index=wi,
                train_start=str(train_df.index[0].date()), train_end=str(train_df.index[-1].date()),
                test_start=str(test_df.index[0].date()), test_end=str(test_df.index[-1].date()),
                train_sharpe=float(is_m["sharpe"]), test_sharpe=float(oos_m["sharpe"]),
                train_return=float(is_m["return_pct"]), test_return=float(oos_m["return_pct"]),
                train_max_dd=float(is_m["max_drawdown"]), test_max_dd=float(oos_m["max_drawdown"]),
            )
            reg.record_walk_forward(name, r)
            oos_sharpes.append(float(oos_m["sharpe"]))
            wf_records += 1

        avg_oos = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        status = "validated" if wf_records >= 2 else ("insufficient_folds" if wf_records else "no_signals")
        base = full or {"sharpe": avg_oos, "return_pct": 0.0, "max_drawdown": 0.0,
                        "win_rate": 0.0, "total_trades": 0, "total_pnl": 0.0, "equity": 10000.0}
        stats = {
            "strategy": name,
            "sharpe": round(avg_oos, 4),          # OOS sharpe = headline
            "avg_sharpe": round(avg_oos, 4),
            "insample_sharpe": base["sharpe"],
            "win_rate": base["win_rate"],
            "total_trades": base["total_trades"],
            "total_pnl": base["total_pnl"],
            "equity": base["equity"],
            "max_drawdown": base["max_drawdown"],
            "oos_sharpes": [round(s, 4) for s in oos_sharpes],
            "wf_windows": wf_records,
            "validation_status": status,
            "symbol": SYMBOL,
            "data_bars": len(df),
            "generated_at": pd.Timestamp.utcnow().isoformat(),
            "source": "scripts/run_wf_validation.py",
        }
        (STATS_DIR / f"{name}.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
        written += 1
        if wf_records:
            validated += 1
        print(f"[{idx+1}/{len(names)}] {name}: folds={wf_records} avg_oos_sharpe={avg_oos:.3f} status={status} ({time.time()-t0:.0f}s)")

    reg.to_json(str(REG_PATH))
    print(f"\nDONE in {time.time()-t0:.0f}s")
    print(f"stats files written: {written} -> {STATS_DIR}")
    print(f"validated (>=1 OOS fold): {validated}")
    print(f"registry saved: {REG_PATH} ({len(reg.list())} strategies)")
    if failed:
        print(f"failed/skipped ({len(failed)}):")
        for n, r in failed:
            print(f"  - {n}: {r}")

if __name__ == "__main__":
    main()
