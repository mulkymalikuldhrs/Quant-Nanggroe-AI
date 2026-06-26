"""OpenBB MCP data provider for Quant Nanggroe AI.

Provides market data via the OpenBB Hub REST API with optional
OpenBB Python SDK acceleration. Designed for integration with
DataManager's ``fetch_ohlcv`` interface.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class OpenBBMCPProvider:
    """OpenBB MCP-based market data provider.

    Fetches OHLCV data via the OpenBB platform. Tries the OpenBB
    Python SDK first; falls back to the OpenBB Hub REST API.

    Parameters
    ----------
    api_key:
        OpenBB personal access token. Falls back to
        ``OPENBB_API_KEY`` or ``QNAI_OPENBB_API_KEY`` env vars.
    base_url:
        OpenBB Hub API base URL.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openbb.co",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._sdk = None
        self._init_sdk()

    # ------------------------------------------------------------------
    # SDK init
    # ------------------------------------------------------------------

    def _init_sdk(self) -> None:
        """Try to initialise the OpenBB Python SDK."""
        import os

        key = self.api_key or os.getenv("OPENBB_API_KEY") or os.getenv("QNAI_OPENBB_API_KEY")
        if key:
            self.api_key = key

        try:
            from openbb import obb  # type: ignore[import-untyped]

            if self.api_key:
                obb.account.login(pat=self.api_key)
            self._sdk = obb
            logger.info("OpenBB SDK initialised")
        except ImportError:
            logger.info("OpenBB SDK not available, using REST API fallback")
        except Exception as exc:
            logger.warning("OpenBB SDK init failed: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "D1",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV market data.

        Parameters
        ----------
        symbol:
            Ticker symbol, *e.g.* ``"AAPL"``.
        timeframe:
            Candle resolution string (*e.g.* ``"D1"``, ``"H1"``, ``"M1"``).
        start:
            Start datetime (inclusive).
        end:
            End datetime (inclusive).

        Returns
        -------
        pd.DataFrame
            Columns: ``timestamp``, ``open``, ``high``, ``low``,
            ``close``, ``volume``.  Empty DataFrame on error or no data.
        """
        if self._sdk is not None:
            return self._fetch_via_sdk(symbol, timeframe, start, end)
        return self._fetch_via_rest(symbol, timeframe, start, end)

    # ------------------------------------------------------------------
    # SDK path
    # ------------------------------------------------------------------

    @staticmethod
    def _timeframe_to_interval(timeframe: str) -> Optional[str]:
        mapping = {
            "D1": None,
            "H1": "1h",
            "h4": "4h",
            "W1": "1wk",
            "M1": "1mo",
        }
        return mapping.get(timeframe)

    def _fetch_via_sdk(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> pd.DataFrame:
        """Fetch data via the OpenBB Python SDK."""
        try:
            params: dict = {"symbol": symbol, "provider": "yfinance"}
            if start:
                params["start_date"] = start.isoformat()
            if end:
                params["end_date"] = end.isoformat()
            interval = self._timeframe_to_interval(timeframe)
            if interval:
                params["interval"] = interval
            data = self._sdk.equity.price.historical(  # type: ignore[union-attr]
                **params,
            )
            if data is not None and not data.empty:
                df = data.to_dataframe()
                return df.reset_index()
        except Exception as exc:
            logger.warning("OpenBB SDK fetch failed: %s", exc)
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    # ------------------------------------------------------------------
    # REST fallback
    # ------------------------------------------------------------------

    def _fetch_via_rest(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> pd.DataFrame:
        """Fetch data via the OpenBB Hub REST API."""
        import requests

        try:
            params: dict = {"symbol": symbol, "provider": "yfinance"}
            if start:
                params["start_date"] = start.isoformat()
            if end:
                params["end_date"] = end.isoformat()
            interval = self._timeframe_to_interval(timeframe)
            if interval:
                params["interval"] = interval
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.get(
                f"{self.base_url}/api/v1/equity/price/historical",
                params=params,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results") if isinstance(payload, dict) else payload
            if results:
                df = pd.DataFrame(results)
                if "date" in df.columns and "timestamp" not in df.columns:
                    df = df.rename(columns={"date": "timestamp"})
                return df
        except Exception as exc:
            logger.warning("OpenBB REST fetch failed: %s", exc)
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


__all__ = ["OpenBBMCPProvider"]
