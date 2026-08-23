"""
QNA Backtester
==============
Pure Python backtesting engine for 1000+ strategy variants.
Calculates: Sharpe, Sortino, Calmar, Max DD, Win Rate, Profit Factor, etc.

Usage:
  from backtester import Backtester, BacktestResult, DataFetcher
  bt = Backtester()
  results = bt.run_batch(variants, candles)
  results.sort(key=lambda r: r.sharpe, reverse=True)
"""

import json
import logging
import math
import os
import ssl
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)


def _ssl_ctx():
    verify = os.environ.get("QNAI_SSL_VERIFY", "1") == "1"
    ctx = ssl.create_default_context()
    ctx.check_hostname = verify
    ctx.verify_mode = ssl.CERT_REQUIRED if verify else ssl.CERT_NONE
    if not verify:
        log.warning("SSL verification DISABLED — set QNAI_SSL_VERIFY=1 in production")
    return ctx


class DataFetcher:
    """Fetch historical market data from CoinGecko."""

    CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "hist_cache"

    def __init__(self):
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _request(self, url, timeout=30):
        ctx = _ssl_ctx()
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "QNA/2.0")
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)

    def fetch_historical(self, coin_id="bitcoin", days=365) -> List[Dict]:
        """Fetch daily OHLC from CoinGecko, cached locally."""
        cache_file = self.CACHE_DIR / f"{coin_id}_{days}d.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < 3600:
                return json.loads(cache_file.read_text())

        # Try OHLC endpoint with max days
        for try_days in ["max", days, 365]:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc?vs_currency=usd&days={try_days}"
            try:
                with self._request(url) as resp:
                    raw = json.loads(resp.read())
                    if isinstance(raw, list) and len(raw) >= 30:
                        candles = []
                        for entry in raw:
                            candles.append({
                                "timestamp": entry[0] // 1000,
                                "open": float(entry[1]),
                                "high": float(entry[2]),
                                "low": float(entry[3]),
                                "close": float(entry[4]),
                                "volume": 0,
                            })
                        cache_file.write_text(json.dumps(candles))
                        return candles
            except Exception:
                continue

        # Fallback: use market_chart for price-only data, generate synthetic OHLC
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
            with self._request(url) as resp:
                raw = json.loads(resp.read())
                prices = raw.get("prices", [])
                if len(prices) >= 30:
                    candles = []
                    for i in range(len(prices)):
                        ts, price = prices[i]
                        open_p = float(price)
                        prev = candles[-1]["close"] if candles else open_p
                        high = max(open_p, prev) * (1 + 0.005)
                        low = min(open_p, prev) * (1 - 0.005)
                        candles.append({
                            "timestamp": int(ts) // 1000,
                            "open": prev,
                            "high": high,
                            "low": low,
                            "close": open_p,
                            "volume": 0,
                        })
                    cache_file.write_text(json.dumps(candles))
                    return candles
        except Exception:
            pass

        raise RuntimeError(
            f"No real market data available for {coin_id} from any source. "
            "Cannot generate synthetic candles. Failing closed."
        )


class BacktestResult:
    """Backtest result for one strategy variant."""

    def __init__(self, strategy_name: str, params: Dict, template_name: str):
        self.strategy_name = strategy_name
        self.params = params
        self.template_name = template_name
        self.total_return = 0.0
        self.annual_return = 0.0
        self.sharpe = 0.0
        self.sortino = 0.0
        self.calmar = 0.0
        self.max_drawdown = 0.0
        self.win_rate = 0.0
        self.profit_factor = 0.0
        self.num_trades = 0
        self.avg_win = 0.0
        self.avg_loss = 0.0
        self.total_pnl = 0.0
        self.start_balance = 10000.0
        self.end_balance = 10000.0
        self.volatility = 0.0

    def to_dict(self) -> Dict:
        return {
            "name": self.strategy_name,
            "template": self.template_name,
            "params": self.params,
            "total_return": round(self.total_return, 4),
            "annual_return": round(self.annual_return, 4),
            "sharpe": round(self.sharpe, 4),
            "sortino": round(self.sortino, 4),
            "calmar": round(self.calmar, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "num_trades": self.num_trades,
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "total_pnl": round(self.total_pnl, 2),
            "start_balance": self.start_balance,
            "end_balance": round(self.end_balance, 2),
            "volatility": round(self.volatility, 4),
        }

    def __repr__(self):
        return (f"<{self.strategy_name} Sharpe={self.sharpe:.2f} "
                f"Ret={self.total_return:.1%} DD={self.max_drawdown:.1%}>")


class Backtester:
    """Runs backtests for thousands of strategy variants."""

    START_BALANCE = 10000.0

    def run_batch(self, variants: List, candles: List[Dict],
                  progress_cb=None, max_strategies=0) -> List[BacktestResult]:
        """Backtest all strategy variants on the same candle data."""
        results = []
        total = len(variants)
        for idx, variant in enumerate(variants):
            if max_strategies > 0 and idx >= max_strategies:
                break
            result = self._backtest_one(variant, candles)
            results.append(result)
            if progress_cb:
                progress_cb(idx + 1, total, variant.name)
        results.sort(key=lambda r: r.sharpe, reverse=True)
        return results

    def _backtest_one(self, variant, candles) -> BacktestResult:
        """Run single strategy backtest with equity curve tracking."""
        result = BacktestResult(variant.name, variant.params, variant.template_name)
        signals = variant.generate_signals(candles)
        if not signals or len(signals) != len(candles):
            return result

        balance = self.START_BALANCE
        position = 0.0
        entry_price = 0.0
        peak = balance
        trades = []
        equity_curve = [balance]

        for i in range(len(candles)):
            price = candles[i]["close"]
            signal = signals[i]

            # Skip if we can't trade (not enough data for indicator)
            if price <= 0:
                equity_curve.append(balance)
                continue

            # Execute signals
            if signal == 1 and position <= 0:
                # Close short if any
                if position < 0:
                    pnl = (entry_price - price) * abs(position)
                    balance += pnl
                    trades.append((entry_price, price, "short", pnl))
                    position = 0
                # Open long
                position = balance * 0.0025 / price
                entry_price = price

            elif signal == -1 and position >= 0:
                # Close long if any
                if position > 0:
                    pnl = (price - entry_price) * position
                    balance += pnl
                    trades.append((entry_price, price, "long", pnl))
                    position = 0
                # Open short
                position = -balance * 0.25 / price
                entry_price = price

            # Calculate equity
            equity = balance + (position * price if position >= 0
                                else position * (2 * entry_price - price))
            equity_curve.append(equity)
            if equity > peak:
                peak = equity

        # Close any remaining position
        if position != 0:
            price = candles[-1]["close"]
            pnl = (price - entry_price) * position if position > 0 else (entry_price - price) * abs(position)
            balance += pnl
            trades.append((entry_price, price, "long" if position > 0 else "short", pnl))
            position = 0
        equity_curve[-1] = balance

        # Calculate metrics
        result.start_balance = self.START_BALANCE
        result.end_balance = balance
        result.total_pnl = balance - self.START_BALANCE
        result.total_return = (balance - self.START_BALANCE) / self.START_BALANCE
        result.annual_return = result.total_return / (len(candles) / 365) if candles else 0
        result.num_trades = len([t for t in trades if abs(t[3]) > 0])

        # Max drawdown
        running_peak = self.START_BALANCE
        max_dd = 0
        for eq in equity_curve:
            if eq > running_peak:
                running_peak = eq
            dd = (running_peak - eq) / running_peak if running_peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown = max_dd

        # Win rate & profit factor
        wins = [t[3] for t in trades if t[3] > 0]
        losses = [t[3] for t in trades if t[3] < 0]
        result.win_rate = len(wins) / len(trades) if trades else 0
        result.avg_win = sum(wins) / len(wins) if wins else 0
        result.avg_loss = abs(sum(losses) / len(losses)) if losses else 0
        result.profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0

        # Calmar ratio
        result.calmar = abs(result.annual_return / max_dd) if max_dd > 0 else 0

        # Daily returns for Sharpe & Sortino
        daily_returns = []
        for j in range(1, len(equity_curve)):
            prev = equity_curve[j - 1]
            if prev > 0:
                daily_returns.append((equity_curve[j] - prev) / prev)

        if daily_returns:
            mean_ret = sum(daily_returns) / len(daily_returns)
            variance = sum((r - mean_ret) ** 2 for r in daily_returns) / len(daily_returns)
            result.volatility = math.sqrt(variance) if variance > 0 else 0

            # Sharpe (annualized, risk-free = 0.05)
            rf_daily = 0.05 / 365
            excess = [r - rf_daily for r in daily_returns]
            mean_excess = sum(excess) / len(excess)
            std_excess = math.sqrt(sum((e - mean_excess) ** 2 for e in excess) / len(excess)) if len(excess) > 1 else 0
            result.sharpe = (mean_excess / std_excess * math.sqrt(365)) if std_excess > 0 else 0

            # Sortino (downside deviation only)
            neg_returns = [r for r in daily_returns if r < 0]
            if neg_returns:
                downside_var = sum(r ** 2 for r in neg_returns) / len(neg_returns)
                downside_std = math.sqrt(downside_var)
                result.sortino = (mean_ret - rf_daily) / downside_std * math.sqrt(365) if downside_std > 0 else 0
            else:
                result.sortino = result.sharpe

        return result

    def rank(self, results: List[BacktestResult],
             min_sharpe=0.5, max_dd=0.30, min_trades=5, top_n=20) -> List[BacktestResult]:
        """Filter and rank backtest results by composite score."""
        filtered = [r for r in results
                    if r.sharpe >= min_sharpe
                    and r.max_drawdown <= max_dd
                    and r.num_trades >= min_trades
                    and r.total_return > 0]

        # Composite score: 50% Sharpe, 30% Calmar, 20% Win Rate
        max_sharpe = max(r.sharpe for r in filtered) if filtered else 1
        max_calmar = max(r.calmar for r in filtered) if filtered else 1

        for r in filtered:
            s_score = r.sharpe / max_sharpe if max_sharpe > 0 else 0
            c_score = r.calmar / max_calmar if max_calmar > 0 else 0
            r._score = 0.5 * s_score + 0.3 * c_score + 0.2 * r.win_rate

        filtered.sort(key=lambda r: r._score, reverse=True)
        return filtered[:top_n]

    def export_deploy(self, results: List[BacktestResult], filepath: str):
        """Export top strategies for deployment to live engine."""
        data = {
            "generated": datetime.now().isoformat(),
            "count": len(results),
            "strategies": [r.to_dict() for r in results],
        }
        Path(filepath).write_text(json.dumps(data, indent=2))
        return data
