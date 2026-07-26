#!/usr/bin/env python3
"""Phase 5: Optimize Kelly fraction, lot sizing, SL/TP multipliers for top gate-passing strategies."""
import sys, os, json
from pathlib import Path
from datetime import datetime

ROOT = r"D:\repositories\Quant-Nanggroe-AI-worktree"
sys.path.insert(0, ROOT)
os.environ["PYTHONPATH"] = ROOT

import numpy as np
import pandas as pd
import yfinance as yf


def load_eurusd():
    df = yf.download("EURUSD=X", period="60d", interval="15m", auto_adjust=False, progress=False)
    if df.empty:
        raise RuntimeError("No EURUSD data")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    df.index.name = "date"
    return df


def backtest_simple(df, strat_name, params, sl_mult=1.5, tp_mult=2.0, kelly_frac=0.25, lot_balance_ratio=10000):
    from quant_nanggroe.engine.strategies.registry import get_strategy
    strat_class = get_strategy(strat_name)
    if strat_class is None:
        return None
    strat = strat_class(parameters=params) if params else strat_class()
    signals = strat.generate_signals(df)
    if signals is None or len(signals) == 0:
        return None

    close = df["close"].values
    n = len(close)
    equity = 10000.0
    peak_equity = equity
    max_dd = 0.0
    trades = 0
    wins = 0
    total_pnl = 0.0
    pnl_list = []
    position = 0
    entry_price = 0
    sl_price = 0
    tp_price = 0
    atr_val = 0.001

    for i in range(1, n):
        if i >= 14:
            high_r = df["high"].iloc[max(0, i - 14) : i + 1].values
            low_r = df["low"].iloc[max(0, i - 14) : i + 1].values
            close_r = df["close"].iloc[max(0, i - 14) : i + 1].values
            tr = np.maximum(high_r - low_r, np.abs(high_r - np.roll(close_r, 1)))
            tr[0] = high_r[0] - low_r[0]
            atr_val = np.mean(tr)

        sig = signals.iloc[i] if i < len(signals) else 0

        if position != 0:
            if position == 1:
                if close[i] <= sl_price:
                    pnl = (sl_price - entry_price) / entry_price * equity
                    equity += pnl; total_pnl += pnl; pnl_list.append(pnl); trades += 1
                    if pnl > 0: wins += 1
                    position = 0
                elif close[i] >= tp_price:
                    pnl = (tp_price - entry_price) / entry_price * equity
                    equity += pnl; total_pnl += pnl; pnl_list.append(pnl); trades += 1
                    if pnl > 0: wins += 1
                    position = 0
            elif position == -1:
                if close[i] >= sl_price:
                    pnl = (entry_price - sl_price) / entry_price * equity
                    equity += pnl; total_pnl += pnl; pnl_list.append(pnl); trades += 1
                    if pnl > 0: wins += 1
                    position = 0
                elif close[i] <= tp_price:
                    pnl = (entry_price - tp_price) / entry_price * equity
                    equity += pnl; total_pnl += pnl; pnl_list.append(pnl); trades += 1
                    if pnl > 0: wins += 1
                    position = 0

        if position == 0 and sig != 0:
            sl_dist = atr_val * sl_mult if atr_val > 0 else close[i] * 0.001
            tp_dist = atr_val * tp_mult if atr_val > 0 else close[i] * 0.002

            if trades > 5:
                win_rate = wins / trades
                wins_list = [p for p in pnl_list if p > 0]
                losses_list = [abs(p) for p in pnl_list if p < 0]
                avg_win = np.mean(wins_list) if wins_list else 0
                avg_loss = np.mean(losses_list) if losses_list else 1
                b = avg_win / max(avg_loss, 0.0001)
                kelly_raw = (b * win_rate - (1 - win_rate)) / b if b > 0 and win_rate > 0 else 0
                kelly_actual = max(0.01, min(kelly_frac, kelly_raw * kelly_frac, 0.05))
            else:
                kelly_actual = kelly_frac

            lot_size = max(0.01, min(equity / lot_balance_ratio, equity * kelly_actual / (max(sl_dist, 0.0001) * 10000)))
            entry_price = close[i]
            if sig == 1:
                sl_price = entry_price - sl_dist
                tp_price = entry_price + tp_dist
                position = 1
            elif sig == -1:
                sl_price = entry_price + sl_dist
                tp_price = entry_price - tp_dist
                position = -1

        peak_equity = max(peak_equity, equity)
        dd = (peak_equity - equity) / peak_equity
        max_dd = max(max_dd, dd)

    if trades == 0:
        return {"sharpe": -999, "return_pct": 0, "max_dd_pct": 0, "wr": 0, "trades": 0}

    wr = wins / trades * 100
    avg_pnl = total_pnl / trades
    std_pnl = np.std(pnl_list) if len(pnl_list) > 1 else 1
    sharpe = (avg_pnl / std_pnl) * np.sqrt(len(pnl_list)) if std_pnl > 0 else 0
    ret_pct = (equity - 10000) / 10000 * 100
    return {"sharpe": round(sharpe, 3), "return_pct": round(ret_pct, 2), "max_dd_pct": round(max_dd * 100, 2), "wr": round(wr, 1), "trades": trades}


def main():
    print("Loading EURUSD data...", flush=True)
    df = load_eurusd()
    print(f"Loaded {len(df)} bars EURUSD", flush=True)

    strategies = {
        "WyckoffStrategy": {
            "base": {"lookback": 50, "volume_threshold": 1.3},
            "tune": {
                "lookback": [30, 50, 70],
                "volume_threshold": [1.0, 1.3, 1.5],
            }
        },
        "MeanReversionStrategy": {
            "base": {"k_period": 14, "d_period": 3, "oversold": 20, "overbought": 80},
            "tune": {
                "k_period": [10, 14, 20],
                "d_period": [3, 5],
                "oversold": [20, 25],
                "overbought": [75, 80],
            }
        },
        "DhaherSystem": {
            "base": {"lookback": 14, "atr_mult": 1.5, "rr_min": 2.0, "min_confluence": 2},
            "tune": {
                "lookback": [14, 20],
                "atr_mult": [1.2, 1.5, 2.0],
                "rr_min": [2.0, 2.5],
                "min_confluence": [1, 2],
            }
        },
    }

    risk_combos = [
        {"kelly_fraction": kf, "sl_mult": sl, "tp_mult": 2.0, "lot_balance_ratio": lb}
        for kf in [0.15, 0.25, 0.35]
        for sl in [1.2, 1.5, 2.0]
        for lb in [5000, 10000]
    ]

    all_results = []
    combo_count = 0

    for strat_name, sinfo in strategies.items():
        print(f"\nStrategy: {strat_name}", flush=True)
        tune = sinfo["tune"]
        keys = list(tune.keys())
        ranges = [tune[k] for k in keys]

        for idx in np.ndindex(*[len(r) for r in ranges]):
            test_params = sinfo["base"].copy()
            for j, key in enumerate(keys):
                test_params[key] = ranges[j][idx[j]]

            for rc in risk_combos:
                combo_count += 1
                try:
                    result = backtest_simple(
                        df, strat_name, test_params,
                        sl_mult=rc["sl_mult"], tp_mult=rc["tp_mult"],
                        kelly_frac=rc["kelly_fraction"],
                        lot_balance_ratio=rc["lot_balance_ratio"],
                    )
                    if result and result["trades"] >= 10:
                        score = result["sharpe"] * (result["wr"] / 50.0)
                        all_results.append({
                            "strategy": strat_name,
                            "strat_params": {k: test_params.get(k) for k in keys},
                            "risk_params": {"kelly_fraction": rc["kelly_fraction"], "sl_mult": rc["sl_mult"], "tp_mult": rc["tp_mult"]},
                            "metrics": result,
                            "score": round(score, 4),
                        })
                except Exception:
                    pass

                if combo_count % 100 == 0:
                    print(f"  Tested {combo_count} combos...", flush=True)

    all_results.sort(key=lambda x: x["score"], reverse=True)
    print(f"\nTotal combinations tested: {combo_count}", flush=True)
    print(f"Valid results: {len(all_results)}", flush=True)

    for i, r in enumerate(all_results[:5]):
        print(f"  {i+1}. {r['strategy']} score={r['score']:.4f} {r['metrics']}", flush=True)

    out_path = Path(ROOT) / "results" / "param_optimization.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"best": all_results[0] if all_results else None, "top_10": all_results[:10], "total_combos": combo_count, "timestamp": datetime.now().isoformat()}, f, indent=2)
    print(f"\nResults saved to {out_path}", flush=True)

    if all_results:
        best = all_results[0]
        print(f"\nBest: {best['strategy']} {best['strat_params']}", flush=True)
        print(f"  Risk: {best['risk_params']}", flush=True)
        print(f"  Metrics: {best['metrics']}", flush=True)


if __name__ == "__main__":
    main()
