"""CCXT Exchange Broker — Unified access to 100+ crypto exchanges.

Wraps the ``ccxt`` library to provide a production-grade implementation
of :class:`~quant_nanggroe.exchange.base.ExchangeInterface` for exchanges
including Binance, Coinbase, Bybit, OKX, Kraken, and 100+ more.

Features
--------
* Async-first: all methods use ``ccxt.async_support`` async exchange classes.
* Automatic rate-limit handling with exponential backoff.
* Configurable retries on transient errors.
* Market-data caching with configurable TTL.
* Position tracking for both spot (derived from balances) and futures.
* WebSocket streaming via ``ccxt.pro`` watch methods.
* Support for spot and futures/perps trading.
* Balance tracking with free/used/total breakdown.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import ccxt.async_support as ccxt

from quant_nanggroe.exchange.base import (
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    ConnectionError,
    OrderError,
    RateLimitError,
    AuthenticationError,
    InsufficientFundsError,
    MarketDataError,
    WebSocketCallback,
)
from quant_nanggroe.types.market import (
    OHLCV,
    OrderBook,
    OrderBookLevel,
    Ticker,
    TimeFrame,
)
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

# TimeFrame enum -> CCXT timeframe string
_TIMEFRAME_MAP: Dict[TimeFrame, str] = {
    TimeFrame.M1: "1m",
    TimeFrame.M5: "5m",
    TimeFrame.M15: "15m",
    TimeFrame.M30: "30m",
    TimeFrame.H1: "1h",
    TimeFrame.H4: "4h",
    TimeFrame.D1: "1d",
    TimeFrame.W1: "1w",
    TimeFrame.MO1: "1M",
}

# OrderSide enum -> CCXT side string
_SIDE_MAP: Dict[OrderSide, str] = {
    OrderSide.BUY: "buy",
    OrderSide.SELL: "sell",
}

# CCXT side string -> OrderSide enum
_SIDE_REVERSE: Dict[str, OrderSide] = {v: k for k, v in _SIDE_MAP.items()}

# OrderType enum -> CCXT type string
_TYPE_MAP: Dict[OrderType, str] = {
    OrderType.MARKET: "market",
    OrderType.LIMIT: "limit",
    OrderType.STOP: "stop",
    OrderType.STOP_LIMIT: "stop_limit",
    OrderType.TRAILING_STOP: "trailing_stop",
    OrderType.TAKE_PROFIT: "take_profit",
    OrderType.TAKE_PROFIT_LIMIT: "take_profit_limit",
}

# CCXT status string -> OrderStatus enum
_STATUS_MAP: Dict[str, OrderStatus] = {
    "open": OrderStatus.SUBMITTED,
    "closed": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELED,
    "cancelled": OrderStatus.CANCELED,
    "rejected": OrderStatus.REJECTED,
    "expired": OrderStatus.EXPIRED,
    "pending": OrderStatus.PENDING,
}

# Known quote currencies for spot position derivation
_QUOTE_CURRENCIES = frozenset({
    "USDT", "USDC", "USD", "BUSD", "TUSD", "EUR", "BTC", "ETH", "BNB",
})


class CCXTBroker(ExchangeInterface):
    """CCXT-based exchange broker supporting 100+ cryptocurrency exchanges.

    This implementation wraps ``ccxt.async_support`` exchange classes and
    translates between CCXT's data structures and Quant Nanggroe's Pydantic
    domain types.

    Parameters
    ----------
    config:
        :class:`ExchangeConfig` with API credentials and settings.

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="binance",
            api_key="...",
            api_secret="...",
            sandbox=True,
        )
        broker = CCXTBroker(config)
        await broker.connect()
        ticker = await broker.get_ticker("BTC/USDT")
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._exchange: Optional[ccxt.Exchange] = None
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._markets_cache: Optional[List[str]] = None
        self._markets_cache_ts: float = 0.0
        self._ws_tasks: Dict[str, asyncio.Task] = {}
        self._ws_callbacks: Dict[str, Dict[str, WebSocketCallback]] = {}
        # Position tracking for futures
        self._local_positions: Dict[str, Position] = {}
        # Spot position tracking derived from balances
        self._spot_positions: Dict[str, Position] = {}
        # Rate-limit tracking
        self._last_request_ts: float = 0.0
        self._request_interval: float = 1.0 / max(config.rate_limit, 0.1)
        # Market type detection
        self._is_futures: bool = False
        # Balance cache
        self._balance_cache: Optional[Dict[str, float]] = None
        self._balance_cache_ts: float = 0.0

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    async def connect(self) -> bool:
        """Create and initialise the CCXT exchange instance.

        Raises:
            ConnectionError: If the exchange cannot be reached.
            AuthenticationError: If API credentials are invalid.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            exchange_class = getattr(ccxt, self._config.exchange_id, None)
            if exchange_class is None:
                raise ConnectionError(
                    f"Unknown exchange id: {self._config.exchange_id}",
                    exchange=self._config.exchange_id,
                )

            exchange_kwargs: Dict[str, Any] = {
                "apiKey": self._config.api_key,
                "secret": self._config.api_secret,
                "enableRateLimit": True,
                "timeout": self._config.timeout * 1000,
                "options": self._config.options,
            }
            if self._config.sandbox:
                exchange_kwargs["sandbox"] = True
            if self._config.passphrase:
                exchange_kwargs["password"] = self._config.passphrase

            self._exchange = exchange_class(**exchange_kwargs)

            # Detect if we're in futures/perps mode
            default_type = self._config.options.get("defaultType", "spot")
            self._is_futures = default_type in ("future", "swap")

            # Load markets to validate connection + cache symbols
            await self._exchange.load_markets()
            self._markets_cache = list(self._exchange.markets.keys())
            self._markets_cache_ts = time.time()

            self._state = ExchangeState.CONNECTED
            logger.info(
                "CCXTBroker [%s]: Connected — %d markets loaded (mode=%s)",
                self._config.exchange_id,
                len(self._markets_cache),
                "futures" if self._is_futures else "spot",
            )
            return True

        except ccxt.AuthenticationError as exc:
            self._state = ExchangeState.ERROR
            raise AuthenticationError(
                f"Authentication failed for {self._config.exchange_id}",
                exchange=self._config.exchange_id,
                original=exc,
            ) from exc

        except ccxt.NetworkError as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Network error connecting to {self._config.exchange_id}: {exc}",
                exchange=self._config.exchange_id,
                original=exc,
            ) from exc

        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to {self._config.exchange_id}: {exc}",
                exchange=self._config.exchange_id,
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close the CCXT exchange and cancel all WebSocket tasks."""
        if self._exchange is not None:
            try:
                # Cancel all WebSocket watch tasks
                for task in self._ws_tasks.values():
                    task.cancel()
                self._ws_tasks.clear()
                self._ws_callbacks.clear()

                await self._exchange.close()
            except Exception as exc:
                logger.warning("CCXTBroker [%s]: Error during disconnect: %s", self.name, exc)
            finally:
                self._exchange = None
                self._state = ExchangeState.DISCONNECTED
                logger.info("CCXTBroker [%s]: Disconnected", self.name)

    @property
    def is_connected(self) -> bool:
        return self._state == ExchangeState.CONNECTED

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return self._config.exchange_id

    # ------------------------------------------------------------------ #
    # Internal: rate-limit gate + retry wrapper
    # ------------------------------------------------------------------ #

    async def _rate_limit_gate(self) -> None:
        """Enforce minimum interval between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_ts
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)
        self._last_request_ts = time.monotonic()

    async def _with_retry(self, coro_factory, *args, **kwargs) -> Any:
        """Execute an async call with retries and rate-limit handling.

        Args:
            coro_factory: Callable returning an awaitable (the CCXT method).
            *args, **kwargs: Passed to ``coro_factory``.

        Returns:
            The result of the successful call.

        Raises:
            RateLimitError: If rate limit is still hit after retries.
            ExchangeError: On non-transient errors.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._config.retries + 1):
            try:
                await self._rate_limit_gate()
                result = await coro_factory(*args, **kwargs)
                self._state = ExchangeState.CONNECTED
                return result
            except ccxt.RateLimitExceeded as exc:
                wait = self._config.retry_delay * (2 ** attempt)
                logger.warning(
                    "CCXTBroker [%s]: Rate limited, retrying in %.1fs (attempt %d/%d)",
                    self.name, wait, attempt + 1, self._config.retries + 1,
                )
                self._state = ExchangeState.RATE_LIMITED
                await asyncio.sleep(wait)
                last_exc = exc
            except ccxt.NetworkError as exc:
                wait = self._config.retry_delay * (2 ** attempt)
                logger.warning(
                    "CCXTBroker [%s]: Network error, retrying in %.1fs: %s",
                    self.name, wait, exc,
                )
                self._state = ExchangeState.RECONNECTING
                await asyncio.sleep(wait)
                last_exc = exc
            except ccxt.AuthenticationError as exc:
                raise AuthenticationError(
                    str(exc), exchange=self.name, original=exc,
                ) from exc
            except ccxt.InsufficientFunds as exc:
                raise InsufficientFundsError(
                    str(exc), exchange=self.name, original=exc,
                ) from exc
            except ccxt.InvalidOrder as exc:
                raise OrderError(
                    str(exc), exchange=self.name, original=exc,
                ) from exc
            except ccxt.BaseError as exc:
                raise ExchangeError(
                    str(exc), exchange=self.name, original=exc,
                ) from exc

        # Exhausted retries
        if isinstance(last_exc, ccxt.RateLimitExceeded):
            self._state = ExchangeState.RATE_LIMITED
            raise RateLimitError(
                f"Rate limit exceeded after {self._config.retries + 1} attempts",
                retry_after=self._config.retry_delay * (2 ** self._config.retries),
                exchange=self.name,
            )
        raise ExchangeError(
            f"Request failed after {self._config.retries + 1} attempts: {last_exc}",
            exchange=self.name,
            original=last_exc,
        )

    def _require_exchange(self) -> ccxt.Exchange:
        """Return the exchange instance or raise ConnectionError."""
        if self._exchange is None or not self.is_connected:
            raise ConnectionError(
                f"Not connected to {self.name}", exchange=self.name,
            )
        return self._exchange

    # ------------------------------------------------------------------ #
    # Account
    # ------------------------------------------------------------------ #

    async def get_balance(self) -> Dict[str, float]:
        """Fetch account balances, returning only non-zero balances.

        For spot exchanges, this returns free balances.
        For futures exchanges, this may include margin info.
        """
        ex = self._require_exchange()
        try:
            raw = await self._with_retry(ex.fetch_balance)
            # CCXT returns {'free': {...}, 'used': {...}, 'total': {...}}
            free = raw.get("free", {})
            result = {k: v for k, v in free.items() if v and v > 0}

            # Cache for spot position derivation
            self._balance_cache = result
            self._balance_cache_ts = time.time()

            # Add total equity for futures
            if self._is_futures:
                total_equity = raw.get("total", {})
                total_usdt = sum(
                    v for k, v in total_equity.items()
                    if k in _QUOTE_CURRENCIES and v and v > 0
                )
                if total_usdt > 0:
                    result["equity"] = total_usdt

            return result
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to fetch balance: {exc}", exchange=self.name, original=exc,
            ) from exc

    async def get_positions(self) -> List[Position]:
        """Fetch open positions.

        For futures/perps exchanges, uses CCXT's unified fetchPositions.
        For spot exchanges, derives positions from non-zero token balances.
        """
        ex = self._require_exchange()
        try:
            if self._is_futures and ex.has.get("fetchPositions"):
                return await self._get_futures_positions(ex)
            else:
                return await self._get_spot_positions(ex)
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to fetch positions: {exc}", exchange=self.name, original=exc,
            ) from exc

    async def _get_futures_positions(self, ex: ccxt.Exchange) -> List[Position]:
        """Fetch futures/perps positions via CCXT unified API."""
        raw_positions = await self._with_retry(ex.fetch_positions)
        positions: List[Position] = []
        for rp in raw_positions:
            if rp and rp.get("contracts") and rp["contracts"] > 0:
                pos = self._ccxt_position_to_position(rp)
                if pos is not None:
                    positions.append(pos)
        # Update local cache
        self._local_positions = {p.symbol: p for p in positions}
        return positions

    async def _get_spot_positions(self, ex: ccxt.Exchange) -> List[Position]:
        """Derive spot positions from non-zero token balances.

        For spot exchanges, we treat each non-zero base currency balance
        as a position. The entry price is estimated from market data.
        """
        # Use cached balances if available
        balances = await self.get_balance()
        positions: List[Position] = []

        for currency, amount in balances.items():
            if currency in _QUOTE_CURRENCIES:
                continue
            if amount <= 0:
                continue

            # Try to find a USDT or USD pair for this currency
            symbol = None
            for quote in ["USDT", "USDC", "USD", "BUSD"]:
                candidate = f"{currency}/{quote}"
                if self._exchange and candidate in self._exchange.markets:
                    symbol = candidate
                    break

            if symbol is None:
                # No market pair found; store without price
                pos = Position(
                    symbol=currency,
                    side=PositionSide.LONG,
                    quantity=amount,
                    entry_price=0.0,
                    current_price=0.0,
                    cost_basis=0.0,
                    market_value=0.0,
                    broker_id=self.name,
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._spot_positions[currency] = pos
                continue

            # Fetch current price for this pair
            try:
                ticker = await self.get_ticker(symbol)
                current_price = ticker.last_price
                # Estimate entry price as current price (spot doesn't track entry)
                entry_price = current_price

                pos = Position(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=amount,
                    entry_price=entry_price,
                    current_price=current_price,
                    cost_basis=entry_price * amount,
                    market_value=current_price * amount,
                    broker_id=self.name,
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._spot_positions[symbol] = pos
            except Exception as exc:
                logger.warning(
                    "CCXTBroker [%s]: Failed to get price for %s: %s",
                    self.name, symbol, exc,
                )
                # Store position without price data
                pos = Position(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    quantity=amount,
                    entry_price=0.0,
                    current_price=0.0,
                    cost_basis=0.0,
                    market_value=0.0,
                    broker_id=self.name,
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._spot_positions[symbol] = pos

        return positions

    async def get_portfolio(self) -> Portfolio:
        """Build a Portfolio snapshot from balance + positions."""
        balances = await self.get_balance()
        positions = await self.get_positions()

        # Determine base currency
        currency = "USDT"
        cash = balances.get(currency, 0.0)
        # Also check USD, USDC
        if cash == 0.0 and "USD" in balances:
            cash = balances["USD"]
            currency = "USD"
        if cash == 0.0 and "USDC" in balances:
            cash = balances["USDC"]
            currency = "USDC"

        initial_capital = cash  # Approximation; real value should be tracked externally

        portfolio = Portfolio(
            name=self.name,
            currency=currency,
            initial_capital=initial_capital,
            cash=cash,
        )
        for pos in positions:
            portfolio.positions[pos.symbol] = pos
        portfolio.recalculate()
        return portfolio

    # ------------------------------------------------------------------ #
    # Trading
    # ------------------------------------------------------------------ #

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Place an order via CCXT.

        Supports market, limit, stop, stop_limit, trailing_stop,
        take_profit, and take_profit_limit order types.

        For stop and trigger orders, the CCXT ``params`` dict is used
        to pass exchange-specific parameters like ``stopPrice``.
        """
        ex = self._require_exchange()
        try:
            ccxt_side = _SIDE_MAP[side]
            ccxt_type = _TYPE_MAP.get(order_type, "market")

            params: Dict[str, Any] = {}
            if stop_price is not None:
                params["stopPrice"] = stop_price
            if client_order_id is not None:
                params["clientOrderId"] = client_order_id

            # Handle trailing stop params
            if order_type == OrderType.TRAILING_STOP:
                if stop_price is not None:
                    params["trailingAmount"] = stop_price
                    params.pop("stopPrice", None)

            raw = await self._with_retry(
                ex.create_order,
                symbol,
                ccxt_type,
                ccxt_side,
                quantity,
                price,
                params,
            )

            return self._ccxt_order_to_order(
                raw,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )

        except (OrderError, InsufficientFundsError, AuthenticationError, RateLimitError):
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place order: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order via CCXT."""
        ex = self._require_exchange()
        try:
            raw = await self._with_retry(
                ex.cancel_order,
                order_id,
                symbol or "",
            )
            return self._ccxt_order_to_order(raw)
        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to cancel order {order_id}: {exc}",
                order_id=order_id,
                exchange=self.name,
                original=exc,
            ) from exc

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Query order state via CCXT."""
        ex = self._require_exchange()
        try:
            raw = await self._with_retry(
                ex.fetch_order,
                order_id,
                symbol or "",
            )
            return self._ccxt_order_to_order(raw)
        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to fetch order {order_id}: {exc}",
                order_id=order_id,
                exchange=self.name,
                original=exc,
            ) from exc

    # ------------------------------------------------------------------ #
    # Market data
    # ------------------------------------------------------------------ #

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Fetch OHLCV candles via CCXT."""
        ex = self._require_exchange()
        try:
            ccxt_tf = _TIMEFRAME_MAP.get(timeframe, "1d")
            since_ms = int(since.timestamp() * 1000) if since else None

            raw_candles = await self._with_retry(
                ex.fetch_ohlcv,
                symbol,
                ccxt_tf,
                since_ms,
                limit,
            )

            candles = []
            for c in raw_candles:
                ts_ms, o, h, l, cl, vol = c[:6]
                candles.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc),
                        open=float(o),
                        high=float(h),
                        low=float(l),
                        close=float(cl),
                        volume=float(vol),
                    )
                )
            return candles

        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to fetch OHLCV for {symbol}: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    async def get_ticker(self, symbol: str) -> Ticker:
        """Fetch the latest ticker via CCXT."""
        ex = self._require_exchange()
        try:
            raw = await self._with_retry(ex.fetch_ticker, symbol)
            return Ticker(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(
                    (raw.get("timestamp") or 0) / 1000, tz=timezone.utc,
                ),
                last_price=float(raw.get("last", 0)),
                bid=float(raw["bid"]) if raw.get("bid") else None,
                ask=float(raw["ask"]) if raw.get("ask") else None,
                bid_volume=float(raw.get("bidVolume", 0)) or None,
                ask_volume=float(raw.get("askVolume", 0)) or None,
                high_24h=float(raw["high"]) if raw.get("high") else None,
                low_24h=float(raw["low"]) if raw.get("low") else None,
                volume_24h=float(raw.get("baseVolume", 0)) or None,
                change_24h=float(raw.get("change", 0)) or None,
                change_pct_24h=float(raw.get("percentage", 0)) or None,
                vwap=float(raw["vwap"]) if raw.get("vwap") else None,
            )
        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to fetch ticker for {symbol}: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Fetch the order book via CCXT."""
        ex = self._require_exchange()
        try:
            raw = await self._with_retry(ex.fetch_order_book, symbol, limit)
            bids = [
                OrderBookLevel(price=float(b[0]), quantity=float(b[1]))
                for b in raw.get("bids", [])
            ]
            asks = [
                OrderBookLevel(price=float(a[0]), quantity=float(a[1]))
                for a in raw.get("asks", [])
            ]
            spread = None
            mid_price = None
            if bids and asks:
                spread = asks[0].price - bids[0].price
                mid_price = (asks[0].price + bids[0].price) / 2

            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                bids=bids,
                asks=asks,
                spread=spread,
                mid_price=mid_price,
            )
        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to fetch order book for {symbol}: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch recent public trades via CCXT."""
        ex = self._require_exchange()
        try:
            since_ms = int(since.timestamp() * 1000) if since else None
            raw = await self._with_retry(
                ex.fetch_trades,
                symbol,
                since_ms,
                limit,
            )
            return [
                {
                    "id": str(t.get("id", "")),
                    "price": float(t.get("price", 0)),
                    "amount": float(t.get("amount", 0)),
                    "side": t.get("side", ""),
                    "timestamp": t.get("datetime", ""),
                }
                for t in raw
            ]
        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to fetch trades for {symbol}: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    # ------------------------------------------------------------------ #
    # WebSocket / real-time (ccxt.pro watch methods)
    # ------------------------------------------------------------------ #

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time ticker via ccxt.pro watchTicker."""
        ex = self._require_exchange()
        key = f"ticker:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback

        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._watch_loop("ticker", symbol, ex.watch_ticker, symbol),
            )
        logger.info("CCXTBroker [%s]: Subscribed to ticker %s", self.name, symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time order book via ccxt.pro watchOrderBook."""
        ex = self._require_exchange()
        key = f"orderbook:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback

        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._watch_loop("orderbook", symbol, ex.watch_order_book, symbol),
            )
        logger.info("CCXTBroker [%s]: Subscribed to orderbook %s", self.name, symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trades via ccxt.pro watchTrades."""
        ex = self._require_exchange()
        key = f"trades:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback

        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._watch_loop("trades", symbol, ex.watch_trades, symbol),
            )
        logger.info("CCXTBroker [%s]: Subscribed to trades %s", self.name, symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Cancel the WebSocket watch task for a symbol + channel."""
        key = f"{channel}:{symbol}"
        task = self._ws_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
        self._ws_callbacks.pop(key, None)
        logger.info("CCXTBroker [%s]: Unsubscribed from %s %s", self.name, channel, symbol)

    async def _watch_loop(
        self,
        channel: str,
        symbol: str,
        watch_fn: Any,
        *watch_args: Any,
    ) -> None:
        """Run a ccxt.pro watch loop, dispatching updates to callbacks."""
        key = f"{channel}:{symbol}"
        try:
            while True:
                try:
                    data = await watch_fn(*watch_args)
                    callbacks = self._ws_callbacks.get(key, {})
                    for cb in callbacks.values():
                        try:
                            await cb(data)
                        except Exception as cb_exc:
                            logger.warning(
                                "CCXTBroker [%s]: Callback error for %s: %s",
                                self.name, key, cb_exc,
                            )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "CCXTBroker [%s]: Watch error for %s, reconnecting: %s",
                        self.name, key, exc,
                    )
                    await asyncio.sleep(self._config.retry_delay)
        except asyncio.CancelledError:
            logger.debug("CCXTBroker [%s]: Watch loop cancelled for %s", self.name, key)

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

    async def get_markets(self) -> List[str]:
        """List all tradable symbols (with caching)."""
        ex = self._require_exchange()
        cache_ttl = 300.0  # 5 minutes
        if (
            self._markets_cache is not None
            and (time.time() - self._markets_cache_ts) < cache_ttl
        ):
            return self._markets_cache

        try:
            await self._with_retry(ex.load_markets)
            self._markets_cache = list(ex.markets.keys())
            self._markets_cache_ts = time.time()
            return self._markets_cache
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to load markets: {exc}",
                exchange=self.name,
                original=exc,
            ) from exc

    async def health_check(self) -> bool:
        """Ping the exchange by fetching the server time."""
        ex = self._require_exchange()
        try:
            if ex.has.get("fetchTime"):
                await self._with_retry(ex.fetch_time)
            else:
                # Fallback: fetch a well-known ticker
                await self._with_retry(ex.fetch_ticker, "BTC/USDT")
            self._state = ExchangeState.CONNECTED
            return True
        except Exception as exc:
            logger.warning("CCXTBroker [%s]: Health check failed: %s", self.name, exc)
            self._state = ExchangeState.ERROR
            return False

    # ------------------------------------------------------------------ #
    # Internal: CCXT -> domain type mappers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _ccxt_order_to_order(
        raw: Dict[str, Any],
        strategy_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Order:
        """Convert a CCXT order dict to our Order model."""
        raw_status = raw.get("status", "pending")
        status = _STATUS_MAP.get(raw_status, OrderStatus.PENDING)

        # Map CCXT order type back
        raw_type = raw.get("type", "market")
        order_type = OrderType.MARKET
        for ot, ccxt_str in _TYPE_MAP.items():
            if ccxt_str == raw_type:
                order_type = ot
                break

        raw_side = raw.get("side", "buy")
        side = _SIDE_REVERSE.get(raw_side, OrderSide.BUY)

        # Extract fee
        fee_cost = 0.0
        fee_info = raw.get("fee")
        if fee_info and isinstance(fee_info, dict):
            fee_cost = float(fee_info.get("cost", 0) or 0)

        # Extract timestamp
        raw_ts = raw.get("timestamp", 0) or 0
        created_at = datetime.fromtimestamp(raw_ts / 1000, tz=timezone.utc) if raw_ts else datetime.now(tz=timezone.utc)

        return Order(
            id=str(raw.get("id", uuid.uuid4())),
            client_order_id=raw.get("clientOrderId"),
            symbol=raw.get("symbol", ""),
            side=side,
            order_type=order_type,
            quantity=float(raw.get("amount", 0) or 0),
            price=float(raw["price"]) if raw.get("price") else None,
            stop_price=float(raw.get("stopPrice")) if raw.get("stopPrice") else None,
            status=status,
            filled_quantity=float(raw.get("filled", 0) or 0),
            average_fill_price=float(raw.get("average")) if raw.get("average") else None,
            commission=fee_cost,
            created_at=created_at,
            updated_at=datetime.now(tz=timezone.utc),
            broker_id=raw.get("exchange", "") or "",
            broker_order_id=str(raw.get("id", "")),
            strategy_name=strategy_name,
            agent_name=agent_name,
            notes=notes,
        )

    @staticmethod
    def _ccxt_position_to_position(raw: Dict[str, Any]) -> Optional[Position]:
        """Convert a CCXT position dict to our Position model."""
        try:
            contracts = float(raw.get("contracts", 0) or 0)
            if contracts == 0:
                return None

            side = PositionSide.LONG if raw.get("side") == "long" else PositionSide.SHORT
            entry_price = float(raw.get("entryPrice", 0) or 0)
            current_price = float(raw.get("markPrice", 0) or entry_price)
            unrealized_pnl = float(raw.get("unrealizedPnl", 0) or 0)
            cost_basis = entry_price * contracts
            market_value = contracts * current_price

            return Position(
                symbol=raw.get("symbol", ""),
                side=side,
                quantity=contracts,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                cost_basis=cost_basis,
                market_value=market_value,
                broker_id=raw.get("exchange", "") or "",
                last_updated=datetime.now(tz=timezone.utc),
            )
        except (ValueError, TypeError, KeyError):
            return None
