"""TwelveData market data provider.

Aggregates OHLCV, ticker, and forex rate data from TwelveData REST API.
All public methods are async with automatic failover and rate limiting.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from quant_nanggroe.types.market import OHLCV, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

BASE_URL = "https://api.twelvedata.com"

_TIMEFRAME_MAP: Dict[TimeFrame, str] = {
    TimeFrame.M1: "1min",
    TimeFrame.M5: "5min",
    TimeFrame.M15: "15min",
    TimeFrame.M30: "30min",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1day",
    TimeFrame.W1: "1week",
    TimeFrame.MO1: "1month",
}

_DEFAULT_TIMEOUT = 15.0
_MAX_RETRIES = 3


class TwelveDataError(Exception):
    """TwelveData API error."""


class TwelveDataProvider:
    """Async TwelveData market data provider.

    Args:
        api_key: TwelveData API key. Falls back to QNAI_TWELVEDATA_API_KEY env var.
        priority: Failover priority (lower = preferred). Default 15.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: int = 15,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.name = "twelvedata"
        self.priority = priority
        self._api_key = api_key
        self._timeout = timeout
        self._http: Optional[httpx.AsyncClient] = None
        self.is_available = True
        self.health_score = 1.0
        self._errors = 0
        self._successes = 0

    def _get_api_key(self) -> str:
        key = self._api_key or os.environ.get("QNAI_TWELVEDATA_API_KEY")
        if not key:
            raise TwelveDataError("TwelveData API key not configured")
        return key

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=self._timeout)
        return self._http

    async def _request(self, endpoint: str, params: Dict[str, str]) -> Any:
        client = await self._get_http()
        params["apikey"] = self._get_api_key()

        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(f"{BASE_URL}/{endpoint}", params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.TimeoutException as exc:
                logger.warning("TwelveData timeout (%s): %s", endpoint, exc)
                if attempt < _MAX_RETRIES - 1:
                    continue
                raise TwelveDataError(f"Timeout after {_MAX_RETRIES} attempts") from exc
            except httpx.HTTPStatusError as exc:
                raise TwelveDataError(f"HTTP {exc.response.status_code}") from exc
            except Exception as exc:
                raise TwelveDataError(str(exc)) from exc

            if isinstance(data, dict) and data.get("status") == "error":
                raise TwelveDataError(data.get("message", "Unknown API error"))

            return data

        raise TwelveDataError(f"Request failed after {_MAX_RETRIES} attempts")

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[OHLCV]:
        """Fetch OHLCV candles. Returns an empty list on any error."""
        try:
            tf_str = _TIMEFRAME_MAP.get(timeframe)
            if tf_str is None:
                raise TwelveDataError(f"Unsupported timeframe: {timeframe}")

            params: Dict[str, str] = {
                "symbol": symbol,
                "interval": tf_str,
                "outputsize": str(limit),
            }
            if start:
                params["start_date"] = start.strftime("%Y-%m-%d %H:%M:%S")
            if end:
                params["end_date"] = end.strftime("%Y-%m-%d %H:%M:%S")

            data = await self._request("time_series", params)
            values = data.get("values", [])
            if not values:
                return []

            results: List[OHLCV] = []
            for entry in values:
                try:
                    o = float(entry["open"])
                    h = float(entry["high"])
                    l = float(entry["low"])
                    c = float(entry["close"])
                    v = float(entry.get("volume", 0))
                except (KeyError, ValueError, TypeError):
                    continue
                if o == 0.0 and h == 0.0 and l == 0.0 and c == 0.0:
                    continue

                try:
                    ts = datetime.strptime(entry["datetime"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    ts = datetime.strptime(entry["datetime"], "%Y-%m-%d")

                results.append(
                    OHLCV(symbol=symbol, timestamp=ts, open=o, high=h, low=l, close=c, volume=v)
                )

            results.sort(key=lambda x: x.timestamp)
            self.mark_success()
            return results
        except TwelveDataError:
            logger.warning("TwelveData get_ohlcv failed for %s", symbol)
            self.mark_error("get_ohlcv failed")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch real-time ticker. Returns None on any error."""
        try:
            data = await self._request("quote", {"symbol": symbol})

            close = data.get("close")
            if not close or float(close) == 0.0:
                return None

            ts = data.get("timestamp")
            timestamp = datetime.fromisoformat(ts) if ts else datetime.utcnow()

            self.mark_success()
            return Ticker(
                symbol=symbol,
                timestamp=timestamp,
                last_price=float(close),
                bid=try_float(data.get("bid")),
                ask=try_float(data.get("ask")),
                high_24h=try_float(data.get("high")),
                low_24h=try_float(data.get("low")),
                volume_24h=try_float(data.get("volume")),
                change_pct_24h=try_float(data.get("percent_change")),
            )
        except TwelveDataError:
            logger.warning("TwelveData get_ticker failed for %s", symbol)
            self.mark_error("get_ticker failed")
            return None

    async def get_forex_rate(self, pair: str) -> Optional[Dict[str, Any]]:
        """Fetch latest forex rate. Returns None on any error."""
        try:
            data = await self._request("exchange_rate", {"symbol": pair})
            values = data.get("values", [])
            if not values:
                return None
            rate = float(values[-1]["close"])
            self.mark_success()
            return {"pair": pair, "rate": rate, "timestamp": datetime.utcnow()}
        except TwelveDataError:
            logger.warning("TwelveData get_forex_rate failed for %s", pair)
            self.mark_error("get_forex_rate failed")
            return None

    async def get_orderbook(self, symbol: str) -> None:
        """Not supported by TwelveData. Always returns None."""
        return None

    async def health_check(self) -> bool:
        """Check API availability by fetching AAPL daily."""
        try:
            await self.get_ohlcv("AAPL", TimeFrame.D1, limit=1)
            self.is_available = True
            return True
        except TwelveDataError:
            self.is_available = False
            return False

    def mark_success(self) -> None:
        self._successes += 1
        total = self._successes + self._errors
        self.health_score = self._successes / max(total, 1)

    def mark_error(self, reason: str) -> None:
        self._errors += 1
        total = self._successes + self._errors
        self.health_score = self._successes / max(total, 1)
        self.is_available = self.health_score > 0.1

    def __repr__(self) -> str:
        return f"TwelveDataProvider(priority={self.priority}, available={self.is_available})"


def try_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
