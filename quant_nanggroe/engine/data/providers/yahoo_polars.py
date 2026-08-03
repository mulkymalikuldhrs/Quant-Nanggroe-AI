"""Yahoo Polars provider pilot (QuantScience QS18: 10X faster data).

Thin provider that fetches OHLCV via the standard Yahoo path and, when the
optional `polars` dependency is installed, returns a Polars DataFrame for fast
rolling analytics. Falls back to pandas when Polars is absent (graceful
degradation, per QNA ponytail rule).

Design:
- No import-time dependency on polars/yfinance.
- Lazy imports inside fetch(); ImportError -> pandas fallback path.
- Implements QNAProviderBase interface (engine/data/provider_interface.py).
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.data.provider_interface import (
    DataCategory,
    DataRequest,
    DataResponse,
    QNAProviderBase,
)


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
        ret = pl.col("close").pct_change()
        roll = (pl.col("close").pct_change().rolling_mean(window) /
                (pl.col("close").pct_change().rolling_std(window) + 1e-9)) * np.sqrt(252)
        return close.with_columns(roll.alias("rolling_sharpe"))
    return close


class YahooPolarsProvider(QNAProviderBase):
    """QNAProviderBase implementation for Yahoo Polars data layer (QS018).

    Falls back to pandas when Polars is not installed. No import-time
    dependency on either library.
    """

    categories: List[DataCategory] = [
        DataCategory.EQUITY_OHLCV,
        DataCategory.CRYPTO_OHLCV,
        DataCategory.FOREX_OHLCV,
    ]

    @property
    def name(self) -> str:
        return "yahoo_polars"

    def fetch(self, request: DataRequest) -> DataResponse:
        """Fetch OHLCV for the requested symbol.

        Params honored: period (default '1y'), interval (default '1d'),
        as_polars (default True).
        """
        symbol = request.symbol
        params = request.params or {}
        period = params.get("period", "1y")
        interval = params.get("interval", "1d")
        as_polars = params.get("as_polars", True)

        try:
            data = fetch_ohlcv(symbol, period=period, interval=interval, as_polars=as_polars)
            if hasattr(data, "to_dict"):
                results = data.to_dict(orient="records") if hasattr(data, "to_dict") else []
                if isinstance(data, pd.DataFrame):
                    results = data.to_dict("records")
            elif hasattr(data, "rows"):
                results = data.rows()
            else:
                results = []
            return DataResponse(results=results, provider=self.name, error="")
        except Exception as exc:
            return DataResponse(results=[], provider=self.name, error=str(exc))
