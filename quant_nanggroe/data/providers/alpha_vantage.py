"""Alpha Vantage data provider.

Uses the Alpha Vantage API for stock, forex, and crypto market data.
Supports daily/weekly/monthly OHLCV, technical indicators, and fundamentals.

Alpha Vantage API is free (25 req/day) or premium (unlimited):
https://www.alphavantage.co/support/#api-key

Symbol convention:
    - Stocks: ``AV:IBM``, ``AV:AAPL``
    - Forex: ``AV:EUR/USD``
    - Crypto: ``AV:BTC/USD``

Rate limits: 25 requests/day (free), 75/min (premium).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# Map internal TimeFrame to Alpha Vantage function + interval
_TIMEFRAME_CONFIG: Dict[TimeFrame, Dict[str, str]] = {
    TimeFrame.M1: {"function": "TIME_SERIES_INTRADAY", "interval": "1min"},
    TimeFrame.M5: {"function": "TIME_SERIES_INTRADAY", "interval": "5min"},
    TimeFrame.M15: {"function": "TIME_SERIES_INTRADAY", "interval": "15min"},
    TimeFrame.M30: {"function": "TIME_SERIES_INTRADAY", "interval": "30min"},
    TimeFrame.H1: {"function": "TIME_SERIES_INTRADAY", "interval": "60min"},
    TimeFrame.D1: {"function": "TIME_SERIES_DAILY", "interval": ""},
    TimeFrame.W1: {"function": "TIME_SERIES_WEEKLY", "interval": ""},
    TimeFrame.MO1: {"function": "TIME_SERIES_MONTHLY", "interval": ""},
}

# Map function name to the JSON key that holds the time series
_FUNCTION_KEY_MAP: Dict[str, str] = {
    "TIME_SERIES_INTRADAY": "Time Series ({interval})",
    "TIME_SERIES_DAILY": "Time Series (Daily)",
    "TIME_SERIES_DAILY_ADJUSTED": "Time Series (Daily Adjusted)",
    "TIME_SERIES_WEEKLY": "Weekly Time Series",
    "TIME_SERIES_MONTHLY": "Monthly Time Series",
}


class AlphaVantageError(Exception):
    """Alpha Vantage API error."""


def _parse_symbol(symbol: str) -> str:
    """Extract Alpha Vantage symbol from convention.

    Args:
        symbol: Symbol in AV:<ticker> format or raw ticker.

    Returns:
        The Alpha Vantage symbol string.
    """
    if symbol.startswith("AV:"):
        return symbol[3:]
    return symbol


def _detect_asset_type(symbol: str) -> str:
    """Detect asset type from symbol.

    Args:
        symbol: Raw symbol without prefix.

    Returns:
        One of 'stock', 'forex', 'crypto'.
    """
    # Common forex pairs
    forex_pairs = {"EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
                   "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"}
    if symbol in forex_pairs or "/" in symbol:
        parts = symbol.split("/")
        if len(parts) == 2 and len(parts[0]) == 3 and len(parts[1]) == 3:
            return "forex"
    # Common crypto symbols
    crypto_quotes = {"USD", "USDT", "BTC", "ETH", "EUR"}
    if "/" in symbol:
        parts = symbol.split("/")
        if parts[1] in crypto_quotes and parts[0] in {
            "BTC", "ETH", "LTC", "XRP", "DOGE", "ADA", "SOL", "DOT", "MATIC", "AVAX"
        }:
            return "crypto"
    return "stock"


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider.

    Provides stock, forex, and crypto data via the Alpha Vantage API.
    Requires QNAI_ALPHA_VANTAGE_API_KEY environment variable.

    Features:
    - Daily, weekly, monthly, and intraday OHLCV data
    - Stock fundamentals and technical indicators
    - Forex and crypto data support
    - Free tier: 25 requests/day; Premium: 75/min

    Example:
        >>> provider = AlphaVantageProvider(api_key="your-key")
        >>> candles = await provider.get_ohlcv("AV:AAPL", TimeFrame.D1)
        >>> ticker = await provider.get_ticker("AV:IBM")
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(
        self,
        api_key: Optional[str] = None,
        priority: int = 18,
        **kwargs,
    ):
        """Initialize Alpha Vantage provider.

        Args:
            api_key: Alpha Vantage API key. Falls back to QNAI_ALPHA_VANTAGE_API_KEY env var.
            priority: Failover priority (lower = higher priority). Default 18.
        """
        super().__init__(name="alpha_vantage", priority=priority, **kwargs)
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    def _get_api_key(self) -> str:
        """Get Alpha Vantage API key from config or environment."""
        key = self._api_key
        if not key:
            key = os.environ.get("QNAI_ALPHA_VANTAGE_API_KEY", "")
        if not key:
            raise AlphaVantageError(
                "Alpha Vantage API key not configured. Set QNAI_ALPHA_VANTAGE_API_KEY "
                "environment variable or pass api_key parameter."
            )
        return key

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy-initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the Alpha Vantage API.

        Args:
            params: Query parameters (apikey will be added automatically).

        Returns:
            Parsed JSON response.

        Raises:
            AlphaVantageError: On API errors.
        """
        params["apikey"] = self._get_api_key()
        client = self._get_client()

        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            # Alpha Vantage returns errors as JSON with "Error Message" or "Note"
            if "Error Message" in data:
                self.mark_error(f"Alpha Vantage API error: {data['Error Message']}")
                raise AlphaVantageError(data["Error Message"])
            if "Note" in data:
                self.mark_error(f"Alpha Vantage rate limit: {data['Note']}")
                raise AlphaVantageError(f"Rate limited: {data['Note']}")

            return data

        except httpx.HTTPStatusError as e:
            self.mark_error(f"Alpha Vantage HTTP error: {e.response.status_code}")
            raise AlphaVantageError(f"HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            self.mark_error(f"Alpha Vantage request error: {e}")
            raise AlphaVantageError(f"Request failed: {e}") from e

    def _get_time_series_key(self, function: str, interval: str = "") -> str:
        """Get the JSON key for the time series data.

        Args:
            function: Alpha Vantage API function name.
            interval: Time interval for intraday data.

        Returns:
            JSON key string for the time series data.
        """
        key_template = _FUNCTION_KEY_MAP.get(function)
        if key_template and "{interval}" in key_template:
            return key_template.format(interval=interval)
        return key_template or "Time Series (Daily)"

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV data from Alpha Vantage.

        Args:
            symbol: Symbol in AV:<ticker> format or raw ticker.
            timeframe: Candle timeframe.
            start: Start datetime.
            end: End datetime.
            limit: Maximum number of candles.

        Returns:
            List of OHLCV candles sorted by timestamp ascending.
        """
        try:
            raw_symbol = _parse_symbol(symbol)
            asset_type = _detect_asset_type(raw_symbol)
            config = _TIMEFRAME_CONFIG.get(timeframe, _TIMEFRAME_CONFIG[TimeFrame.D1])

            params: Dict[str, Any] = {"datatype": "json"}

            if asset_type == "forex":
                params["function"] = "FX_" + config["function"].replace("TIME_SERIES_", "")
                from_currency, to_currency = raw_symbol.split("/")
                params["from_symbol"] = from_currency
                params["to_symbol"] = to_currency
                ts_key = params["function"].replace("FX_", "Time Series ")
            elif asset_type == "crypto":
                params["function"] = "DIGITAL_CURRENCY_DAILY"
                from_symbol, to_symbol = raw_symbol.split("/")
                params["symbol"] = from_symbol
                params["market"] = to_symbol
                ts_key = "Time Series (Digital Currency Daily)"
            else:
                params["function"] = config["function"]
                params["symbol"] = raw_symbol
                if config["interval"]:
                    params["interval"] = config["interval"]
                ts_key = self._get_time_series_key(
                    config["function"], config["interval"]
                )

            if start:
                params.setdefault("outputsize", "full")

            data = await self._request(params)

            # For intraday, the key may contain the interval
            ts_data = None
            for key in data:
                if "Time Series" in key:
                    ts_data = data[key]
                    break

            if not ts_data:
                self.mark_error(f"No time series data in response for {symbol}")
                return []

            result = []
            for date_str, values in sorted(ts_data.items()):
                try:
                    # Parse date - Alpha Vantage returns various formats
                    ts = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S"
                                           if " " in date_str else "%Y-%m-%d")
                except ValueError:
                    continue

                if start and ts < start:
                    continue
                if end and ts > end:
                    continue

                # Normalize field names (Alpha Vantage uses different prefixes)
                def _get_val(d: dict, *keys: str) -> float:
                    for k in keys:
                        if k in d:
                            return float(d[k])
                    return 0.0

                candle = OHLCV(
                    symbol=symbol,
                    timestamp=ts,
                    open=_get_val(values, "1. open", "1a. open (USD)"),
                    high=_get_val(values, "2. high", "2a. high (USD)"),
                    low=_get_val(values, "3. low", "3a. low (USD)"),
                    close=_get_val(values, "4. close", "4a. close (USD)"),
                    volume=_get_val(values, "5. volume", "6. market cap (USD)"),
                )
                result.append(candle)

            self.mark_success()
            return result[-limit:]

        except AlphaVantageError:
            return []
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Alpha Vantage OHLCV error for {symbol}: {e}")
            return []

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Fetch current ticker data from Alpha Vantage.

        Uses the GLOBAL_QUOTE endpoint for stocks.

        Args:
            symbol: Symbol in AV:<ticker> format or raw ticker.

        Returns:
            Current ticker data.
        """
        try:
            raw_symbol = _parse_symbol(symbol)
            asset_type = _detect_asset_type(raw_symbol)

            if asset_type == "stock":
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": raw_symbol,
                }
                data = await self._request(params)
                quote = data.get("Global Quote", {})

                if not quote:
                    self.mark_error(f"No quote data for {symbol}")
                    return None

                ticker = Ticker(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    last_price=float(quote.get("05. price", 0)),
                    open=float(quote.get("02. open", 0)),
                    high_24h=float(quote.get("03. high", 0)),
                    low_24h=float(quote.get("04. low", 0)),
                    volume_24h=float(quote.get("06. volume", 0)),
                    change_24h=float(quote.get("08. previous close", 0)),
                    change_pct_24h=float(quote.get("10. change percent", "0").rstrip("%")),
                )
                self.mark_success()
                return ticker

            # For forex/crypto, use latest OHLCV
            candles = await self.get_ohlcv(symbol, TimeFrame.D1, limit=1)
            if not candles:
                return None

            c = candles[-1]
            ticker = Ticker(
                symbol=symbol,
                timestamp=c.timestamp,
                last_price=c.close,
                high_24h=c.high,
                low_24h=c.low,
                volume_24h=c.volume,
            )
            self.mark_success()
            return ticker

        except AlphaVantageError:
            return None
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Alpha Vantage ticker error for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[OrderBook]:
        """Alpha Vantage does not support order book data.

        Returns:
            None — Alpha Vantage provides end-of-day and historical data only.
        """
        logger.debug("Alpha Vantage does not support order book data")
        return None

    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Fetch company fundamentals from Alpha Vantage.

        Args:
            symbol: Stock symbol in AV:<ticker> format or raw ticker.

        Returns:
            Dict with company overview data.
        """
        try:
            raw_symbol = _parse_symbol(symbol)
            params = {
                "function": "OVERVIEW",
                "symbol": raw_symbol,
            }
            data = await self._request(params)
            self.mark_success()
            return data
        except Exception as e:
            self.mark_error(str(e))
            logger.warning(f"Alpha Vantage fundamentals error for {symbol}: {e}")
            return {}

    async def health_check(self) -> bool:
        """Check if the Alpha Vantage API is accessible.

        Returns:
            True if the API responds successfully.
        """
        try:
            params: Dict[str, Any] = {
                "function": "GLOBAL_QUOTE",
                "symbol": "IBM",
            }
            await self._request(params)
            self._is_available = True
            return True
        except Exception as e:
            self._is_available = False
            self._last_error = str(e)
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
