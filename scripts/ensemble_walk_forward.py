"""Ensemble walk-forward: simpler approach — detect regime, run enabled strategies, combine."""
import json, sys
sys.path.insert(0, "/sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree")
import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path("/sdcard/dhaherlabs/repositories/Quant-Nanggroe-AI-worktree/data/cached_ohlcv")
SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "SPY", "QQQ", "IWM"]
TRAIN = 252
TEST = 63
MIN_BARS = 60

from quant_nanggroe.engine.regime.strategy_selector import RegimeStrategySelector
from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

selector = RegimeStrategySelector()
ALL_STRATS = list_strategies()

def detect_regime(close):
    n = len(close)
    if n < 63:
        return "sideways", 0.4
    sma_21 = np.mean(close[-21:])
    sma_63 = np.mean(close[-63:])
    vol_21 = np.std(close[-21:] / np.mean(close[-21:])) if n >= 21 else 0.02
    last = close[-1]
    if last > sma_63 and vol_21 < 0.015:
        return "bull_trend", min(0.8, 0.5 + (last - sma_63) / sma_63 * 5)
    elif last < sma_63 and vol_21 > 0.01:
        return "bear_trend", min(0.8, 0.5 + vol_21 * 10)
    elif vol_21 > 0.025:
        return "high_volatility", min(0.8, 0.5 + vol_21 * 8)
    else:
        return "sideways", 0.5

results = {}
for symbol in SYMBOLS:
    csv_path = DATA_DIR / f"{symbol}.csv"
    if not csv_path.exists():
        print(f"  {symbol}: no data — skipping")
        continue
    raw = pd.read_csv(csv_path, parse_dates=["date"]).sort_values("date")
    if len(raw) < TRAIN + MIN_BARS:
        print(f"  {symbol}: only {len(raw)} bars — skipping")
        continue
    print(f"  {symbol}: {len(raw)} bars — running ensemble walk-forward...")
    oos_returns = []
    n_windows = 0
    for start in range(0, len(raw) - TRAIN - MIN_BARS, TEST):
        train_end = start + TRAIN
        test_end = min(train_end + TEST, len(raw))
        if test_end - train_end < MIN_BARS:
            break
        train = raw.iloc[start:train_end]
        test = raw.iloc[train_end - 1:test_end]
        regime, conf = detect_regime(train["close"].values)
        rm = selector.select_strategies(regime, conf)
        enabled = [s.name for s in rm.active_strategies if s.name in ALL_STRATS]
        if not enabled:
            enabled = ALL_STRATS
        regime_params = {s.name: s.params for s in rm.active_strategies}
        mult = rm.risk_multiplier
        daily_rets = []
        for i in range(1, len(test)):
            hist = test.iloc[:i + 1]
            if len(hist) < MIN_BARS:
                continue
            signals = []
            for s_name in enabled:
                try:
                    params = dict(regime_params.get(s_name, {}))
                    strat = create_strategy(s_name, params)
                    sig = strat.generate_signal(hist)
                    if sig and sig.signal_type.value in ("buy", "sell"):
                        direction = 1 if sig.signal_type.value == "buy" else -1
                        signals.append(direction * sig.confidence)
                except Exception:
                    pass
            if signals:
                close_i = test.iloc[i]["close"]
                close_prev = test.iloc[i - 1]["close"]
                ret = np.mean(signals) * mult * (close_i - close_prev) / max(abs(close_prev), 1e-10)
                daily_rets.append(ret)
        if daily_rets:
            oos_returns.extend(daily_rets)
            n_windows += 1
    if len(oos_returns) < 10:
        print(f"    -> too few trades ({len(oos_returns)}) — skipping")
        continue
    oos_arr = np.array(oos_returns)
    sharpe = np.mean(oos_arr) / max(np.std(oos_arr), 1e-10) * np.sqrt(252)
    total_ret = float(np.sum(oos_arr))
    results[symbol] = {
        "windows": n_windows, "oos_trades": len(oos_returns),
        "oos_sharpe": round(float(sharpe), 3),
        "total_return_pct": round(total_ret * 100, 2),
        "win_rate": round(float(np.mean(oos_arr > 0) * 100), 1),
    }
    print(f"    -> Sharpe={sharpe:.3f} ret={total_ret*100:.2f}% win={np.mean(oos_arr>0)*100:.1f}% windows={n_windows} trades={len(oos_returns)}")

print("\n=== ENSEMBLE WALK-FORWARD VERDICT ===")
sharpe_vals = [r["oos_sharpe"] for r in results.values()]
if sharpe_vals:
    mean_sharpe = float(np.mean(sharpe_vals))
    print(f"Mean OOS Sharpe: {mean_sharpe:.3f}")
    print(f"Positive: {sum(1 for s in sharpe_vals if s > 0)}/{len(sharpe_vals)}")
    print(f"Best: {max(sharpe_vals):.3f}  Worst: {min(sharpe_vals):.3f}")
summary = {"mean_oos_sharpe": round(float(np.mean(sharpe_vals)), 3) if sharpe_vals else 0, "per_symbol": results}
print(json.dumps(summary, indent=2))
