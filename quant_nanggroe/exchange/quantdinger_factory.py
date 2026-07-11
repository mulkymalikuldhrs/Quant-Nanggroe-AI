"""QuantDinger Multi-Exchange Factory — Unified Multi-Market Data & Trading.

Provides a factory that creates exchange adapters for 9+ cryptocurrency
exchanges and multiple market data sources (US stock, CN stock, futures,
forex), ported from the QuantDinger backend architecture.

Features
--------
* Factory pattern for creating exchange adapters
* Support for: Binance, Bybit, OKX, KuCoin, Kraken, Gate, Bitfinex, Bitget, Coinbase
* Data source factory: crypto, US stock, CN stock, futures, forex
* Consistent BaseExchange interface across all adapters
* Market type detection and appropriate data source routing
* Graceful fallback when exchange APIs are unavailable

Dependencies
------------
Requires ``ccxt`` for crypto exchange connectivity (already installed).
Optional: ``yfinance`` for stock data, ``akshare`` for CN stock.

Notes
-----
This factory creates adapters that wrap the existing CCXTBroker with
market-specific configurations and additional data source capabilities.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from quant_nanggroe.exchange.base import (
    ExchangeError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Market type enumeration
# ---------------------------------------------------------------------------

class MarketType(str, Enum):
    """Supported market types for data source routing."""
    CRYPTO = "crypto"
    US_STOCK = "us_stock"
    CN_STOCK = "cn_stock"
    FUTURES = "futures"
    FOREX = "forex"


# ---------------------------------------------------------------------------
# Base Exchange Adapter
# ---------------------------------------------------------------------------

class BaseExchangeAdapter(ABC):
    """Abstract base class for QuantDinger-style exchange adapters.

    Each adapter provides a consistent interface for a specific exchange,
    wrapping the CCXT implementation with additional capabilities.
    """

    @abstractmethod
    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch kline (OHLCV) data.

        Args:
            symbol: Trading pair (e.g., "BTC/USDT").
            timeframe: Candle interval (e.g., "1m", "5m", "1h", "1d").
            limit: Maximum number of candles.
            before_time: Timestamp for pagination.

        Returns:
            List of kline dicts with keys: time, open, high, low, close, volume.
        """

    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> float:
        """Get the current price for a symbol.

        Args:
            symbol: Trading pair.

        Returns:
            Current price as float.
        """

    @abstractmethod
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book snapshot.

        Args:
            symbol: Trading pair.
            limit: Depth per side.

        Returns:
            Dict with 'bids' and 'asks' lists.
        """

    @abstractmethod
    def get_exchange_name(self) -> str:
        """Return the exchange name identifier."""

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Return list of commonly supported symbols."""


# ---------------------------------------------------------------------------
# Crypto Exchange Adapters
# ---------------------------------------------------------------------------

class _CCXTAdapter(BaseExchangeAdapter):
    """Generic CCXT-based exchange adapter.

    Wraps the existing CCXTBroker or uses ccxt directly for data access.
    """

    def __init__(self, exchange_id: str = "binance", config: Optional[Dict[str, Any]] = None) -> None:
        self._exchange_id = exchange_id
        self._config = config or {}
        self._exchange = None

    async def _ensure_exchange(self):
        """Lazily initialize the CCXT exchange instance."""
        if self._exchange is None:
            try:
                import ccxt.async_support as ccxt_async  # type: ignore[import-untyped]

                exchange_class = getattr(ccxt_async, self._exchange_id, None)
                if exchange_class is None:
                    raise ExchangeError(
                        f"CCXT exchange '{self._exchange_id}' not found",
                        exchange=self._exchange_id,
                    )

                self._exchange = exchange_class({
                    "apiKey": self._config.get("api_key", ""),
                    "secret": self._config.get("api_secret", ""),
                    "sandbox": self._config.get("sandbox", False),
                    "enableRateLimit": True,
                })
            except ImportError:
                raise ImportError("ccxt is required for crypto exchange adapters")
        return self._exchange

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        exchange = await self._ensure_exchange()
        try:
            params = {}
            if before_time:
                params["since"] = before_time

            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit, params=params)

            klines = []
            for candle in ohlcv:
                klines.append({
                    "time": int(candle[0] / 1000),
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })
            klines.sort(key=lambda x: x["time"])
            return klines
        except Exception as exc:
            logger.error("Failed to fetch kline from %s: %s", self._exchange_id, exc)
            return []

    async def get_ticker_price(self, symbol: str) -> float:
        exchange = await self._ensure_exchange()
        try:
            ticker = await exchange.fetch_ticker(symbol)
            return float(ticker.get("last", 0) or 0)
        except Exception as exc:
            logger.error("Failed to fetch ticker from %s: %s", self._exchange_id, exc)
            return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        exchange = await self._ensure_exchange()
        try:
            book = await exchange.fetch_order_book(symbol, limit=limit)
            return {
                "bids": book.get("bids", []),
                "asks": book.get("asks", []),
            }
        except Exception as exc:
            logger.error("Failed to fetch orderbook from %s: %s", self._exchange_id, exc)
            return {"bids": [], "asks": []}

    def get_exchange_name(self) -> str:
        return self._exchange_id

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

    async def close(self) -> None:
        """Close the exchange connection."""
        if self._exchange:
            await self._exchange.close()
            self._exchange = None


class BinanceAdapter(_CCXTAdapter):
    """Binance exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("binance", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
                "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "MATIC/USDT"]


class BybitAdapter(_CCXTAdapter):
    """Bybit exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("bybit", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]


class OKXAdapter(_CCXTAdapter):
    """OKX exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("okx", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "OKB/USDT", "SOL/USDT"]


class KuCoinAdapter(_CCXTAdapter):
    """KuCoin exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("kucoin", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "KCS/USDT", "SOL/USDT"]


class KrakenAdapter(_CCXTAdapter):
    """Kraken exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("kraken", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USD", "ETH/USD", "XRP/USD", "SOL/USD"]


class GateAdapter(_CCXTAdapter):
    """Gate.io exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("gate", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "GT/USDT"]


class BitfinexAdapter(_CCXTAdapter):
    """Bitfinex exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("bitfinex", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USD", "ETH/USD", "LEO/USD"]


class BitgetAdapter(_CCXTAdapter):
    """Bitget exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("bitget", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USDT", "ETH/USDT", "BGB/USDT"]


class CoinbaseAdapter(_CCXTAdapter):
    """Coinbase exchange adapter."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("coinbase", config)

    def get_supported_symbols(self) -> List[str]:
        return ["BTC/USD", "ETH/USD", "SOL/USD"]


# ---------------------------------------------------------------------------
# Data Source Adapters (non-crypto)
# ---------------------------------------------------------------------------

class _YFinanceAdapter(BaseExchangeAdapter):
    """US Stock data adapter using yfinance."""

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            import yfinance as yf

            interval_map = {
                "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                "1h": "1h", "1d": "1d", "1w": "1wk", "1M": "1mo",
            }
            yf_interval = interval_map.get(timeframe, "1d")

            ticker = yf.Ticker(symbol)
            period = "1y" if limit > 60 else "3mo"
            df = ticker.history(period=period, interval=yf_interval)

            klines = []
            for idx, row in df.iterrows():
                klines.append({
                    "time": int(idx.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                })
                if len(klines) >= limit:
                    break

            klines.sort(key=lambda x: x["time"])
            return klines[-limit:]
        except ImportError:
            logger.warning("yfinance not installed; returning empty klines")
            return []
        except Exception as exc:
            logger.error("Failed to fetch yfinance kline for %s: %s", symbol, exc)
            return []

    async def get_ticker_price(self, symbol: str) -> float:
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        return {"bids": [], "asks": [], "note": "Order book not available for stocks via yfinance"}

    def get_exchange_name(self) -> str:
        return "yfinance"

    def get_supported_symbols(self) -> List[str]:
        return ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "SPY", "QQQ"]


class _AKShareAdapter(BaseExchangeAdapter):
    """CN Stock (A-Share) data adapter using akshare."""

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            import akshare as ak  # type: ignore[import-untyped]

            period_map = {"1d": "daily", "1w": "weekly", "1M": "monthly"}
            period = period_map.get(timeframe, "daily")

            df = ak.stock_zh_a_hist(symbol=symbol, period=period, adjust="qfq")

            klines = []
            for _, row in df.tail(limit).iterrows():
                klines.append({
                    "time": int(datetime.strptime(str(row["日期"]), "%Y-%m-%d").timestamp()),
                    "open": float(row["开盘"]),
                    "high": float(row["最高"]),
                    "low": float(row["最低"]),
                    "close": float(row["收盘"]),
                    "volume": float(row["成交量"]),
                })
            klines.sort(key=lambda x: x["time"])
            return klines
        except ImportError:
            logger.warning("akshare not installed; returning empty klines")
            return []
        except Exception as exc:
            logger.error("Failed to fetch akshare kline for %s: %s", symbol, exc)
            return []

    async def get_ticker_price(self, symbol: str) -> float:
        klines = await self.get_kline(symbol, limit=1)
        if klines:
            return klines[-1]["close"]
        return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        return {"bids": [], "asks": [], "note": "Order book not available via akshare"}

    def get_exchange_name(self) -> str:
        return "akshare"

    def get_supported_symbols(self) -> List[str]:
        return ["000001", "600519", "000858", "601318"]


class _FuturesAdapter(BaseExchangeAdapter):
    """Futures data adapter (uses yfinance for futures quotes)."""

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}=F")
            df = ticker.history(period="1y", interval="1d")
            klines = []
            for idx, row in df.tail(limit).iterrows():
                klines.append({
                    "time": int(idx.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                })
            klines.sort(key=lambda x: x["time"])
            return klines
        except Exception as exc:
            logger.error("Failed to fetch futures kline for %s: %s", symbol, exc)
            return []

    async def get_ticker_price(self, symbol: str) -> float:
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}=F")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        return {"bids": [], "asks": []}

    def get_exchange_name(self) -> str:
        return "futures"

    def get_supported_symbols(self) -> List[str]:
        return ["ES", "NQ", "CL", "GC", "SI", "ZN"]


class _ForexAdapter(BaseExchangeAdapter):
    """Forex data adapter (uses yfinance for forex quotes)."""

    async def get_kline(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        try:
            import yfinance as yf

            ticker = yf.Ticker(f"{symbol}=X")
            df = ticker.history(period="1y", interval="1d")
            klines = []
            for idx, row in df.tail(limit).iterrows():
                klines.append({
                    "time": int(idx.timestamp()),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                })
            klines.sort(key=lambda x: x["time"])
            return klines
        except Exception as exc:
            logger.error("Failed to fetch forex kline for %s: %s", symbol, exc)
            return []

    async def get_ticker_price(self, symbol: str) -> float:
        try:
            import yfinance as yf
            ticker = yf.Ticker(f"{symbol}=X")
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            return 0.0
        except Exception:
            return 0.0

    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        return {"bids": [], "asks": []}

    def get_exchange_name(self) -> str:
        return "forex"

    def get_supported_symbols(self) -> List[str]:
        return ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCNY"]


# ---------------------------------------------------------------------------
# QuantDinger Factory
# ---------------------------------------------------------------------------

# Adapter registry
_EXCHANGE_ADAPTERS: Dict[str, type] = {
    "binance": BinanceAdapter,
    "bybit": BybitAdapter,
    "okx": OKXAdapter,
    "kucoin": KuCoinAdapter,
    "kraken": KrakenAdapter,
    "gate": GateAdapter,
    "bitfinex": BitfinexAdapter,
    "bitget": BitgetAdapter,
    "coinbase": CoinbaseAdapter,
}

_DATA_SOURCE_ADAPTERS: Dict[str, type] = {
    MarketType.CRYPTO: _CCXTAdapter,
    MarketType.US_STOCK: _YFinanceAdapter,
    MarketType.CN_STOCK: _AKShareAdapter,
    MarketType.FUTURES: _FuturesAdapter,
    MarketType.FOREX: _ForexAdapter,
}

# Cache for adapter instances
_adapter_cache: Dict[str, BaseExchangeAdapter] = {}


class QuantDingerFactory:
    """Factory for creating multi-exchange and multi-market data adapters.

    Follows the QuantDinger architecture pattern to provide consistent
    access to 9+ crypto exchanges and multiple data source types.

    Usage::

        factory = QuantDingerFactory()

        # Create a Binance adapter
        binance = factory.create_exchange_adapter("binance")
        klines = await binance.get_kline("BTC/USDT", "1h", 100)

        # Create a data source by market type
        stock_source = factory.create_data_source("us_stock")
        prices = await stock_source.get_ticker_price("AAPL")

        # Use convenience method
        klines = await factory.get_kline("crypto", "BTC/USDT", "1h", 100)
    """

    def __init__(self, default_config: Optional[Dict[str, Any]] = None) -> None:
        self._default_config = default_config or {}

    def create_exchange_adapter(
        self,
        exchange_name: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseExchangeAdapter:
        """Create an exchange adapter by name.

        Args:
            exchange_name: Exchange identifier (e.g., "binance", "bybit").
            config: Optional exchange-specific configuration.

        Returns:
            BaseExchangeAdapter instance.

        Raises:
            ValueError: If exchange_name is not supported.
        """
        key = exchange_name.lower().strip()

        # Check cache
        cache_key = f"exchange:{key}"
        if cache_key in _adapter_cache:
            return _adapter_cache[cache_key]

        # Check registry
        adapter_class = _EXCHANGE_ADAPTERS.get(key)
        if adapter_class is not None:
            merged_config = {**self._default_config, **(config or {})}
            adapter = adapter_class(config=merged_config)
            _adapter_cache[cache_key] = adapter
            return adapter

        # Fallback: try as generic CCXT adapter
        logger.info("Creating generic CCXT adapter for '%s'", exchange_name)
        merged_config = {**self._default_config, **(config or {})}
        adapter = _CCXTAdapter(exchange_name, config=merged_config)
        _adapter_cache[cache_key] = adapter
        return adapter

    def create_data_source(
        self,
        market_type: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> BaseExchangeAdapter:
        """Create a data source adapter by market type.

        Args:
            market_type: Market type (crypto, us_stock, cn_stock, futures, forex).
            config: Optional configuration.

        Returns:
            BaseExchangeAdapter instance for the market type.

        Raises:
            ValueError: If market_type is not supported.
        """
        key = market_type.lower().strip()

        # Map aliases
        alias_map = {
            "crypto": MarketType.CRYPTO,
            "binance": MarketType.CRYPTO,
            "okx": MarketType.CRYPTO,
            "bybit": MarketType.CRYPTO,
            "bitget": MarketType.CRYPTO,
            "kucoin": MarketType.CRYPTO,
            "gate": MarketType.CRYPTO,
            "mexc": MarketType.CRYPTO,
            "kraken": MarketType.CRYPTO,
            "coinbase": MarketType.CRYPTO,
            "us_stock": MarketType.US_STOCK,
            "usstock": MarketType.US_STOCK,
            "us": MarketType.US_STOCK,
            "cn_stock": MarketType.CN_STOCK,
            "ashare": MarketType.CN_STOCK,
            "cn": MarketType.CN_STOCK,
            "hshare": MarketType.CN_STOCK,
            "futures": MarketType.FUTURES,
            "forex": MarketType.FOREX,
        }

        market_enum = alias_map.get(key)
        if market_enum is None:
            # Default to crypto
            logger.warning("Unknown market type '%s', defaulting to crypto", key)
            market_enum = MarketType.CRYPTO

        # Check cache
        cache_key = f"datasource:{market_enum.value}"
        if cache_key in _adapter_cache:
            return _adapter_cache[cache_key]

        # Create adapter
        adapter_class = _DATA_SOURCE_ADAPTERS.get(market_enum)
        if adapter_class is None:
            raise ValueError(f"Unsupported market type: {market_type}")

        adapter = adapter_class()
        _adapter_cache[cache_key] = adapter
        return adapter

    async def get_kline(
        self,
        market: str,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
        before_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Convenience method: fetch kline data for any market.

        Args:
            market: Market type or exchange name.
            symbol: Trading pair or ticker.
            timeframe: Candle interval.
            limit: Maximum number of candles.
            before_time: Timestamp for pagination.

        Returns:
            List of kline dicts.
        """
        try:
            # Try as exchange adapter first
            if market.lower() in _EXCHANGE_ADAPTERS:
                adapter = self.create_exchange_adapter(market)
            else:
                adapter = self.create_data_source(market)

            klines = await adapter.get_kline(symbol, timeframe, limit, before_time)
            klines.sort(key=lambda x: x["time"])
            return klines
        except Exception as exc:
            logger.error("Failed to fetch klines for %s:%s - %s", market, symbol, exc)
            return []

    @staticmethod
    def get_supported_exchanges() -> List[str]:
        """Get list of supported exchange names."""
        return list(_EXCHANGE_ADAPTERS.keys())

    @staticmethod
    def get_supported_market_types() -> List[str]:
        """Get list of supported market types."""
        return [m.value for m in MarketType]

    async def close_all(self) -> None:
        """Close all cached adapters."""
        for adapter in _adapter_cache.values():
            if hasattr(adapter, "close"):
                try:
                    await adapter.close()
                except Exception as exc:
                    logger.warning("Error closing adapter: %s", exc)
        _adapter_cache.clear()


__all__ = [
    "QuantDingerFactory",
    "BaseExchangeAdapter",
    "MarketType",
    # Crypto exchange adapters
    "BinanceAdapter",
    "BybitAdapter",
    "OKXAdapter",
    "KuCoinAdapter",
    "KrakenAdapter",
    "GateAdapter",
    "BitfinexAdapter",
    "BitgetAdapter",
    "CoinbaseAdapter",
]
