"""Benchmark — Resolve and fetch benchmark return series for backtest comparison.

Provides the ``resolve_benchmark`` function used by the advanced engine
framework (backtest.engines.base.BaseEngine) to compare strategy returns
against a market benchmark.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkResult:
    """Resolved benchmark series and metadata."""

    ticker: str
    ret_series: pd.Series
    total_ret: float


# Default benchmark tickers per market
_DEFAULT_BENCHMARKS: Dict[str, str] = {
    "equity": "SPY",
    "china_a": "000300.SS",
    "crypto": "BTC-USD",
    "forex": "DXY",
    "futures": "ES=F",
}


def resolve_benchmark(
    strategy_codes: List[str],
    source: str = "yfinance",
    start_date: str = "",
    end_date: str = "",
    interval: str = "1D",
    explicit: Optional[str] = None,
) -> Optional[BenchmarkResult]:
    """Resolve and fetch a benchmark return series.

    If *explicit* is given, that ticker is used directly.  Otherwise the
    market type is inferred from the strategy codes and a default benchmark
    is selected from ``_DEFAULT_BENCHMARKS``.

    Args:
        strategy_codes: List of strategy instrument codes.
        source: Data source identifier (currently only "yfinance").
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        interval: Bar interval (e.g. "1D").
        explicit: Explicit benchmark ticker to use.

    Returns:
        BenchmarkResult or None if benchmark cannot be resolved.
    """
    ticker = explicit

    if not ticker:
        # Infer market type from first code
        code = strategy_codes[0] if strategy_codes else ""
        if code.endswith("-USDT") or code.endswith("/USDT"):
            market = "crypto"
        elif len(code) == 6 and code.isalpha():
            market = "forex"
        elif code.endswith(".SS") or code.endswith(".SZ"):
            market = "china_a"
        else:
            market = "equity"
        ticker = _DEFAULT_BENCHMARKS.get(market, "SPY")

    try:
        return _fetch_yfinance(ticker, start_date, end_date, interval)
    except Exception as exc:
        logger.warning("Failed to fetch benchmark %s: %s", ticker, exc)
        return None


def _fetch_yfinance(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str,
) -> BenchmarkResult:
    """Fetch benchmark data via yfinance."""
    import yfinance as yf

    data = yf.download(ticker, start=start_date or None, end=end_date or None, interval=interval)
    if data.empty:
        raise ValueError(f"No data returned for {ticker}")

    close = data["Close"]
    ret_series = close.pct_change().dropna()
    total_ret = float((close.iloc[-1] / close.iloc[0]) - 1) if len(close) > 1 else 0.0

    return BenchmarkResult(ticker=ticker, ret_series=ret_series, total_ret=total_ret)
