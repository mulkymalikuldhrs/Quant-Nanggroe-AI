#!/usr/bin/env python3
"""Phase 5 fangbot param optimization — grid search Kelly/SL/TP for Wyckoff + MeanReversion.
Uses yfinance EURUSD 1h data. Hermes venv required.
"""
import sys, json, math
from pathlib import Path
from datetime import datetime, timedelta

# Add QNA to path
QNA = Path(__file__).resolve().parent.parent / "quant_nanggroe"
sys.path.insert(0, str(QNA.parent))

import numpy as np
import pandas as pd
import yfinance as yf

from quant_nanggroe.engine.strategies.wyckoff import WyckoffStrategy
from quant_nanggroe.engine.strategies.mean_reversion import MeanReversionStrategy
from quant_nanggroe.engine.risk.kelly import KellyCriterion, KellyMethod, KellyParameters

# ─── Data ───────────────────────────────────────────────────────────────────
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "eurusd_h1_730d_cache.csv"

def fetch_data():
    df = pd.read_csv(DATA_FILE, parse_dates=["Datetime"], index_col="Datetime")
    df = df.rename(columns={c: c.lower().replace("adj close","adj_close") for c in df.columns})
    # Normalize to lowercase OHLCV
    col_map = {c: c.lower().replace(" ","") for c in df.columns}
    df = df.rename(columns=col_map)
    keep = [c for c in ["open","high","low","close","volume"] if c in df.columns]
    df = df[keep].dropna()
    df = df[df["volume"] >= 0]  # forex has 0 volume, keep it
    # Remove timezone for consistency
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    return df

# ─── Helpers ────────────────────────────────────────────────────────────────
def calc_atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def kelly_position_size(account, kelly_frac, sl_distance, entry_price):
    """Lot size from Kelly fraction + SL distance."""
    if sl_distance <= 0 or entry_price <= 0:
        return 0.0
    risk_amount = account * kelly_frac
    pip_value = entry_price * 0.0001  # 1 pip ≈ 0.0001 for EURUSD
    sl_pips = sl_distance / pip_value
    if sl_pips <= 0:
        return 0.0
    lot = risk_amount / (sl_pips * pip_value * 100_000)
    return max(0.01, round(lot * 100) / 100)

# ─── Backtest Engine ─────────────────────────────────────────────────────────
def backtest(df, strategy_fn, kelly_frac, sl_atr_mult, tp_atr_mult, sizing_mode="kelly"):
    START_BAL = 10_000.0
    balance = START_BAL
    position = 0.0
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    peak = balance
    trades = []
    equity_curve = [balance]

    atr_series = calc_atr(df)
    min_bars = 30

    for i in range(min_bars, len(df)):
        row = df.iloc[i]
        atr = atr_series.iloc[i]
        if pd.isna(atr) or atr <= 0:
            equity_curve.append(balance)
            continue

        sub = df.iloc[:i+1]
        sig = strategy_fn(sub, sl_atr_mult=sl_atr_mult, tp_atr_mult=tp_atr_mult)
        if sig is None:
            sig = {"direction": "hold"}

        direction = sig.get("direction", "hold")
        raw_sl = sig.get("stop_loss", 0)
        raw_tp = sig.get("take_profit", 0)

        # Check SL/TP hit first (intrabar approximation)
        if position != 0:
            hit_sl = (position > 0 and row["low"] <= sl_price) or \
                     (position < 0 and row["high"] >= sl_price)
            hit_tp = (position > 0 and row["high"] >= tp_price) or \
                     (position < 0 and row["low"] <= tp_price)
            exit_price = 0
            if hit_sl and hit_tp:
                exit_price = sl_price  # SL hits first (conservative)
            elif hit_sl:
                exit_price = sl_price
            elif hit_tp:
                exit_price = tp_price
            if exit_price:
                pnl = (exit_price - entry_price) * position if position > 0 else (entry_price - exit_price) * abs(position)
                balance += pnl
                trades.append(pnl)
                position = 0.0

        # New entry
        if position == 0 and direction != "hold" and raw_sl > 0 and raw_tp > 0:
            sl_distance = abs(row["close"] - raw_sl)
            if sl_distance <= 0:
                equity_curve.append(balance)
                continue
            if sizing_mode == "kelly":
                lot = kelly_position_size(balance, kelly_frac, sl_distance, row["close"])
            else:
                lot = (balance * 0.0025) / (sl_distance * 100_000)
                lot = max(0.01, round(lot * 100) / 100)
            position = lot * 100_000 if direction == "buy" else -lot * 100_000
            entry_price = row["close"]
            sl_price = raw_sl
            tp_price = raw_tp

        equity = balance + (position * (row["close"] - entry_price) if position >= 0 else position * (2*entry_price - row["close"]))
        equity_curve.append(equity)
        if equity > peak:
            peak = equity

    # Close open
    if position != 0:
        pnl = (df.iloc[-1]["close"] - entry_price) * position if position > 0 else (entry_price - df.iloc[-1]["close"]) * abs(position)
        balance += pnl
        trades.append(pnl)
        equity_curve[-1] = balance

    return _metrics(START_BAL, balance, equity_curve, trades)

def _metrics(start, end, equity, trades):
    ret = (end - start) / start
    dd = 0.0
    pk = start
    for e in equity:
        if e > pk: pk = e
        d = (pk - e) / pk if pk > 0 else 0
        if d > dd: dd = d
    wr = sum(1 for t in trades if t > 0) / len(trades) if trades else 0
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    pf = abs(sum(wins)/sum(losses)) if losses and sum(losses) != 0 else (float("inf") if wins else 0)
    # Sharpe annualized
    dr = [(equity[i]-equity[i-1])/equity[i-1] for i in range(1, len(equity)) if equity[i-1] > 0]
    sharpe = 0.0
    if dr:
        m = sum(dr)/len(dr)
        v = sum((r-m)**2 for r in dr)/len(dr)
        sd = math.sqrt(v)
        sharpe = (m / sd * math.sqrt(365)) if sd > 0 else 0.0
    return {"return": ret, "sharpe": sharpe, "max_dd": -dd, "win_rate": wr, "pf": pf, "trades": len(trades)}

# ─── Strategy wrappers ──────────────────────────────────────────────────────
def wyckoff_fn(df, sl_atr_mult, tp_atr_mult):
    strat = WyckoffStrategy()
    try:
        sig = strat.generate_signal(df)
        if sig is None or sig.direction.value == "hold":
            return {"direction": "hold"}
        # Override SL/TP with ATR-scaled values
        atr = calc_atr(df).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return {"direction": "hold"}
        entry = float(df["close"].iloc[-1])
        if sig.direction.value == "buy":
            sl = entry - sl_atr_mult * atr
            tp = entry + tp_atr_mult * atr
        else:
            sl = entry + sl_atr_mult * atr
            tp = entry - tp_atr_mult * atr
        return {"direction": sig.direction.value, "stop_loss": sl, "take_profit": tp}
    except Exception:
        return {"direction": "hold"}

def meanrev_fn(df, sl_atr_mult, tp_atr_mult):
    strat = MeanReversionStrategy()
    try:
        sig = strat.generate_signal(df)
        if sig is None or sig.direction.value == "hold":
            return {"direction": "hold"}
        # Override ATR multipliers
        atr = calc_atr(df).iloc[-1]
        if pd.isna(atr) or atr <= 0:
            return {"direction": "hold"}
        entry = float(df["close"].iloc[-1])
        if sig.direction.value == "buy":
            sl = entry - sl_atr_mult * atr
            tp = entry + tp_atr_mult * atr
        else:
            sl = entry + sl_atr_mult * atr
            tp = entry - tp_atr_mult * atr
        return {"direction": sig.direction.value, "stop_loss": sl, "take_profit": tp}
    except Exception:
        return {"direction": "hold"}

# ─── Grid Search ────────────────────────────────────────────────────────────
def grid_search(df, strategy_fn, name):
    kelly_grid = [0.125, 0.1875, 0.25, 0.375]
    sl_grid = [1.0, 1.5, 2.0]
    tp_grid = [2.0, 2.5, 3.0]
    size_modes = ["kelly", "fixed_0.25pct"]

    results = []
    total = len(kelly_grid) * len(sl_grid) * len(tp_grid) * len(size_modes)
    done = 0
    for kf in kelly_grid:
        for sl_m in sl_grid:
            for tp_m in tp_grid:
                for sm in size_modes:
                    m = backtest(df.copy(), strategy_fn, kf, sl_m, tp_m, sm)
                    m.update(kelly=kf, sl_mult=sl_m, tp_mult=tp_m, sizing=sm, strategy=name)
                    results.append(m)
                    done += 1

    results.sort(key=lambda r: r["sharpe"], reverse=True)
    return results

def main():
    print("Fetching EURUSD 1h data...", flush=True)
    df = fetch_data()
    print(f"  {len(df)} bars: {df.index[0]} → {df.index[-1]}", flush=True)

    wyckoff_results = grid_search(df, wyckoff_fn, "Wyckoff")
    meanrev_results = grid_search(df, meanrev_fn, "MeanReversion")

    print("\n=== Wyckoff top 5 ===")
    for r in wyckoff_results[:5]:
        gate = "✅" if r["sharpe"] > 0.5 and r["return"] > 0 and r["max_dd"] > -0.25 else "❌"
        print(f"{gate} Sharpe={r['sharpe']:.3f} Ret={r['return']:.2%} DD={r['max_dd']:.2%} "
              f"WR={r['win_rate']:.1%} T={r['trades']} Kelly={r['kelly']} SL={r['sl_mult']}x TP={r['tp_mult']}x {r['sizing']}")

    print("\n=== MeanReversion top 5 ===")
    for r in meanrev_results[:5]:
        gate = "✅" if r["sharpe"] > 0.5 and r["return"] > 0 and r["max_dd"] > -0.25 else "❌"
        print(f"{gate} Sharpe={r['sharpe']:.3f} Ret={r['return']:.2%} DD={r['max_dd']:.2%} "
              f"WR={r['win_rate']:.1%} T={r['trades']} Kelly={r['kelly']} SL={r['sl_mult']}x TP={r['tp_mult']}x {r['sizing']}")

    # Best per strategy
    bw = wyckoff_results[0]
    bm = meanrev_results[0]

    # Write results
    out = {
        "timestamp": datetime.now().isoformat(),
        "wyckoff_best": {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in bw.items()},
        "meanrev_best": {k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in bm.items()},
        "wyckoff_top5": [{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in r.items()} for r in wyckoff_results[:5]],
        "meanrev_top5": [{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in r.items()} for r in meanrev_results[:5]],
    }
    out_path = Path(__file__).resolve().parent / "results" / "phase5_param_tune.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    print(f"Best Wyckoff  → Kelly={bw['kelly']}, SL={bw['sl_mult']}x, TP={bw['tp_mult']}x, {bw['sizing']}, Sharpe={bw['sharpe']:.3f}")
    print(f"Best MeanRev  → Kelly={bm['kelly']}, SL={bm['sl_mult']}x, TP={bm['tp_mult']}x, {bm['sizing']}, Sharpe={bm['sharpe']:.3f}")



if __name__ == "__main__":
    main()
