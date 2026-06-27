#!/usr/bin/env python3
"""Alpha Destruction Protocol v2 — Quant Nanggroe AI.

Tests every registered strategy against REAL market data (when available)
or statistically realistic synthetic data with GARCH vol, fat tails,
and autocorrelation. Each strategy gets PSR + DSR scores.

Usage::
    python scripts/alpha_destruction.py                              # synthetic (realistic)
    python scripts/alpha_destruction.py --real                        # real data if available
    python scripts/alpha_destruction.py --real --days 365             # 1 year of data
    python scripts/alpha_destruction.py --symbols BTC,ETH --export report.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.psr import validate_backtest_metrics
from quant_nanggroe.engine.strategy.strategies import list_strategies, create_strategy

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_N_OBS = 500
PASS_THRESHOLD = 0.95


def generate_realistic_ohlcv(n: int, seed: int = 42) -> pd.DataFrame:
    """Generate realistic OHLCV with GARCH vol, fat tails, momentum."""
    rng = np.random.default_rng(seed)
    # Fat-tailed returns (t-distribution df=4)
    returns = rng.standard_t(df=4, size=n) * 0.015
    # Autocorrelation (momentum structure)
    for i in range(1, n):
        returns[i] += 0.05 * returns[i - 1]
    # GARCH-like vol clustering
    vol = np.ones(n) * 0.015
    for i in range(1, n):
        vol[i] = np.sqrt(0.00001 + 0.85 * vol[i - 1]**2 + 0.10 * returns[i - 1]**2)
    returns = returns * (vol / 0.015)
    # Build OHLCV from returns
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(10000, 100000, n)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n, freq="D")
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close, "volume": volume,
    }, index=dates)


def try_load_real_data(symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
    """Try loading real OHLCV from local cache, then available providers."""
    # 1. Check local CSV cache first
    cached = _load_single_from_cache(symbol, days)
    if cached is not None:
        return cached

    # 2. Try CoinGecko (no API key needed)
    try:
        from quant_nanggroe.data.providers.coingecko_provider import CoinGeckoProvider
        provider = CoinGeckoProvider()
        end = pd.Timestamp.today()
        start = end - pd.Timedelta(days=days)
        df = provider.fetch_historical(symbol.replace("-", "").lower(), days=days)
        if df is not None and len(df) > 30:
            logger.info("  Loaded %d bars for %s from CoinGecko", len(df), symbol)
            return df
    except Exception as e:
        logger.debug("CoinGecko failed for %s: %s", symbol, e)

    # Try TwelveData (needs API key in env)
    try:
        from quant_nanggroe.data.providers.twelvedata import TwelveDataProvider
        provider = TwelveDataProvider()
        df = provider.fetch_ohlcv(symbol, interval="D")
        if df is not None and len(df) > 30:
            logger.info("  Loaded %d bars for %s from TwelveData", len(df), symbol)
            return df
    except Exception as e:
        logger.debug("TwelveData failed for %s: %s", symbol, e)

    return None


_CACHE_DIR = os.path.join(_REPO_ROOT, "data", "cached_ohlcv")


def _load_single_from_cache(symbol: str, days: int = 365) -> Optional[pd.DataFrame]:
    """Load a single symbol from the local CSV cache directory."""
    csv_path = os.path.join(_CACHE_DIR, f"{symbol}.csv")
    if not os.path.isfile(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path, parse_dates=["date"])
        df = df.set_index("date")
        df.index.name = None
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            logger.warning("  Cache file %s missing columns: %s", csv_path, required - set(df.columns))
            return None
        df = df[["open", "high", "low", "close", "volume"]]
        if days and len(df) > days:
            df = df.iloc[-days:]
        logger.info("  Loaded %d bars for %s from cache", len(df), symbol)
        return df
    except Exception as e:
        logger.debug("Local cache load failed for %s: %s", symbol, e)
        return None


def load_real_data(symbols: List[str], days: int = 365) -> Dict[str, pd.DataFrame]:
    """Load real OHLCV from local cached CSV files.

    Looks in ``data/cached_ohlcv/{symbol}.csv`` for each symbol.
    Expected CSV columns: **date, open, high, low, close, volume**.

    Returns a dict mapping symbol → DataFrame with a DatetimeIndex
    and columns ``open, high, low, close, volume`` — the same format
    produced by :func:`generate_realistic_ohlcv`.
    """
    result: Dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        df = _load_single_from_cache(symbol, days)
        if df is not None:
            result[symbol] = df
    return result


class _MultiCloseData:
    """Wrapper so data['close'] returns a T×N DataFrame (for StatArb).

    StatArb's validate_data checks 'close' in data.columns, then generate_signal
    expects data['close'] to be a DataFrame with one column per stock.  Pandas
    doesn't allow storing a DataFrame inside a DataFrame cell, so we proxy the
    minimal interface: columns, __getitem__, iloc, __len__, __contains__.
    """

    def __init__(self, close_df: pd.DataFrame):
        self._close_df = close_df

    def __getitem__(self, key):
        if key == "close":
            return self._close_df
        return self._close_df[key]

    def __contains__(self, key):
        if key == "close":
            return True
        return key in self._close_df.columns

    def __len__(self):
        return len(self._close_df)

    @property
    def empty(self):
        return self._close_df.empty

    @property
    def columns(self):
        return pd.Index(["close"])

    @property
    def iloc(self):
        return _Slicer(self._close_df)


class _Slicer:
    """Supports data.iloc[:i+1] → returns sliced _MultiCloseData."""

    def __init__(self, close_df: pd.DataFrame):
        self._close_df = close_df

    def __getitem__(self, idx):
        return _MultiCloseData(self._close_df.iloc[idx])


def prepare_data_for_strategy(strategy_name: str, ohlcv: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Transform synthetic OHLCV into the format each strategy expects."""
    rng = np.random.default_rng(42)
    n = len(ohlcv)

    if strategy_name == "PairsTrading":
        close = ohlcv["close"].values
        close_a = close
        beta = 2.0
        spread = np.zeros(n)
        for t in range(1, n):
            spread[t] = 0.85 * spread[t - 1] + rng.normal(0, 0.5)
        spread = spread * 2.0 / spread.std()
        close_b = beta * close_a + spread
        data = pd.DataFrame({
            "close": close_a,
            "ASSET_A": close_a,
            "ASSET_B": close_b,
        }, index=ohlcv.index)
        return data

    if strategy_name == "StatisticalArbitrage":
        n_stocks = 10
        cols = {}
        base = ohlcv["close"].values
        for j in range(n_stocks):
            noise = np.cumsum(rng.normal(0, 0.005, n))
            cols[f"STOCK_{j}"] = base * (1 + 0.02 * noise / np.std(noise))
        cols["ASSET"] = base.copy()
        close_df = pd.DataFrame(cols, index=ohlcv.index)
        return _MultiCloseData(close_df)

    if strategy_name == "CryptoSpecific":
        data = ohlcv.copy()
        data["funding_rate"] = rng.normal(0, 0.001, n)
        return data

    return ohlcv


def generate_signals(strategy_name: str, ohlcv: pd.DataFrame, symbol: str = "BTC") -> np.ndarray:
    """Generate a signal time series by running strategy on expanding windows.

    Returns array of position weights (same length as ohlcv). Entries before
    the strategy's warmup period are 0.
    """
    try:
        strategy = create_strategy(strategy_name)
        if strategy is None:
            return np.zeros(len(ohlcv))

        signal_method = (getattr(strategy, "generate_signal", None)
                         or getattr(strategy, "generate", None)
                         or getattr(strategy, "predict", None))
        if signal_method is None:
            return np.zeros(len(ohlcv))

        data = prepare_data_for_strategy(strategy_name, ohlcv, symbol)

        signals = np.zeros(len(data))
        for i in range(len(data)):
            window = data.iloc[:i + 1]
            try:
                result = signal_method(window)
                if result is None:
                    continue
                if hasattr(result, "signal_type") and hasattr(result, "confidence"):
                    val = float(result.confidence)
                    if result.signal_type.value in ("sell", "close_long"):
                        val = -val
                    signals[i] = val
                elif hasattr(result, "value"):
                    signals[i] = float(result.value)
                elif isinstance(result, (int, float, np.floating)):
                    signals[i] = float(result)
            except Exception:
                continue

        return signals
    except Exception as e:
        logger.debug("Strategy %s failed: %s", strategy_name, e)
        return np.zeros(len(ohlcv))


def run_destruction(
    symbols: List[str],
    n_observations: int = DEFAULT_N_OBS,
    use_real: bool = False,
    export_path: Optional[str] = None,
    walk_forward: bool = False,
    strategies_filter: Optional[List[str]] = None,
) -> Dict[str, dict]:
    """Run the full Alpha Destruction Protocol against every registered strategy.

    Uses realistic synthetic data by default. With --real, tries live data.
    """
    np.random.seed(42)
    strategies = list_strategies()
    if strategies_filter:
        strategies = [s for s in strategies if s in strategies_filter]

    if not strategies:
        logger.error("No strategies registered")
        return {}

    results: Dict[str, dict] = {}

    for strategy_name in strategies:
        logger.info("Testing strategy: %s", strategy_name)
        strategy_results = {"symbols": {}}
        all_strategy_returns: List[np.ndarray] = []

        for symbol in symbols:
            if use_real:
                ohlcv = try_load_real_data(symbol, n_observations)
                if ohlcv is None:
                    logger.warning("  No real data for %s, using synthetic", symbol)
                    ohlcv = generate_realistic_ohlcv(n_observations)
            else:
                ohlcv = generate_realistic_ohlcv(n_observations)

            n_bars = len(ohlcv)
            close = ohlcv["close"].values if "close" in ohlcv.columns else ohlcv[symbol].values
            signals = generate_signals(strategy_name, ohlcv, symbol)

            # Compute returns from signals, skipping warmup
            portfolio_returns = np.zeros(n_bars)
            for i in range(1, n_bars):
                target = float(signals[i])
                target = np.clip(target, -1, 1)
                ret = target * (close[i] - close[i - 1]) / max(close[i - 1], 1e-8)
                portfolio_returns[i] = ret

            # Only validate after warmup
            nonzero_mask = np.abs(signals) > 1e-6
            if np.any(nonzero_mask):
                first_trade = np.argmax(nonzero_mask)
                active_returns = portfolio_returns[first_trade:]
            else:
                active_returns = portfolio_returns

            # Run PSR/DSR validation on active (post-warmup) returns
            num_trials = max(1, len(strategies))
            vr = validate_backtest_metrics(
                f"{strategy_name}/{symbol}",
                active_returns,
                num_trials=num_trials,
            )

            symbol_result = {
                "symbol": symbol,
                "n": n_bars,
                "sharpe": round(vr.sharpe_annualized, 4),
                "psr": round(vr.psr.psr, 4) if vr.psr else 0.0,
                "psr_significant": vr.psr.is_significant if vr.psr else False,
                "dsr": round(vr.dsr.dsr, 4) if vr.dsr else 0.0,
                "dsr_significant": vr.dsr.is_significant if vr.dsr else False,
                "num_trades": vr.num_trades,
                "notes": vr.notes,
            }
            strategy_results["symbols"][symbol] = symbol_result
            all_strategy_returns.append(portfolio_returns)

        # Aggregate: does the strategy show ANY alpha?
        psr_values = [s["psr"] for s in strategy_results["symbols"].values()]
        sharpe_values = [s["sharpe"] for s in strategy_results["symbols"].values()]
        dsr_values = [s["dsr"] for s in strategy_results["symbols"].values()]

        mean_psr = float(np.mean(psr_values)) if psr_values else 0.0
        mean_sharpe = float(np.mean(sharpe_values)) if sharpe_values else 0.0
        mean_dsr = float(np.mean(dsr_values)) if dsr_values else 0.0
        survives = all(s["psr_significant"] for s in strategy_results["symbols"].values())

        strategy_results["aggregate"] = {
            "mean_sharpe": round(mean_sharpe, 4),
            "mean_psr": round(mean_psr, 4),
            "mean_dsr": round(mean_dsr, 4),
            "survives_alpha_test": survives,
            "data_source": "real" if use_real else "synthetic",
        }
        verdict = "PASS" if survives else "FAIL"
        strategy_results["verdict"] = verdict
        results[strategy_name] = strategy_results

        logger.info("  %s: PSR=%.3f, Sharpe=%.3f, DSR=%.3f → %s",
                     strategy_name, mean_psr, mean_sharpe, mean_dsr, verdict)

    if walk_forward:
        try:
            from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer
            from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig, MarketType, StrategyType
            logger.info("\n  ── Walk-Forward Validation ──")
            engine = BacktestEngine(BacktestConfig(market=MarketType.CRYPTO))
            for strategy_name in strategies:
                for symbol in symbols:
                    ohlcv = try_load_real_data(symbol, n_observations) if use_real else generate_realistic_ohlcv(n_observations)
                    if ohlcv is None or len(ohlcv) < 400:
                        logger.info("    %s/%s: skipping (only %d bars)", strategy_name, symbol, len(ohlcv) if ohlcv is not None else 0)
                        continue
                    sigs = generate_signals(strategy_name, ohlcv, symbol)
                    prices = ohlcv[["close"]].rename(columns={"close": symbol})
                    sigs_df = pd.DataFrame({symbol: sigs}, index=ohlcv.index)
                    wfa = WalkForwardAnalyzer(
                        engine,
                        train_window=252, test_window=63, mode="rolling",
                    )
                    wf_results = wfa.analyze(prices, sigs_df)
                    windows = wf_results.get("windows", [])
                    oos_sharpes = [w.out_of_sample_sharpe for w in windows]
                    if oos_sharpes:
                        avg_oos = float(np.mean(oos_sharpes))
                        logger.info("    %s/%s: OOS Sharpe=%.3f (%d windows, IS Sharpe=%.3f)",
                                     strategy_name, symbol, avg_oos, len(oos_sharpes),
                                     wf_results.get("aggregate", {}).get("avg_is_sharpe", 0))
                    else:
                        logger.info("    %s/%s: 0 windows generated", strategy_name, symbol)
        except Exception as e:
            logger.warning("  Walk-forward skipped: %s", e)

    passed = sum(1 for r in results.values() if r["verdict"] == "PASS")
    failed = sum(1 for r in results.values() if r["verdict"] == "FAIL")

    summary = {
        "total_strategies": len(strategies),
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / max(len(strategies), 1) * 100, 1),
        "symbols_tested": symbols,
        "data_source": "real" if use_real else "synthetic",
    }
    full_report = {"summary": summary, "strategies": results}

    if export_path:
        with open(export_path, "w") as f:
            json.dump(full_report, f, indent=2)
        logger.info("Report exported to %s", export_path)

    logger.info("\n━━━ Alpha Destruction Complete ━━━")
    logger.info("  %d/%d strategies PASSED (%.1f%%)", passed, len(strategies), summary["pass_rate"])
    logger.info("  %d/%d strategies FAILED", failed, len(strategies))

    return full_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha Destruction Protocol v2")
    parser.add_argument("--symbols", default="BTC,ETH,SOL,XRP,SPY,QQQ,IWM",
                        help="Comma-separated symbols")
    parser.add_argument("--n", type=int, default=DEFAULT_N_OBS,
                        help="Number of observations")
    parser.add_argument("--real", action="store_true",
                        help="Use real market data (falls back to synthetic)")
    parser.add_argument("--export", default=None,
                        help="Export path for JSON report")
    parser.add_argument("--walk-forward", action="store_true",
                        help="Run walk-forward analysis after PSR/DSR")
    parser.add_argument("--strategies", default=None,
                        help="Comma-separated strategy names (default: all)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]
    strategies_filter = [s.strip() for s in args.strategies.split(",")] if args.strategies else None
    run_destruction(symbols, args.n, use_real=args.real, export_path=args.export,
                    walk_forward=args.walk_forward, strategies_filter=strategies_filter)


if __name__ == "__main__":
    main()
