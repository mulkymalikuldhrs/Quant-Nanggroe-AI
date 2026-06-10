"""
Alpaca Broker — Live & Paper Trading via Alpaca API
====================================================
Full implementation of equity/crypto execution through
the Alpaca Trade API with rate limiting, error recovery,
and automatic retry logic.

Features:
    - Market, limit, stop, and stop-limit orders
    - Position and account management
    - Rate-limit aware with exponential backoff
    - Automatic reconnection on transient failures
    - Paper and live mode support

Requirements:
    pip install alpaca-trade-api
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class AlpacaOrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class AlpacaOrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class AlpacaTimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    OPG = "opg"
    CLS = "cls"
    IOC = "ioc"
    FOK = "fok"


class AlpacaOrderResult(BaseModel):
    """Result from an Alpaca order submission."""

    order_id: str
    client_order_id: str = ""
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str = "pending_new"
    limit_price: float | None = None
    filled_price: float | None = None
    filled_quantity: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class AlpacaPosition(BaseModel):
    """Position from Alpaca account."""

    symbol: str
    quantity: float
    side: str  # long / short
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class AlpacaAccountInfo(BaseModel):
    """Alpaca account information."""

    account_id: str = ""
    cash: float = 0.0
    equity: float = 0.0
    buying_power: float = 0.0
    long_market_value: float = 0.0
    short_market_value: float = 0.0
    portfolio_value: float = 0.0
    status: str = "ACTIVE"
    trading_blocked: bool = False
    transfers_blocked: bool = False


# ══════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ══════════════════════════════════════════════════════════════════════


class RateLimiter:
    """
    Token-bucket rate limiter for API calls.

    Alpaca allows ~200 requests per minute. We use a conservative limit.
    """

    def __init__(
        self,
        max_requests: int = 180,
        window_seconds: float = 60.0,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._tokens = max_requests
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request token is available."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            refill = (elapsed / self._window) * self._max_requests
            self._tokens = min(self._max_requests, self._tokens + refill)
            self._last_refill = now

            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self._max_requests * self._window
                logger.debug("Rate limited, waiting %.2f seconds", wait_time)
                await asyncio.sleep(wait_time)
                self._tokens = 0
            else:
                self._tokens -= 1


# ══════════════════════════════════════════════════════════════════════
# ALPACA BROKER
# ══════════════════════════════════════════════════════════════════════


class AlpacaBroker:
    """
    Alpaca API broker for live and paper equity/crypto trading.

    Connects to Alpaca's REST API with automatic rate limiting,
    exponential backoff on errors, and full order lifecycle management.

    Args:
        api_key: Alpaca API key
        secret_key: Alpaca secret key
        base_url: API base URL (paper or live)
        max_retries: Maximum retry attempts on transient errors
        rate_limit: Max requests per minute

    Example:
        broker = AlpacaBroker(
            api_key="PK...",
            secret_key="...",
            base_url="https://paper-api.alpaca.markets",
        )
        order = await broker.buy("AAPL", 10)
    """

    # Alpaca endpoints
    PAPER_URL = "https://paper-api.alpaca.markets"
    LIVE_URL = "https://api.alpaca.markets"

    def __init__(
        self,
        api_key: str = "",
        secret_key: str = "",
        base_url: str | None = None,
        max_retries: int = 3,
        rate_limit: int = 180,
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._base_url = base_url or self.PAPER_URL
        self._max_retries = max_retries
        self._rate_limiter = RateLimiter(max_requests=rate_limit)
        self._client: Any = None
        self._connected = False

        # Track state
        self._order_cache: dict[str, AlpacaOrderResult] = {}

        if api_key and secret_key:
            self._init_client()
        else:
            logger.warning(
                "AlpacaBroker initialized without API keys. "
                "Call connect() with credentials before trading."
            )

    def _init_client(self) -> None:
        """Initialize the Alpaca API client."""
        try:
            import alpaca_trade_api as tradeapi

            self._client = tradeapi.REST(
                key_id=self._api_key,
                secret_key=self._secret_key,
                base_url=self._base_url,
                api_version="v2",
            )
            self._connected = True
            logger.info("Alpaca client connected: %s", self._base_url)
        except ImportError:
            logger.error(
                "alpaca-trade-api not installed. Run: pip install alpaca-trade-api"
            )
            raise
        except Exception as exc:
            logger.error("Failed to initialize Alpaca client: %s", exc)
            self._connected = False

    async def connect(
        self,
        api_key: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
    ) -> AlpacaAccountInfo:
        """
        Connect to the Alpaca API and verify credentials.

        Args:
            api_key: Override stored API key
            secret_key: Override stored secret key
            base_url: Override stored base URL

        Returns:
            AlpacaAccountInfo with account details

        Raises:
            ConnectionError: If connection fails after retries
        """
        self._api_key = api_key or self._api_key
        self._secret_key = secret_key or self._secret_key
        self._base_url = base_url or self._base_url

        if not self._api_key or not self._secret_key:
            raise ValueError("API key and secret key are required")

        self._init_client()
        account = await self._retry_call(self._get_account)
        return account

    # ══════════════════════════════════════════════════════════════════
    # ORDER SUBMISSION
    # ══════════════════════════════════════════════════════════════════

    async def buy(
        self,
        symbol: str,
        quantity: float,
        price: float | None = None,
        order_type: str = "market",
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> AlpacaOrderResult:
        """
        Submit a buy order.

        Args:
            symbol: Stock or crypto symbol (e.g. "AAPL", "BTC/USD")
            quantity: Number of shares/units
            price: Limit price (required for limit orders)
            order_type: "market", "limit", "stop", "stop_limit"
            time_in_force: "day", "gtc", "ioc", "fok"
            client_order_id: Optional custom order ID

        Returns:
            AlpacaOrderResult with submission details
        """
        return await self._submit_order(
            symbol=symbol,
            side="buy",
            quantity=quantity,
            price=price,
            order_type=order_type,
            time_in_force=time_in_force,
            client_order_id=client_order_id,
        )

    async def sell(
        self,
        symbol: str,
        quantity: float,
        price: float | None = None,
        order_type: str = "market",
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> AlpacaOrderResult:
        """
        Submit a sell order.

        Args:
            symbol: Stock or crypto symbol
            quantity: Number of shares/units
            price: Limit price (required for limit orders)
            order_type: Order type string
            time_in_force: Time in force
            client_order_id: Optional custom order ID

        Returns:
            AlpacaOrderResult with submission details
        """
        return await self._submit_order(
            symbol=symbol,
            side="sell",
            quantity=quantity,
            price=price,
            order_type=order_type,
            time_in_force=time_in_force,
            client_order_id=client_order_id,
        )

    async def _submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float | None = None,
        order_type: str = "market",
        time_in_force: str = "day",
        client_order_id: str | None = None,
    ) -> AlpacaOrderResult:
        """Internal order submission with retry logic."""
        self._ensure_connected()

        import uuid
        client_id = client_order_id or f"qna-{uuid.uuid4().hex[:8]}"

        kwargs: dict[str, Any] = {
            "symbol": symbol.upper(),
            "qty": str(quantity),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "client_order_id": client_id,
        }

        if order_type in ("limit", "stop_limit") and price is not None:
            kwargs["limit_price"] = str(price)
        if order_type in ("stop", "stop_limit") and price is not None:
            kwargs["stop_price"] = str(price)

        def _place():
            return self._client.submit_order(**kwargs)

        try:
            response = await self._retry_call(_place)
            result = self._parse_order_response(response)
            self._order_cache[result.order_id] = result
            logger.info("Order submitted: %s %s %.2f %s", side, symbol, quantity, order_type)
            return result
        except Exception as exc:
            logger.error("Order submission failed: %s %s - %s", side, symbol, exc)
            raise

    # ══════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT
    # ══════════════════════════════════════════════════════════════════

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an open order.

        Args:
            order_id: Alpaca order ID

        Returns:
            Dict with cancellation status
        """
        self._ensure_connected()

        def _cancel():
            self._client.cancel_order(order_id)
            return {"order_id": order_id, "status": "cancelled"}

        try:
            result = await self._retry_call(_cancel)
            logger.info("Order cancelled: %s", order_id)
            return result
        except Exception as exc:
            logger.error("Cancel failed for %s: %s", order_id, exc)
            return {"order_id": order_id, "status": "error", "error": str(exc)}

    async def get_order(self, order_id: str) -> AlpacaOrderResult | None:
        """Get order details by ID."""
        self._ensure_connected()

        def _get():
            return self._client.get_order(order_id)

        try:
            response = await self._retry_call(_get)
            return self._parse_order_response(response)
        except Exception as exc:
            logger.error("Get order failed for %s: %s", order_id, exc)
            return None

    # ══════════════════════════════════════════════════════════════════
    # POSITION & ACCOUNT QUERIES
    # ══════════════════════════════════════════════════════════════════

    async def get_positions(self) -> list[AlpacaPosition]:
        """
        Get all current positions.

        Returns:
            List of AlpacaPosition objects
        """
        self._ensure_connected()

        def _get():
            return self._client.list_positions()

        try:
            responses = await self._retry_call(_get)
            positions = []
            for r in responses:
                positions.append(AlpacaPosition(
                    symbol=r.symbol,
                    quantity=float(r.qty),
                    side=r.side,
                    avg_entry_price=float(r.avg_entry_price),
                    current_price=float(r.current_price),
                    market_value=float(r.market_value),
                    unrealized_pnl=float(r.unrealized_pl),
                    unrealized_pnl_pct=float(r.unrealized_plpc),
                ))
            return positions
        except Exception as exc:
            logger.error("Get positions failed: %s", exc)
            return []

    async def get_position(self, symbol: str) -> AlpacaPosition | None:
        """Get position for a specific symbol."""
        self._ensure_connected()

        def _get():
            return self._client.get_position(symbol.upper())

        try:
            r = await self._retry_call(_get)
            return AlpacaPosition(
                symbol=r.symbol,
                quantity=float(r.qty),
                side=r.side,
                avg_entry_price=float(r.avg_entry_price),
                current_price=float(r.current_price),
                market_value=float(r.market_value),
                unrealized_pnl=float(r.unrealized_pl),
                unrealized_pnl_pct=float(r.unrealized_plpc),
            )
        except Exception:
            return None

    async def get_balance(self) -> dict[str, float]:
        """
        Get account balance information.

        Returns:
            Dict with cash, equity, buying_power, etc.
        """
        account = await self._retry_call(self._get_account)
        return {
            "cash": account.cash,
            "equity": account.equity,
            "buying_power": account.buying_power,
            "long_market_value": account.long_market_value,
            "short_market_value": account.short_market_value,
            "portfolio_value": account.portfolio_value,
        }

    async def get_open_orders(self) -> list[AlpacaOrderResult]:
        """Get all open orders."""
        self._ensure_connected()

        def _get():
            return self._client.list_orders(status="open")

        try:
            responses = await self._retry_call(_get)
            return [self._parse_order_response(r) for r in responses]
        except Exception as exc:
            logger.error("Get open orders failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _get_account(self) -> AlpacaAccountInfo:
        """Fetch account info from Alpaca."""
        acct = self._client.get_account()
        return AlpacaAccountInfo(
            account_id=acct.id,
            cash=float(acct.cash),
            equity=float(acct.equity),
            buying_power=float(acct.buying_power),
            long_market_value=float(acct.long_market_value),
            short_market_value=float(acct.short_market_value),
            portfolio_value=float(acct.portfolio_value),
            status=acct.status,
            trading_blocked=acct.trading_blocked,
            transfers_blocked=acct.transfers_blocked,
        )

    def _parse_order_response(self, response: Any) -> AlpacaOrderResult:
        """Parse Alpaca API order response into our model."""
        return AlpacaOrderResult(
            order_id=response.id,
            client_order_id=getattr(response, "client_order_id", ""),
            symbol=response.symbol,
            side=response.side,
            quantity=float(response.qty or 0),
            order_type=response.type,
            status=response.status,
            limit_price=float(response.limit_price) if response.limit_price else None,
            filled_price=float(response.filled_avg_price) if response.filled_avg_price else None,
            filled_quantity=float(response.filled_qty or 0),
            created_at=datetime.now(),
            raw_response={
                "id": response.id,
                "status": response.status,
                "filled_qty": response.filled_qty,
                "filled_avg_price": response.filled_avg_price,
            },
        )

    def _ensure_connected(self) -> None:
        """Raise if not connected to Alpaca API."""
        if not self._connected or self._client is None:
            raise ConnectionError(
                "Not connected to Alpaca. Call connect() with API keys first."
            )

    async def _retry_call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with exponential backoff retry.

        Retries on rate limit (429) and server errors (5xx).
        """
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            await self._rate_limiter.acquire()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exc:
                last_exc = exc
                status_code = getattr(exc, "status_code", None)

                # Don't retry client errors (4xx) except 429
                if status_code and 400 <= status_code < 500 and status_code != 429:
                    raise

                if attempt < self._max_retries - 1:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning(
                        "API call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, self._max_retries, backoff, exc,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "API call failed after %d retries: %s",
                        self._max_retries, exc,
                    )

        raise last_exc  # type: ignore[misc]
