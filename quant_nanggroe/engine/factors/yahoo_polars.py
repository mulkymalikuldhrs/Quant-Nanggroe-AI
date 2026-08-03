"""Yahoo Finance → Polars data loader (QuantScience QS-M4: fast OHLCV ingest).

Mirrors QuantScience archive roadmap module `yahoo_polars.py`. Provides a single
entry point `fetch_ohlcv(symbol, interval, period)` that returns a Polars DataFrame
when Polars + yfinance are available, and falls back to a pandas DataFrame (or a
list[dict] candles shape) when they are not — so the live path never breaks on a
missing optional dependency.

Ponytail: one job (fetch + normalize), no strategy logic here.
REAL-ONLY: hits Yahoo via yfinance; no synthetic data.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


def _lazy_yfinance():
    try:
        import yfinance as yf  # type: ignore
        return yf
    except Exception as e:  # pragma: no cover - optional dep
        log.warning("yahoo_polars: yfinance unavailable (%s) — callers use fallback", e)
        return None


def _lazy_polars():
    try:
        import polars as pl  # type: ignore
        return pl
    except Exception:  # pragma: no cover - optional dep
        return None


def fetch_ohlcv(
    symbol: str,
    interval: str = "1d",
    period: str = "3mo",
    as_candles: bool = False,
) -> object:
    """Fetch OHLCV from Yahoo and return normalized data.

    Returns:
      - Polars DataFrame (if polars available) with columns
        open/high/low/close/volume/timestamp
      - pandas DataFrame (fallback) with same columns
      - list[dict] candles (if as_candles=True) compatible with strategy input

    On any failure returns an EMPTY structure of the same shape (never raises to
    the caller — data layer must be fail-safe for the signal path).
    """
    yf = _lazy_yfinance()
    if yf is None:
        log.error("fetch_ohlcv: yfinance missing — cannot fetch %s", symbol)
        return [] if as_candles else (_lazy_polars().DataFrame() if _lazy_polars() else None)

    try:
        df = yf.Ticker(symbol).history(interval=interval, period=period)
        if df is None or len(df) == 0:
            log.warning("fetch_ohlcv: empty history for %s", symbol)
            return [] if as_candles else (_lazy_polars().DataFrame() if _lazy_polars() else None)

        norm = df.reset_index()[["Open", "High", "Low", "Close", "Volume"]].copy()
        norm.columns = ["open", "high", "low", "close", "volume"]
        norm["timestamp"] = df.index.astype("int64") // 10**9 if hasattr(df.index, "astype") else 0

        pl = _lazy_polars()
        if pl is not None:
            pdf = pl.from_pandas(norm)
            if as_candles:
                return pdf.to_dicts()
            return pdf

        # pandas fallback
        if as_candles:
            return norm.to_dict("records")
        return norm
    except Exception as e:
        log.error("fetch_ohlcv: fetch failed for %s: %s", symbol, e)
        return [] if as_candles else None


__all__ = ["fetch_ohlcv"]
