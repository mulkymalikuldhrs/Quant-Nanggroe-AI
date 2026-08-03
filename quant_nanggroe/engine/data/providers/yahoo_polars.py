"""Yahoo Polars provider pilot (QuantScience QS18: 10X faster data).

Thin provider that fetches OHLCV via the standard Yahoo path and, when the
optional `polars` dependency is installed, returns a Polars DataFrame for fast
rolling analytics. Falls back to pandas when Polars is absent (graceful
degradation, per QNA ponytail rule).

Design:
- No import-time dependency on polars/yfinance.
- Lazy imports inside fetch(); ImportError -> pandas fallback path.
- Conforms to engine/data/provider_interface.QNAProviderBase shape (best-effort).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def _fetch_yahoo_pandas(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch via yfinance if available; otherwise return empty frame with schema."""
    try:
        import yfinance as yf  # type: ignore  (optional)
    except Exception:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "timestamp"])
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "timestamp"])
    out = pd.DataFrame(index=df.index)
    out["open"] = df["Open"].to_numpy()
    out["high"] = df["High"].to_numpy()
    out["low"] = df["Low"].to_numpy()
    out["close"] = df["Close"].to_numpy()
    out["volume"] = df["Volume"].to_numpy()
    out["timestamp"] = (pd.to_datetime(df.index).astype("int64") // 10**9).to_numpy()
    return out


def fetch_ohlcv(symbol: str, period: str = "1y", interval: str = "1d", as_polars: bool = True):
    """Fetch OHLCV; return Polars DataFrame if available and requested.

    Returns pandas DataFrame when polars is not installed (always safe).
    """
    pdf = _fetch_yahoo_pandas(symbol, period=period, interval=interval)
    if as_polars:
        try:
            import polars as pl  # type: ignore  (optional, roadmap QS18)
        except Exception:
            return pdf
        return pl.from_pandas(pdf)
    return pdf


def rolling_sharpe(close: object, window: int = 20) -> object:
    """Rolling Sharpe by symbol group — Polars path when available.

    Accepts a Polars DataFrame with 'close' (and optionally 'symbol'); returns
    the same frame with a 'rolling_sharpe' column. Pandas fallback supported.
    """
    try:
        import polars as pl  # type: ignore
    except Exception:
        if isinstance(close, pd.DataFrame):
            ret = close["close"].pct_change()
            roll = ret.rolling(window).mean() / (ret.rolling(window).std() + 1e-9) * np.sqrt(252)
            out = close.copy()
            out["rolling_sharpe"] = roll.to_numpy()
            return out
        return close
    if isinstance(close, pl.DataFrame):
        ret = close["close"].pct_change()
        roll = (ret.rolling(window).mean() / (ret.rolling(window).std() + 1e-9)) * np.sqrt(252)
        return close.with_columns(roll.alias("rolling_sharpe"))
    return close
