#!/usr/bin/env python3
"""backtest_pipeline.py — Walk-forward gate pipeline for Quant Nanggroe AI.

Called by:
  - hedge_fund/risk/gate.py           (check_gate via subprocess)
  - hedge_fund/portfolio/main.py     (run_once via subprocess)

Outputs JSON with "pass": true/false to stdout.
Exit code 0 = pass, non-zero = fail.

Strategy types tested:
  1. Forex pairs (EURUSD, GBPUSD, USDJPY) — 90d daily data via yfinance
  2. Crypto via CoinGecko (BTC, ETH, SOL, BNB) — 365d via existing backtest runner
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────
QNA_DIR = Path(__file__).resolve().parent
DATA_DIR = QNA_DIR / "data"
RESULT_FILE = DATA_DIR / "backtest_results.json"
GATE_FILE = DATA_DIR / "gate_status.json"

# ── Constants ─────────────────────────────────────────────────────────
MIN_WIN_RATE = 0.35
MIN_SHARPE = 0.05
MIN_TRADES = 3
MAX_DRAWDOWN = 0.45
FOREX_PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
FOREX_DAYS = 90


def run_forex_backtest() -> dict:
    """Run simple SMA/RSI strategy backtest on forex pairs via yfinance.

    Returns summary dict with pass/fail metrics.
    """
    import numpy as np
    import yfinance as yf

    results = {}
    for ticker in FOREX_PAIRS:
        symbol = ticker.replace("=X", "")
        try:
            df = yf.download(ticker, period=f"{FOREX_DAYS}d", interval="1d", progress=False)
            if df is None or len(df) < 30:
                results[symbol] = {"status": "skip", "reason": f"insufficient_data:{len(df) if df is not None else 0}"}
                continue

            closes = df["Close"].values if "Close" in df.columns else df["close"].values
            highs = df["High"].values if "High" in df.columns else df["high"].values
            lows = df["Low"].values if "Low" in df.columns else df["low"].values

            # SMA crossover strategy
            fast_period = 10
            slow_period = 30
            fast_sma = np.convolve(closes, np.ones(fast_period) / fast_period, mode="valid")
            slow_sma = np.convolve(closes, np.ones(slow_period) / slow_period, mode="valid")
            min_len = min(len(fast_sma), len(slow_sma))
            fast_sma = fast_sma[-min_len:]
            slow_sma = slow_sma[-min_len:]

            # Generate signals
            signals = np.zeros(min_len)
            for i in range(1, min_len):
                if fast_sma[i - 1] <= slow_sma[i - 1] and fast_sma[i] > slow_sma[i]:
                    signals[i] = 1
                elif fast_sma[i - 1] >= slow_sma[i - 1] and fast_sma[i] < slow_sma[i]:
                    signals[i] = -1

            # Simple backtest
            balance = 10000.0
            position = 0.0
            entry_price = 0.0
            trades = []
            peak = balance
            equity_curve = [balance]

            base_idx = len(closes) - min_len
            for i in range(min_len):
                price = closes[base_idx + i]
                signal = signals[i]
                if price <= 0:
                    equity_curve.append(balance)
                    continue

                if signal == 1 and position <= 0:
                    if position < 0:
                        pnl = (entry_price - price) * abs(position)
                        balance += pnl
                        trades.append(("short_close", pnl))
                        position = 0
                    position = balance * 0.25 / price
                    entry_price = price
                elif signal == -1 and position >= 0:
                    if position > 0:
                        pnl = (price - entry_price) * position
                        balance += pnl
                        trades.append(("long_close", pnl))
                        position = 0
                    position = -balance * 0.25 / price
                    entry_price = price

                equity = balance + (position * price if position >= 0 else position * (2 * entry_price - price))
                equity_curve.append(equity)
                if equity > peak:
                    peak = equity

            # Close remaining
            if position != 0:
                price = closes[-1]
                pnl = (price - entry_price) * position if position > 0 else (entry_price - price) * abs(position)
                balance += pnl
                trades.append(("close", pnl))
                position = 0
            equity_curve[-1] = balance

            # Metrics
            wins = [t[1] for t in trades if t[1] > 0]
            losses = [t[1] for t in trades if t[1] < 0]
            total_return = (balance - 10000.0) / 10000.0
            num_trades = len(trades)
            win_rate = len(wins) / num_trades if num_trades > 0 else 0

            # Max drawdown
            max_dd = 0
            running_peak = 10000.0
            for eq in equity_curve:
                if eq > running_peak:
                    running_peak = eq
                dd = (running_peak - eq) / running_peak if running_peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd

            # Sharpe (simplified)
            daily_returns = []
            for j in range(1, len(equity_curve)):
                prev = equity_curve[j - 1]
                if prev > 0:
                    daily_returns.append((equity_curve[j] - prev) / prev)

            sharpe = 0.0
            if len(daily_returns) > 1:
                mean_ret = sum(daily_returns) / len(daily_returns)
                std = (sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)) ** 0.5
                if std > 0:
                    rf_daily = 0.05 / 365
                    excess = [r - rf_daily for r in daily_returns]
                    mean_excess = sum(excess) / len(excess)
                    std_excess = (sum((e - mean_excess) ** 2 for e in excess) / len(excess)) ** 0.5
                    sharpe = (mean_excess / std_excess * (365 ** 0.5)) if std_excess > 0 else 0

            results[symbol] = {
                "status": "ok",
                "trades": num_trades,
                "win_rate": round(win_rate, 4),
                "total_return": round(total_return, 4),
                "sharpe": round(sharpe, 4),
                "max_drawdown": round(max_dd, 4),
                "final_balance": round(balance, 2),
            }
        except Exception as e:
            results[symbol] = {"status": "error", "reason": str(e)}

    return results


def run_crypto_backtest() -> dict:
    """Delegate to existing QNA backtest runner for crypto."""
    try:
        from quant_nanggroe.backtest.runner import BacktestRunner
        runner = BacktestRunner()
        output = runner.run_pipeline(days=365, max_strategies=200, top_n=10)
        return {
            "status": "ok",
            "total_variants": output.get("total_variants", 0),
            "coins": {
                coin: {
                    "total_tested": d["total_tested"],
                    "passed": d["passed"],
                    "top_sharpe": max((r.get("sharpe", 0) for r in d.get("results", [])), default=0),
                }
                for coin, d in output.get("coins", {}).items()
            }
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def evaluate_gate(forex_results: dict, crypto_results: dict) -> tuple:
    """Evaluate whether the gate should pass.

    Returns (passed: bool, reasons: list[str]).
    """
    reasons = []
    failures = 0
    total_checked = 0

    # forex check
    for symbol, r in forex_results.items():
        if r.get("status") != "ok":
            continue
        total_checked += 1
        if r["trades"] < MIN_TRADES:
            failures += 1
            reasons.append(f"{symbol}: only {r['trades']} trades (need {MIN_TRADES})")
        elif r["win_rate"] < MIN_WIN_RATE:
            failures += 1
            reasons.append(f"{symbol}: win_rate {r['win_rate']:.1%} < {MIN_WIN_RATE:.0%}")
        elif r["sharpe"] < MIN_SHARPE and r["total_return"] < 0:
            failures += 1
            reasons.append(f"{symbol}: sharpe {r['sharpe']:.2f} negative return")
        elif r["max_drawdown"] > MAX_DRAWDOWN:
            failures += 1
            reasons.append(f"{symbol}: max_dd {r['max_drawdown']:.1%} > {MAX_DRAWDOWN:.0%}")

    # crypto check
    crypto_ok = crypto_results.get("status") == "ok"
    if crypto_ok:
        coin_results = crypto_results.get("coins", {})
        for coin, r in coin_results.items():
            total_checked += 1
            if r.get("passed", 0) == 0:
                failures += 1
                reasons.append(f"{coin}: no strategies passed backtest")

    if total_checked == 0:
        reasons.append("no_markets_tested")
        return False, reasons

    if failures > total_checked * 0.5:
        reasons.append(f"{failures}/{total_checked} checks failed")
        return False, reasons

    reasons.append(f"passed {total_checked - failures}/{total_checked} checks")
    return True, reasons


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(json.dumps({"phase": "forex", "status": "running"}))

    forex_results = run_forex_backtest()
    print(json.dumps({"phase": "forex", "status": "done", "results": forex_results}))

    print(json.dumps({"phase": "crypto", "status": "running"}))
    crypto_results = run_crypto_backtest()
    print(json.dumps({"phase": "crypto", "status": "done", "results": crypto_results}))

    passed, reasons = evaluate_gate(forex_results, crypto_results)

    result = {
        "pass": passed,
        "timestamp": datetime.now().isoformat(),
        "reasons": reasons,
        "forex": forex_results,
        "crypto": crypto_results,
    }

    # Write gate status file
    GATE_FILE.write_text(json.dumps(result, indent=2))

    # Final stdout result
    print(json.dumps({"pass": passed, "reasons": reasons}))

    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
