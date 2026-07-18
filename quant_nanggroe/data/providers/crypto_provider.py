"""
Crypto Market Data Provider for Quant Nanggroe AI Trading Framework.

Aggregates OHLCV data from Bybit, OKX, and Kraken via CCXT with
automatic failover, rate limiting, and exponential-backoff retry.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from quant_nanggroe.data.providers.base import DataProvider
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

SUPPORTED_TIMEFRAMES = frozenset({"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"})
EXCHANGE_PRIORITY = ["bybit", "okx", "kraken"]
_MAX_REQUESTS_PER_SECOND = 10
_MAX_RETRIES = 3
_RETRY_BACKOFF_MULTIPLIER = 2.0
_BASE_RETRY_DELAY = 1.0
_RATE_LIMIT_INTERVAL = 1.0 / _MAX_REQUESTS_PER_SECOND

_TIMEFRAME_MAP = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1w",
}


def _parse_since(since: Optional[str]) -> Optional[int]:
    """Parse ISO datetime string to millisecond timestamp (CCXT convention)."""
    if since is None:
        return None
    try:
        dt = datetime.fromisoformat(since)
        return int(dt.timestamp() * 1000)
    except (ValueError, TypeError):
        logger.warning("Invalid 'since' format '%s', ignoring", since)
        return None


class CryptoProvider:
    """Multi-exchange crypto market data provider with auto-failover.

    Tries Bybit first, then OKX, then Kraken. Uses CCXT for exchange
    communication and handles rate limiting + retry internally.

    Parameters
    ----------
    api_keys:
        Optional dict mapping exchange name to its API credentials.
        Public endpoints work without keys (rate-limited).
    """

    def __init__(
        self,
        api_keys: Optional[Dict[str, Dict[str, str]]] = None,
    ) -> None:
        self._api_keys = api_keys or {}
        self._exchanges: Dict[str, Any] = {}
        self._async_exchanges: Dict[str, Any] = {}
        self._last_request: Dict[str, float] = {}

    # ── Exchange initialization ───────────────────────────────────────────────

    def _build_exchange_config(self, name: str) -> Dict[str, Any]:
        """Build CCXT config dict, injecting API keys if provided."""
        config: Dict[str, Any] = {
            "enableRateLimit": False,
        }
        keys = self._api_keys.get(name, {})
        if keys.get("apiKey") and keys.get("secret"):
            config["apiKey"] = keys["apiKey"]
            config["secret"] = keys["secret"]
            if "password" in keys:
                config["password"] = keys["password"]
        return config

    def _get_exchange(self, name: str) -> Any:
        """Get or create a synchronous CCXT exchange instance."""
        if name not in self._exchanges:
            import ccxt

            exchange_class = getattr(ccxt, name, None)
            if exchange_class is None:
                raise ValueError(f"Unsupported exchange: {name}")
            self._exchanges[name] = exchange_class(self._build_exchange_config(name))
        return self._exchanges[name]

    def _get_async_exchange(self, name: str) -> Any:
        """Get or create an async CCXT exchange instance."""
        if name not in self._async_exchanges:
            import ccxt.async_support as ccxt_async

            exchange_class = getattr(ccxt_async, name, None)
            if exchange_class is None:
                raise ValueError(f"Unsupported exchange: {name}")
            self._async_exchanges[name] = exchange_class(
                self._build_exchange_config(name)
            )
        return self._async_exchanges[name]

    # ── Rate limiting ─────────────────────────────────────────────────────────

    async def _throttle(self, exchange_name: str) -> None:
        """Sleep if needed to stay under ``_MAX_REQUESTS_PER_SECOND``."""
        now = time.monotonic()
        last = self._last_request.get(exchange_name, 0.0)
        elapsed = now - last
        if elapsed < _RATE_LIMIT_INTERVAL:
            await asyncio.sleep(_RATE_LIMIT_INTERVAL - elapsed)
        self._last_request[exchange_name] = time.monotonic()

    # ── Core fetch with retry ─────────────────────────────────────────────────

    async def _fetch_ohlcv_single(
        self,
        exchange_name: str,
        symbol: str,
        timeframe: str,
        since: Optional[int],
        limit: int,
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV from a single exchange with exponential-backoff retry.

        Returns ``None`` when all retries are exhausted.
        """
        exchange = self._get_async_exchange(exchange_name)

        for attempt in range(_MAX_RETRIES):
            try:
                await self._throttle(exchange_name)
                raw = await exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=since,
                    limit=limit,
                )
                if not raw:
                    logger.warning("Empty response from %s for %s", exchange_name, symbol)
                    return None

                df = pd.DataFrame(
                    raw,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                return df

            except Exception as exc:
                logger.warning(
                    "Attempt %d/%d failed for %s %s: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exchange_name,
                    symbol,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    delay = _BASE_RETRY_DELAY * (_RETRY_BACKOFF_MULTIPLIER**attempt)
                    await asyncio.sleep(delay)

        logger.error(
            "All %d retries exhausted for %s %s on %s",
            _MAX_RETRIES,
            symbol,
            timeframe,
            exchange_name,
        )
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """Fetch OHLCV data with auto-failover across exchanges.

        Tries exchanges in priority order: bybit → okx → kraken.

        Parameters
        ----------
        symbol:
            Trading pair, e.g. ``"BTC/USDT"``.
        timeframe:
            Candle interval. One of ``1m``, ``5m``, ``15m``, ``30m``,
            ``1h``, ``4h``, ``1d``, ``1w``.
        since:
            ISO-8601 datetime string, e.g. ``"2024-01-01T00:00:00"``.
        limit:
            Maximum number of candles to return.

        Returns
        -------
        pd.DataFrame
            Columns: ``timestamp``, ``open``, ``high``, ``low``, ``close``, ``volume``.

        Raises
        ------
        ValueError
            If *timeframe* is not in ``SUPPORTED_TIMEFRAMES``.
        RuntimeError
            If every exchange in the priority list returns no data.
        """
        if timeframe not in SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported timeframe '{timeframe}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_TIMEFRAMES))}"
            )

        since_ms = _parse_since(since)
        errors: List[str] = []

        for exchange_name in EXCHANGE_PRIORITY:
            df = await self._fetch_ohlcv_single(
                exchange_name=exchange_name,
                symbol=symbol,
                timeframe=timeframe,
                since=since_ms,
                limit=limit,
            )
            if df is not None and not df.empty:
                return df
            errors.append(f"{exchange_name}: no data returned")

        raise RuntimeError(
            f"All exchanges failed for {symbol} {timeframe}: {'; '.join(errors)}"
        )

    # ── Sync wrapper ─────────────────────────────────────────────────────────
    # ponytail: reuses running loop when possible; falls back to new thread+loop

    def fetch_ohlcv_sync(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[str] = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        """Synchronous convenience wrapper around :meth:`fetch_ohlcv`.

        Handles both running-event-loop and no-loop environments.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.fetch_ohlcv(symbol, timeframe, since, limit))

        # ponytail: running loop detected — offload to a fresh loop in a thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                lambda: asyncio.run(
                    self.fetch_ohlcv(symbol, timeframe, since, limit)
                )
            )
            return future.result()

    def get_exchanges(self) -> List[str]:
        """Return list of configured exchange names in priority order."""
        return list(EXCHANGE_PRIORITY)

    async def close(self) -> None:
        """Close all open async exchange connections."""
        for name, exchange in self._async_exchanges.items():
            try:
                await exchange.close()
            except Exception as exc:
                logger.debug("Error closing async %s: %s", name, exc)
        self._async_exchanges.clear()
        self._exchanges.clear()

    async def __aenter__(self) -> CryptoProvider:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


class CryptoProviderAdapter(DataProvider):
    """Adapter wrapping CryptoProvider to conform to the DataProvider ABC."""

    def __init__(self, wrapped: CryptoProvider) -> None:
        super().__init__(name="crypto", priority=10)
        self._wrapped = wrapped

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        tf_str = _TIMEFRAME_MAP.get(timeframe, "1d")
        since_iso = start.isoformat() if start else None
        df = await self._wrapped.fetch_ohlcv(symbol, timeframe=tf_str, since=since_iso, limit=limit)
        if df.empty:
            return []
        results: List[OHLCV] = []
        for _, row in df.iterrows():
            try:
                results.append(OHLCV(
                    symbol=symbol,
                    timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0)),
                ))
            except Exception:
                continue
        return results

    async def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            last_price=0.0,
        )

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        return OrderBook(
            symbol=symbol,
            timestamp=datetime.utcnow(),
        )

    async def health_check(self) -> bool:
        try:
            await self._wrapped.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=1)
            return True
        except Exception:
            return False
