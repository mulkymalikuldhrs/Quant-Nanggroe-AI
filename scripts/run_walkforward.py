#!/usr/bin/env python3
"""Walk-forward backtest runner for all 15 QNA strategies.

Usage:
    python3 scripts/run_walkforward.py [--symbol BTCUSDT] [--strategy Momentum]

Output: JSON results to data/backtest/results/ + summary to stdout.
"""

import json, os, sys, time, argparse
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DATA_DIR = REPO / "quant_nanggroe" / "data" / "backtest"
RESULTS_DIR = DATA_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Import strategy factory
from quant_nanggroe.engine.strategy.strategies import create_strategy, list_strategies

# Helper functions

def load_candles(symbol: str) -> List[Dict]:
    path = DATA_DIR / f"{symbol}_daily.json"
    if not path.exists():
        print(f"  No data for {symbol}, run fetch_backtest_data.py first")
        return []
    with open(path) as f:
        return json.load(f)

def compute_metrics(trades: List[Dict], equity_curve: List[float]) -> Dict:
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl_pct": 0.0,
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "avg_hold_bars": 0,
        }
    closed = [t for t in trades if t.get("exit_idx") is not None]
    wins = sum(1 for t in closed if t.get("pnl_pct", 0) > 0)
    losses = len(closed) - wins
    win_rate = wins / len(closed) if closed else 0.0
    first_equity = equity_curve[0] if equity_curve else 10000.0
    last_equity = equity_curve[-1] if equity_curve else first_equity
    total_pnl_pct = (last_equity - first_equity) / first_equity * 100
    returns = [t["pnl_pct"] / 100 for t in closed if t.get("pnl_pct")]
    if len(returns) >= 2:
        avg_r = sum(returns) / len(returns)
        var_r = sum((r - avg_r) ** 2 for r in returns) / len(returns)
        std = var_r ** 0.5
        sharpe = (avg_r / std * (252 ** 0.5)) if std > 0 else 0.0
    else:
        sharpe = 0.0
    # Max drawdown
    max_dd = 0.0
    peak = equity_curve[0] if equity_curve else 10000.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    avg_hold = 0
    if closed:
        holds = [t.get("exit_idx", 0) - t.get("entry_idx", 0) for t in closed]
        avg_hold = sum(holds) / len(holds) if holds else 0
    return {
        "total_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "sharpe": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd, 4),
        "avg_hold_bars": round(avg_hold, 1),
    }

def run_strategy_backtest(strategy_name: str, closes: List[float], initial_capital: float = 10000.0, position_pct: float = 0.95) -> Dict:
    if len(closes) < 30:
        return {"strategy": strategy_name, "total_trades": 0, "error": "insufficient_data"}
    try:
        strategy = create_strategy(strategy_name)
    except Exception as e:
        return {"strategy": strategy_name, "total_trades": 0, "error": str(e)}

    cash = initial_capital
    position = 0.0
    trades: List[Dict] = []
    equity_curve = [initial_capital]
    # Walk data
    for i in range(30, len(closes)):
        # Build a minimal DataFrame for the strategy (OHLCV only needed columns)
        import pandas as pd
        df = pd.DataFrame({
            "close": closes[: i + 1],
            "open": closes[: i + 1],
            "high": closes[: i + 1],
            "low": closes[: i + 1],
            "volume": [0] * (i + 1),
        })
        # Generate signal
        try:
            signal = strategy.generate_signal(df)
        except Exception:
            signal = None
        sig_type = "hold"
        if signal is not None:
            sig_type = getattr(signal, "signal_type", "hold")
            # pydantic returns enum objects
            if hasattr(sig_type, "value"):
                sig_type = sig_type.value
        price = closes[i]
        if sig_type == "buy" and position == 0:
            position = cash * position_pct / price
            cash *= 1 - position_pct
            trades.append({"type": "buy", "price": price, "entry_idx": i})
        elif sig_type == "sell" and position > 0 and trades:
            cash += position * price
            entry = trades[-1]
            entry["exit_price"] = price
            entry["exit_idx"] = i
            entry["pnl_pct"] = round((price - entry["price"]) / entry["price"] * 100, 4)
            position = 0.0
        equity_curve.append(cash + (position * price if position > 0 else 0))
    # Close any remaining position
    if position > 0:
        cash += position * closes[-1]
        position = 0.0
    metrics = compute_metrics(trades, equity_curve)
    metrics["strategy"] = strategy_name
    metrics["symbol"] = "BTCUSDT"
    metrics["period"] = f"{len(closes)} days"
    metrics["final_equity"] = round(cash, 2)
    metrics["initial_capital"] = initial_capital
    return metrics

def _closes_to_prices(closes: List[float], symbol: str = "BTCUSDT") -> "pd.DataFrame":
    """ponytail: minimal DataFrame bridge — DatetimeIndex + single close col."""
    import pandas as pd
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(closes), freq="D")
    return pd.DataFrame({symbol: closes}, index=idx)


def run_walk_forward(
    strategy_name: str,
    closes: List[float],
    n_folds: int = 5,
    train_window: int = 60,
    test_window: int = 20,
) -> Dict:
    """Walk-forward via engine WalkForwardAnalyzer (proper OOS, no leakage).

    Replaces the old leaky approach that concatenated train+val and backtested
    the combined series (validation data leaked into signal generation).
    Now uses analyze_strategy: re-fits per fold, separate IS/OOS signal slices.
    """
    import pandas as pd
    from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
    from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
    from quant_nanggroe.engine.strategy.strategies import create_strategy

    prices = _closes_to_prices(closes)
    strategy_class = create_strategy(strategy_name).__class__
    engine = BacktestEngine(BacktestConfig())
    analyzer = WalkForwardAnalyzer(
        engine, train_window=train_window, test_window=test_window, mode="rolling",
        purge_gap=2, embargo=1, min_observations=30,
    )
    res = analyzer.analyze_strategy(prices, strategy_class)
    windows = res.get("windows", [])
    folds = [{
        "fold": i + 1,
        "is_sharpe": round(w.in_sample_sharpe, 4),
        "oos_sharpe": round(w.out_of_sample_sharpe, 4),
        "is_trades": w.is_trades,
        "oos_trades": w.oos_trades,
        "degradation": round(w.degradation_ratio, 4),
    } for i, w in enumerate(windows)]
    agg = res.get("aggregate", {})
    return {
        "strategy": strategy_name,
        "folds": folds,
        "avg_is_sharpe": agg.get("avg_is_sharpe", 0.0),
        "avg_oos_sharpe": agg.get("avg_oos_sharpe", 0.0),
        "consistent_folds": sum(1 for f in folds if f["oos_sharpe"] > 0.5),
        "total_folds": len(folds),
        "under_sampled": agg.get("under_sampled", False),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair")
    parser.add_argument("--strategy", default=None, help="Strategy name (default: all)")
    args = parser.parse_args()
    candles = load_candles(args.symbol)
    if not candles:
        sys.exit(1)
    closes = [c["close"] for c in candles][:150]
    strategies = [args.strategy] if args.strategy else list_strategies()
    all_results = []
    for name in strategies:
        print(f"\n=== {name} ===")
        # ponytail: run_strategy_backtest is IN-SAMPLE ONLY (no OOS discipline).
        # Use it only as a sanity check, NEVER as a deployment signal.
        bt = run_strategy_backtest(name, closes)
        print(f"[IN-SAMPLE ONLY] Backtest: {bt.get('total_trades',0)} trades, Sharpe {bt.get('sharpe',0):.2f}, PnL {bt.get('total_pnl_pct',0):+.2f}%")
        wf = run_walk_forward(name, closes)
        print(f"Walk-forward (proper OOS): {wf['total_folds']} folds, IS Sharpe {wf['avg_is_sharpe']:.2f}, OOS Sharpe {wf['avg_oos_sharpe']:.2f}, consistent {wf['consistent_folds']}/{wf['total_folds']}")
        if wf.get("under_sampled"):
            print("  WARNING: under_sampled (median OOS fold < 30 trades) — do NOT trust edge")
        all_results.append({"name": name, "backtest_in_sample": bt, "walkforward": wf})
    # Save results JSON
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_path = RESULTS_DIR / f"walkforward_{args.symbol}_{timestamp}.json"
    result_path.write_text(json.dumps(all_results, indent=2))
    print(f"Results saved to {result_path}")
    # Summary table
    print("\nSummary:")
    header = f"{'Strategy':<20} {'Trades':>7} {'Sharpe':>8} {'Win%':>7} {'PnL%':>8} {'DD%':>7} {'WF_Sharpe':>10}"
    print(header)
    print("-" * len(header))
    for r in sorted(all_results, key=lambda x: x["backtest"].get("sharpe",0), reverse=True):
        bt = r["backtest"]
        wf = r["walkforward"]
        win_pct = bt.get("win_rate",0) * 100 if "win_rate" in bt else 0
        dd_pct = bt.get("max_drawdown_pct",0) * 100 if "max_drawdown_pct" in bt else 0
        print(f"{r['name']:<20} {bt.get('total_trades',0):>7} {bt.get('sharpe',0):>8.2f} {win_pct:>6.1f}% {bt.get('total_pnl_pct',0):>7.2f}% {dd_pct:>6.1f}% {wf.get('avg_sharpe',0):>10.2f}")

if __name__ == "__main__":
    main()
