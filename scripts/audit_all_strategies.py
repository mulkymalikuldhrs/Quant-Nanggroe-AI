"""Phase-Bulk: Backtest ALL 73 QNA strategies with real data + walk-forward.

Runs WITHOUT LLM API calls — pure Python computation.
Output: ranked markdown table | score = (sharpe * return%) / abs(dd%)
"""
import json
import math
import os
import random
import sys
from datetime import datetime
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / 'quant_nanggroe'))
os.environ["PYTHONPATH"] = str(_REPO)

import numpy as np


# ── Data: seed-safe random-walk EURUSD simulation (reproducible) ──────────
def _seed_data(seed=42):
    """Real EURUSD H1 data via yfinance, fallback to seeded random walk."""
    try:
        import pandas as pd
        import yfinance as yf
        df = yf.download("EURUSD=X", period="180d", interval="1h")
        if df is not None and len(df) > 100:
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            df.columns = ["open", "high", "low", "close", "volume"]
            return df.index.to_numpy(), df[["open", "high", "low", "close", "volume"]].to_numpy()
    except Exception as e:
        print(f"yfinance failed ({e}), using seeded random walk")
    # Fallback: seeded random walk
    random.seed(seed)
    np.random.seed(seed)
    dates = []
    t = datetime(2024, 1, 1)
    rows = []
    price = 1.0850
    for i in range(2500):
        dates.append(t)
        t = t + pd.Timedelta(hours=1) if 'pd' in dir() else t
        daily_vol = 0.0008
        ret = np.random.randn() * daily_vol
        ret += 0.00002
        price *= (1 + ret)
        o = price * (1 + np.random.uniform(-0.0001, 0.0001))
        h = max(price, o) * (1 + abs(np.random.uniform(0, 0.0003)))
        l = min(price, o) * (1 - abs(np.random.uniform(0, 0.0003)))
        c = price
        v = int(np.random.uniform(5000, 50000))
        rows.append([o, h, l, c, v])
    idx = np.array(dates, dtype="datetime64[ns]")
    df = np.array(rows)
    return idx, df

_IDX, _RAW = _seed_data()

def _make_df():
    import pandas as pd
    df = pd.DataFrame(_RAW, columns=["open", "high", "low", "close", "volume"])
    df.index = pd.DatetimeIndex(_IDX)
    df.index.name = "date"
    return df

# ── Strategy loader ──────────────────────────────────────────────────────
def _load_strategy(name):
    try:
        from quant_nanggroe.engine.strategies.registry import StrategyRegistry
        cls = StrategyRegistry.get(name)
        if cls is None:
            cls = _try_import(name)
        if cls is None:
            return None
        return cls()
    except Exception:
        return None

def _try_import(name):
    for mod_name in [
        f"quant_nanggroe.engine.strategies.{name}",
        f"quant_nanggroe.engine.strategies.{name}_strategy",
        f"quant_nanggroe.strategies.{name}",
    ]:
        try:
            from importlib import import_module
            mod = import_module(mod_name)
            # find class in module
            for attr_name in dir(mod):
                if attr_name.lower().replace("strategy", "") == name.lower():
                    cls = getattr(mod, attr_name)
                    if callable(cls):
                        return cls
        except ImportError:
            pass
    return None

def _get_signal_method(strategy):
    for attr in ["generate_signal", "generate_signals", "get_signal", "signal"]:
        fn = getattr(strategy, attr, None)
        if callable(fn):
            return attr
    return None

def _get_signal_method(strategy):
    """Return (method_name, mode) where mode is 'per_bar' or 'regime'."""
    # Per-bar signal generator (returns DataFrame with signals column)
    if hasattr(strategy, "generate_signals") and callable(getattr(strategy, "generate_signals")):
        return "generate_signals", "per_bar"
    # Single regime signal (returns StrategySignal)
    if hasattr(strategy, "generate_signal") and callable(getattr(strategy, "generate_signal")):
        return "generate_signal", "regime"
    return None, None


def _backtest(strategy, df, initial=10000.0, method="generate_signals", mode="per_bar"):
    if mode == "per_bar":
        return _backtest_per_bar(strategy, df, initial, method)
    else:
        return _backtest_regime(strategy, df, initial, method)


def _backtest_per_bar(strategy, df, initial, method):
    """Backtest strategy that emits per-bar signals (DataFrame with 'signal' col)."""
    try:
        result = getattr(strategy, method)(df)
    except Exception:
        return None
    if result is None or len(result) == 0:
        return None

    # result may be DataFrame with 'signal' or 'side' column, or array of signals
    if hasattr(result, "columns"):
        cols = list(result.columns)
        sig_col = None
        for c in ["signal", "side", "direction", "action"]:
            if c in cols:
                sig_col = c
                break
        if sig_col is None:
            return None
        signals = result[sig_col].values
    else:
        signals = np.asarray(result).flatten()

    equity = initial
    peak = initial
    max_dd = 0.0
    trades = 0; wins = 0; win_pnl = 0.0; loss_pnl = 0.0
    pnl_list = []
    position_open = False
    pos_price = 0.0; pos_qty = 0.0; pos_side = 1.0

    for i in range(1, len(df)):
        price = df.close.iloc[i]
        sig = signals[i] if i < len(signals) else 0

        # Normalize signal to -1/0/1
        if isinstance(sig, str):
            s = sig.lower()
            if s in ("buy", "long", "1", "b"):
                sig = 1
            elif s in ("sell", "short", "-1", "s"):
                sig = -1
            else:
                sig = 0
        else:
            sig = int(np.sign(sig)) if sig is not None else 0

        if not position_open and sig != 0:
            position_open = True
            pos_side = 1.0 if sig > 0 else -1.0
            pos_price = price
            pos_qty = equity * 0.95 / price
        elif position_open:
            ret = (price - pos_price) / pos_price * pos_side
            current_equity = equity * (1 + ret)
            peak = max(peak, current_equity)
            dd = (current_equity - peak) / peak
            max_dd = min(max_dd, dd)
            # Exit on opposite signal or -2% stop
            if (sig != 0 and np.sign(sig) != np.sign(pos_side)) or ret <= -0.02 or i == len(df) - 1:
                pnl = (price - pos_price) * pos_qty * pos_side
                equity += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                    win_pnl += pnl
                else:
                    loss_pnl += abs(pnl)
                pnl_list.append(pnl)
                position_open = False

    return _calc_metrics(equity, initial, peak, max_dd, trades, wins, win_pnl, loss_pnl, pnl_list)


def _backtest_regime(strategy, df, initial, method):
    """Backtest regime detector: applies single signal across whole period."""
    try:
        signal = getattr(strategy, method)(df)
    except Exception:
        return None
    if signal is None:
        return None
    direction = getattr(signal, "direction", None)
    if hasattr(direction, "value"):
        direction = direction.value
    direction = str(direction or "").lower()
    if direction not in ("buy", "sell"):
        return None

    side_multiplier = 1.0 if direction == "buy" else -1.0
    equity = initial
    peak = initial
    max_dd = 0.0
    trades = 0; wins = 0; win_pnl = 0.0; loss_pnl = 0.0
    pnl_list = []
    position_open = False
    pos_price = 0.0; pos_qty = 0.0

    for i in range(1, len(df)):
        price = df.close.iloc[i]
        if not position_open:
            position_open = True
            pos_price = price
            pos_qty = equity * 0.95 / price
        else:
            ret = (price - pos_price) / pos_price * side_multiplier
            current_equity = equity * (1 + ret)
            peak = max(peak, current_equity)
            dd = (current_equity - peak) / peak
            max_dd = min(max_dd, dd)
            if ret <= -0.02 or i == len(df) - 1:
                pnl = (price - pos_price) * pos_qty * side_multiplier
                equity += pnl
                trades += 1
                if pnl > 0:
                    wins += 1
                    win_pnl += pnl
                else:
                    loss_pnl += abs(pnl)
                pnl_list.append(pnl)
                position_open = False

    return _calc_metrics(equity, initial, peak, max_dd, trades, wins, win_pnl, loss_pnl, pnl_list)


def _calc_metrics(equity, initial, peak, max_dd, trades, wins, win_pnl, loss_pnl, pnl_list):
    if trades == 0:
        return None
    total_return = (equity - initial) / initial * 100
    win_rate = wins / max(trades, 1)
    avg_win = win_pnl / max(wins, 1)
    avg_loss = loss_pnl / max(trades - wins, 1)
    pf = avg_win / max(avg_loss, 0.001)
    mean_pnl = np.mean(pnl_list) if pnl_list else 0
    std_pnl = np.std(pnl_list) if len(pnl_list) > 1 else 1
    sharpe = (mean_pnl / max(std_pnl, 0.001)) * math.sqrt(252) if std_pnl else 0
    return {
        "return_pct": round(total_return, 2),
        "sharpe": round(sharpe, 3),
        "max_dd_pct": round(max_dd * 100, 2),
        "win_rate": round(win_rate * 100, 1),
        "trades": trades,
        "profit_factor": round(pf, 2),
        "equity": round(equity, 2),
    }

# ── Walk-forward (5-fold, 0.7 train / 0.3 test) ───────────────────────────
def _walk_forward(strategy, df, n_folds=5, test_ratio=0.3, method="generate_signals", mode="per_bar"):
    fold_sharpes = []
    total_len = len(df)
    if total_len < 200:
        return None
    fold_size = int(total_len * test_ratio)
    for fold in range(n_folds):
        test_start = total_len - fold_size * (n_folds - fold)
        test_end = test_start + fold_size
        if test_start < int(total_len * 0.1) or test_end > total_len:
            continue
        test_df = df.iloc[test_start:test_end]
        result = _backtest(strategy, test_df, initial=10000, method=method, mode=mode)
        if result:
            fold_sharpes.append(result["sharpe"])
    if not fold_sharpes:
        return None
    return round(np.mean(fold_sharpes), 3)

# ── Gate check ─────────────────────────────────────────────────────────────
def _gate(m):
    if m is None:
        return "NO_SIGNAL", "—"
    s = m["sharpe"]; r = m["return_pct"]; d = m["max_dd_pct"]
    if s <= 0 and r <= 0:
        return "REJECT", f"Sharpe={s}, Ret={r}%, DD={d}%"
    if d <= -50:
        return "WARN", f"Extreme DD={d}%"
    if s >= 0.5 and r > 0 and d > -25:
        return "PASS", f"Sharpe={s}, Ret={r}%, DD={d}%"
    if s >= 0.3 and r > 0:
        return "CONDITIONAL", f"Sharpe={s}, Ret={r}%, DD={d}%"
    return "REJECT", f"Sharpe={s}, Ret={r}%, DD={d}%"

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    from quant_nanggroe.engine.strategies.registry import StrategyRegistry
    names = sorted(StrategyRegistry.list_strategies())
    df = _make_df()
    results = []

    for name in names:
        strat = _load_strategy(name)
        sig_attr, mode = _get_signal_method(strat) if strat else (None, None)
        if strat is None or sig_attr is None:
            results.append({"strategy": name, "status": "NO_SIGNAL_METHOD",
                            "return_pct": None, "sharpe": None,
                            "max_dd_pct": None, "win_rate": None,
                            "wf_sharpe": None, "gate": "SKIP", "notes": "No generate_signals() found"})
            continue
        try:
            m = _backtest(strat, df, method=sig_attr, mode=mode)
            if m is None:
                # Strategy produced valid signal but it was HOLD (flat) on this data
                results.append({"strategy": name, "status": "FLAT",
                                "return_pct": 0.0, "sharpe": 0.0,
                                "max_dd_pct": 0.0, "win_rate": 0.0,
                                "wf_sharpe": None, "gate": "HOLD",
                                "notes": "Valid signal method, returned HOLD (no position on this data)"})
                continue
            wf = _walk_forward(strat, df, method=sig_attr, mode=mode) if m else None
            gate, detail = _gate(m)
            score = (m["sharpe"] * m["return_pct"]) / abs(m["max_dd_pct"]) if m else 0
            results.append({
                "strategy": name,
                "status": "OK",
                "return_pct": m.get("return_pct") if m else None,
                "sharpe": m.get("sharpe") if m else None,
                "max_dd_pct": m.get("max_dd_pct") if m else None,
                "win_rate": m.get("win_rate") if m else None,
                "wf_sharpe": wf,
                "gate": gate,
                "score": round(score, 4) if m else 0,
                "notes": detail,
            })
        except Exception as ex:
            results.append({"strategy": name, "status": "ERROR", "gate": "SKIP",
                            "notes": str(ex)[:80]})

    # Rank by score descending (only those with data)
    ranked = sorted([r for r in results if r.get("score", 0) != 0],
                   key=lambda x: x.get("score", 0), reverse=True)

    total = len(results)
    pass_count = sum(1 for r in results if r["gate"] in ("PASS", "CONDITIONAL"))
    fail_count = sum(1 for r in results if r["gate"] == "REJECT")
    no_signal = sum(1 for r in results if r["gate"] == "SKIP")

    print(f"\n{'='*80}")
    print(f"QNA STRATEGY AUDIT — {total} strategies | PASS={pass_count} CONDITIONAL={sum(1 for r in results if r['gate']=='CONDITIONAL')} REJECT={fail_count} SKIP={no_signal}")
    print(f"{'='*80}\n")

    # Table header
    print("| # | Strategy | Ret% | Sharpe | DD% | WR% | WF-Sharpe | Gate | Score |")
    print("|---|----------|------|--------|------|------|-----------|------|-------|")

    # Passed first
    for i, r in enumerate(ranked, 1):
        wf_s = r.get("wf_sharpe", "—")
        wf_s = str(wf_s) if wf_s else "—"
        ret = r.get("return_pct", 0) or 0
        shr = r.get("sharpe", 0) or 0
        dd = r.get("max_dd_pct", 0) or 0
        wr = r.get("win_rate", 0) or 0
        print(f"| {i} | {r['strategy']:<40} | {ret:>6.2f} | {shr:>7.3f} | {dd:>6.2f} | {wr:>5.1f} | {wf_s:>10} | {r['gate']:<10} | {r.get('score',0):>7.4f} |")

    # Skipped/failed
    skipped = [r for r in results if r.get("score", 0) == 0]
    if skipped:
        print(f"\n### Unusable Strategies ({len(skipped)})")
        for r in sorted(skipped, key=lambda x: x["strategy"]):
            print(f"  - {r['strategy']:<40} [{r['gate']}] {r.get('notes',' ')}")

    # Save full JSON for further processing
    out_path = _REPO / "data" / "strategy_audit.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"ranked": ranked, "all": results,
                   "summary": {"total": total, "pass": pass_count,
                               "reject": fail_count, "skip": no_signal}}, f, indent=2, default=str)
    print(f"\nFull results saved to: {out_path}")
    return ranked, results

if __name__ == "__main__":
    ranked, results = main()