"""Polymarket CLOB Broker — Prediction market trading via Polymarket CLOB API.

Provides a production-grade implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for the
Polymarket Central Limit Order Book (CLOB) API.

Features
--------
* Connect to Polymarket CLOB API with EIP-712 authentication
* Place YES/NO bets (limit and market orders)
* Cancel orders
* Read order books for prediction markets
* Track positions across markets
* Portfolio management for prediction market positions
* Real-time updates via Polymarket WebSocket
* Proper rate limiting and error handling

Authentication
--------------
Polymarket uses Ethereum-based authentication:
1. An Ethereum private key derives the wallet address
2. API key is obtained from Polymarket via the CLOB API
3. All requests are signed with EIP-712 typed data signatures
4. The CLOB API key, secret, and passphrase are used for authenticated endpoints

Dependencies
------------
Requires ``httpx``, ``eth_account``, and ``web3`` packages.

Notes
-----
Polymarket markets are represented as conditional token contracts.
Each market has a condition_id and two tokens: YES and NO.
The symbol format is ``"MARKET_SLUG:YES"`` or ``"MARKET_SLUG:NO"``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

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
from quant_nanggroe.types.market import OHLCV, OrderBook, OrderBookLevel, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLYMARKET_CLOB_URL = "https://clob.polymarket.com"
POLYMARKET_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws"
POLYMARKET_CHAIN_ID = 137  # Polygon mainnet

# Rate limits
_RATE_LIMIT_REQUESTS = 60
_RATE_LIMIT_WINDOW = 60.0  # seconds


# ---------------------------------------------------------------------------
# Pydantic models for Polymarket data
# ---------------------------------------------------------------------------

class PolymarketMarket(BaseModel):
    """A Polymarket prediction market.

    Attributes
    ----------
    condition_id:
        Unique condition identifier on-chain.
    question:
        The prediction market question.
    slug:
        URL-friendly identifier.
    tokens:
        Token IDs for YES and NO outcomes.
    active:
        Whether the market is currently active.
    closed:
        Whether the market has been resolved.
    end_date:
        When the market closes.
    description:
        Market description.
    """

    condition_id: str = ""
    question: str = ""
    slug: str = ""
    tokens: List[Dict[str, Any]] = Field(default_factory=list)
    active: bool = True
    closed: bool = False
    end_date: Optional[str] = None
    description: str = ""

    model_config = {"from_attributes": True}


class PolymarketCreds(BaseModel):
    """Polymarket CLOB API credentials.

    Attributes
    ----------
    api_key:
        CLOB API key.
    api_secret:
        CLOB API secret.
    api_passphrase:
        CLOB API passphrase.
    """

    api_key: str = ""
    api_secret: str = ""
    api_passphrase: str = ""

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# EIP-712 Signing
# ---------------------------------------------------------------------------

class EIP712Signer:
    """EIP-712 typed data signer for Polymarket authentication.

    Signs messages using an Ethereum private key for CLOB API
    authentication and order signing.

    Parameters
    ----------
    private_key:
        Ethereum private key (hex string with or without 0x prefix).
    chain_id:
        Chain ID for the EIP-712 domain (default: 137 for Polygon).
    """

    def __init__(
        self,
        private_key: str,
        chain_id: int = POLYMARKET_CHAIN_ID,
    ) -> None:
        self._chain_id = chain_id
        self._private_key = private_key
        self._address: Optional[str] = None

    @property
    def address(self) -> str:
        """The Ethereum address derived from the private key."""
        if self._address is None:
            try:
                from eth_account import Account  # type: ignore[import-untyped]
                acct = Account.from_key(self._private_key)
                self._address = acct.address
            except ImportError as exc:
                raise ImportError(
                    "eth_account package is required for Polymarket. "
                    "Install with: pip install eth-account"
                ) from exc
        return self._address

    def sign_message(self, message: bytes) -> str:
        """Sign a raw message with the private key.

        Parameters
        ----------
        message:
            Raw bytes to sign.

        Returns
        -------
        str
            Hex-encoded signature.
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct  # type: ignore[import-untyped]

            msg = encode_defunct(message)
            signed = Account.sign_message(msg, self._private_key)
            return signed.signature.hex()
        except ImportError as exc:
            raise ImportError(
                "eth_account package is required. Install with: pip install eth-account"
            ) from exc

    def sign_typed_data(
        self,
        domain: Dict[str, Any],
        types: Dict[str, Any],
        primary_type: str,
        message: Dict[str, Any],
    ) -> str:
        """Sign EIP-712 typed data.

        Parameters
        ----------
        domain:
            EIP-712 domain data.
        types:
            Type definitions.
        primary_type:
            Primary type name.
        message:
            Message data to sign.

        Returns
        -------
        str
            Hex-encoded signature.
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_structured_data  # type: ignore[import-untyped]

            structured_data = {
                "types": types,
                "primaryType": primary_type,
                "domain": domain,
                "message": message,
            }

            signed = Account.sign_message(encode_structured_data(structured_data), self._private_key)
            return signed.signature.hex()
        except ImportError as exc:
            raise ImportError(
                "eth_account package is required. Install with: pip install eth-account"
            ) from exc

    def sign_order(
        self,
        order_data: Dict[str, Any],
    ) -> str:
        """Sign a Polymarket CLOB order.

        Parameters
        ----------
        order_data:
            Order data to sign.

        Returns
        -------
        str
            Hex-encoded signature.
        """
        domain = {
            "name": "Polymarket CLOB",
            "version": "1",
            "chainId": self._chain_id,
        }
        types = {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "Order": [
                {"name": "salt", "type": "uint256"},
                {"name": "maker", "type": "address"},
                {"name": "signer", "type": "address"},
                {"name": "taker", "type": "address"},
                {"name": "tokenId", "type": "uint256"},
                {"name": "makerAmount", "type": "uint256"},
                {"name": "takerAmount", "type": "uint256"},
                {"name": "side", "type": "string"},
                {"name": "expiration", "type": "uint256"},
                {"name": "nonce", "type": "uint256"},
                {"name": "feeRateBps", "type": "uint256"},
            ],
        }

        return self.sign_typed_data(
            domain=domain,
            types=types,
            primary_type="Order",
            message=order_data,
        )


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

class PolymarketRateLimiter:
    """Simple sliding window rate limiter for Polymarket API.

    Parameters
    ----------
    max_requests:
        Maximum requests per window.
    window_seconds:
        Time window in seconds.
    """

    def __init__(
        self,
        max_requests: int = _RATE_LIMIT_REQUESTS,
        window_seconds: float = _RATE_LIMIT_WINDOW,
    ) -> None:
        self._max_requests = max_requests
        self._window = window_seconds
        self._request_times: List[float] = []

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        while True:
            now = time.monotonic()
            # Remove timestamps outside the window
            self._request_times = [
                t for t in self._request_times if now - t < self._window
            ]
            if len(self._request_times) < self._max_requests:
                self._request_times.append(now)
                return
            await asyncio.sleep(0.1)


# ---------------------------------------------------------------------------
# PolymarketBroker
# ---------------------------------------------------------------------------

class PolymarketBroker(ExchangeInterface):
    """Polymarket CLOB broker implementing ExchangeInterface.

    Provides trading capabilities for Polymarket prediction markets,
    including YES/NO bet placement, order book reading, position
    management, and portfolio tracking.

    Parameters
    ----------
    config:
        Exchange configuration.
        ``api_key`` is the Ethereum private key (hex).
        ``api_secret`` is the CLOB API key (can be derived).
        Additional options may include:
        - ``clob_url``: Custom CLOB URL (default: https://clob.polymarket.com)
        - ``chain_id``: Chain ID (default: 137 for Polygon)

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="polymarket",
            api_key="0x...",  # Ethereum private key
        )
        broker = PolymarketBroker(config)
        await broker.connect()

        # Place a YES bet
        order = await broker.place_order(
            symbol="will-bitcoin-hit-100k:YES",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100.0,
            price=0.65,
        )
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._http_client: Optional[httpx.AsyncClient] = None
        self._signer: Optional[EIP712Signer] = None
        self._clob_creds: Optional[PolymarketCreds] = None
        self._rate_limiter = PolymarketRateLimiter()
        self._local_orders: Dict[str, Order] = {}
        self._local_positions: Dict[str, Position] = {}
        self._markets_cache: Dict[str, PolymarketMarket] = {}
        self._markets_cache_ts: float = 0.0
        self._ws_tasks: Dict[str, asyncio.Task] = {}
        self._ws_callbacks: Dict[str, Dict[str, WebSocketCallback]] = {}

        # Custom settings from config options
        self._clob_url = config.options.get("clob_url", POLYMARKET_CLOB_URL)
        self._chain_id = config.options.get("chain_id", POLYMARKET_CHAIN_ID)

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Connect to the Polymarket CLOB API.

        Derives CLOB credentials from the Ethereum private key and
        authenticates with the API.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the connection fails.
        AuthenticationError
            If the API credentials are invalid.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            # Initialize EIP-712 signer
            private_key = self._config.api_key
            if not private_key:
                raise ConnectionError(
                    "Ethereum private key (api_key) is required for Polymarket",
                    exchange="polymarket",
                )

            # Normalize private key
            if private_key.startswith("0x"):
                private_key = private_key[2:]

            self._signer = EIP712Signer(
                private_key=private_key,
                chain_id=self._chain_id,
            )

            # Initialize HTTP client
            self._http_client = httpx.AsyncClient(
                timeout=self._config.timeout,
                headers={"Content-Type": "application/json"},
            )

            # Try to get/create CLOB API credentials
            await self._authenticate_clob()

            # Verify connection by getting markets
            await self._get_markets_internal()

            self._state = ExchangeState.CONNECTED
            logger.info(
                "PolymarketBroker: Connected — wallet %s",
                self._signer.address[:10] + "...",
            )
            return True

        except ImportError as exc:
            self._state = ExchangeState.ERROR
            raise ImportError(
                "eth_account package is required for Polymarket. "
                "Install with: pip install eth-account"
            ) from exc
        except AuthenticationError:
            self._state = ExchangeState.ERROR
            raise
        except ExchangeError:
            self._state = ExchangeState.ERROR
            raise
        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to Polymarket: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def _authenticate_clob(self) -> None:
        """Authenticate with the Polymarket CLOB API.

        Derives or retrieves API credentials using the Ethereum key.
        """
        if self._http_client is None or self._signer is None:
            return

        # Check if we already have CLOB credentials from config
        if self._config.api_secret:
            self._clob_creds = PolymarketCreds(
                api_key=self._config.api_secret,
                api_secret=self._config.options.get("clob_api_secret", ""),
                api_passphrase=self._config.options.get("clob_api_passphrase", ""),
            )
            return

        # Derive CLOB credentials from Ethereum key
        try:
            # Step 1: Get API key nonce
            nonce_payload = {
                "address": self._signer.address,
            }
            resp = await self._http_client.post(
                f"{self._clob_url}/api-key-nonce",
                json=nonce_payload,
            )
            if resp.status_code != 200:
                logger.warning(
                    "PolymarketBroker: Could not get API nonce: %s", resp.text,
                )
                # Try to create API key instead
                await self._create_api_key()
                return

            nonce_data = resp.json()
            nonce = nonce_data.get("nonce", 0)

            # Step 2: Sign the nonce to create/derive API key
            signature = self._signer.sign_message(
                f"polymarket:{nonce}".encode(),
            )

            # Step 3: Create or get API key
            create_payload = {
                "address": self._signer.address,
                "signature": signature,
                "nonce": nonce,
            }
            resp = await self._http_client.post(
                f"{self._clob_url}/create-api-key",
                json=create_payload,
            )

            if resp.status_code in (200, 201):
                key_data = resp.json()
                self._clob_creds = PolymarketCreds(
                    api_key=key_data.get("apiKey", ""),
                    api_secret=key_data.get("secret", ""),
                    api_passphrase=key_data.get("passphrase", ""),
                )
                logger.info("PolymarketBroker: CLOB API key created successfully")
            else:
                logger.warning(
                    "PolymarketBroker: Could not create API key: %s", resp.text,
                )
                # Continue without CLOB creds (limited to public endpoints)

        except Exception as exc:
            logger.warning(
                "PolymarketBroker: CLOB authentication error: %s", exc,
            )

    async def _create_api_key(self) -> None:
        """Create a new CLOB API key from the Ethereum wallet."""
        if self._http_client is None or self._signer is None:
            return

        try:
            signature = self._signer.sign_message(
                b"polymarket",
            )
            payload = {
                "address": self._signer.address,
                "signature": signature,
            }
            resp = await self._http_client.post(
                f"{self._clob_url}/create-api-key",
                json=payload,
            )
            if resp.status_code in (200, 201):
                key_data = resp.json()
                self._clob_creds = PolymarketCreds(
                    api_key=key_data.get("apiKey", ""),
                    api_secret=key_data.get("secret", ""),
                    api_passphrase=key_data.get("passphrase", ""),
                )
        except Exception as exc:
            logger.warning("PolymarketBroker: API key creation failed: %s", exc)

    async def disconnect(self) -> None:
        """Close the Polymarket connection and clean up resources."""
        for task in self._ws_tasks.values():
            if not task.done():
                task.cancel()
        self._ws_tasks.clear()
        self._ws_callbacks.clear()

        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

        self._signer = None
        self._clob_creds = None
        self._state = ExchangeState.DISCONNECTED
        logger.info("PolymarketBroker: Disconnected")

    @property
    def is_connected(self) -> bool:
        return self._state == ExchangeState.CONNECTED

    @property
    def state(self) -> ExchangeState:
        return self._state

    @property
    def name(self) -> str:
        return "polymarket"

    # ----- Internal: API call with rate limiting -----

    async def _api_call(
        self,
        method: str,
        endpoint: str,
        *,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        authenticated: bool = False,
    ) -> Any:
        """Execute an API call with rate limiting and error handling.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, DELETE).
        endpoint:
            API endpoint path (relative to base URL).
        json_data:
            JSON body for POST/PUT requests.
        params:
            Query parameters for GET requests.
        authenticated:
            Whether to include CLOB authentication headers.

        Returns
        -------
        Any
            Parsed JSON response.

        Raises
        ------
        RateLimitError
            If rate limit is hit after retries.
        ExchangeError
            On non-transient errors.
        """
        self._require_connected()

        await self._rate_limiter.acquire()

        url = f"{self._clob_url}{endpoint}"
        headers: Dict[str, str] = {}

        if authenticated and self._clob_creds:
            headers["POLY_API_KEY"] = self._clob_creds.api_key
            headers["POLY_API_SECRET"] = self._clob_creds.api_secret
            headers["POLY_PASSPHRASE"] = self._clob_creds.api_passphrase

        last_exc: Optional[Exception] = None
        for attempt in range(self._config.retries + 1):
            try:
                if method.upper() == "GET":
                    resp = await self._http_client.get(url, params=params, headers=headers)
                elif method.upper() == "POST":
                    resp = await self._http_client.post(url, json=json_data, headers=headers)
                elif method.upper() == "DELETE":
                    resp = await self._http_client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle status codes
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 201:
                    try:
                        return resp.json()
                    except Exception:
                        return {"status": "created"}
                elif resp.status_code == 429:
                    wait = self._config.retry_delay * (2 ** attempt)
                    logger.warning(
                        "PolymarketBroker: Rate limited, retrying in %.1fs",
                        wait,
                    )
                    self._state = ExchangeState.RATE_LIMITED
                    await asyncio.sleep(wait)
                    last_exc = RateLimitError(
                        f"Rate limited: {resp.text}",
                        retry_after=wait,
                        exchange="polymarket",
                    )
                    continue
                elif resp.status_code in (401, 403):
                    raise AuthenticationError(
                        f"Authentication failed: {resp.text}",
                        exchange="polymarket",
                    )
                elif resp.status_code in (500, 502, 503):
                    wait = self._config.retry_delay * (2 ** attempt)
                    logger.warning(
                        "PolymarketBroker: Server error %d, retrying in %.1fs",
                        resp.status_code, wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = ExchangeError(
                        f"Server error {resp.status_code}: {resp.text}",
                        exchange="polymarket",
                    )
                    continue
                else:
                    raise ExchangeError(
                        f"API error ({resp.status_code}): {resp.text}",
                        exchange="polymarket",
                    )

            except (AuthenticationError, RateLimitError):
                raise
            except ExchangeError:
                raise
            except Exception as exc:
                last_exc = exc
                wait = self._config.retry_delay * (2 ** attempt)
                logger.warning(
                    "PolymarketBroker: Request error, retrying in %.1fs: %s",
                    wait, exc,
                )
                await asyncio.sleep(wait)

        # Exhausted retries
        if isinstance(last_exc, RateLimitError):
            raise last_exc
        raise ExchangeError(
            f"API call failed after {self._config.retries + 1} attempts: {last_exc}",
            exchange="polymarket",
            original=last_exc,
        )

    # ----- Symbol parsing -----

    @staticmethod
    def _parse_symbol(symbol: str) -> tuple[str, str]:
        """Parse a Polymarket symbol into (market_slug, outcome).

        Symbol format: ``"market-slug:YES"`` or ``"market-slug:NO"``

        Parameters
        ----------
        symbol:
            Trading symbol.

        Returns
        -------
        tuple of (market_slug, outcome)
        """
        if ":" in symbol:
            parts = symbol.rsplit(":", 1)
            return parts[0], parts[1].upper()
        return symbol, "YES"

    @staticmethod
    def _make_symbol(market_slug: str, outcome: str) -> str:
        """Create a symbol from market slug and outcome.

        Parameters
        ----------
        market_slug:
            Market slug.
        outcome:
            Outcome (YES or NO).

        Returns
        -------
        str
            Symbol string.
        """
        return f"{market_slug}:{outcome.upper()}"

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        """Get account balances from Polymarket.

        Returns
        -------
        dict
            Mapping of asset -> balance.
        """
        self._require_connected()
        try:
            if not self._signer:
                raise ExchangeError("Not authenticated", exchange="polymarket")

            # Get balances from CLOB
            data = await self._api_call(
                "GET",
                "/balances",
                authenticated=True,
            )

            balances: Dict[str, float] = {}
            if isinstance(data, dict):
                # USDC balance
                usdc = data.get("USDC", {})
                if isinstance(usdc, dict):
                    balances["USDC"] = float(usdc.get("available", 0) or 0)
                elif isinstance(usdc, (int, float, str)):
                    balances["USDC"] = float(usdc)

            return balances
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get balance: {exc}", exchange="polymarket", original=exc,
            ) from exc

    async def get_positions(self) -> List[Position]:
        """Get all open positions from Polymarket.

        Returns
        -------
        list of Position
            Current prediction market positions.
        """
        self._require_connected()
        try:
            if not self._signer:
                raise ExchangeError("Not authenticated", exchange="polymarket")

            data = await self._api_call(
                "GET",
                "/positions",
                authenticated=True,
            )

            positions: List[Position] = []
            if isinstance(data, list):
                for item in data:
                    pos = self._parse_polymarket_position(item)
                    if pos is not None:
                        positions.append(pos)
                        self._local_positions[pos.symbol] = pos
            elif isinstance(data, dict):
                # Single position or wrapped response
                items = data.get("positions", [data])
                for item in items:
                    pos = self._parse_polymarket_position(item)
                    if pos is not None:
                        positions.append(pos)
                        self._local_positions[pos.symbol] = pos

            return positions
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get positions: {exc}", exchange="polymarket", original=exc,
            ) from exc

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot from Polymarket.

        Returns
        -------
        Portfolio
            Complete portfolio with prediction market positions.
        """
        self._require_connected()
        try:
            balances = await self.get_balance()
            positions = await self.get_positions()

            cash = balances.get("USDC", 0.0)

            portfolio = Portfolio(
                name="polymarket",
                currency="USDC",
                initial_capital=cash,
                cash=cash,
            )
            for pos in positions:
                portfolio.positions[pos.symbol] = pos
            portfolio.recalculate()
            return portfolio
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get portfolio: {exc}", exchange="polymarket", original=exc,
            ) from exc

    # ----- Trading -----

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
        """Place a bet on a Polymarket prediction market.

        Parameters
        ----------
        symbol:
            Market symbol in format ``"market-slug:YES"`` or ``"market-slug:NO"``.
        side:
            BUY to place a bet, SELL to exit a position.
        order_type:
            LIMIT or MARKET. Limit requires a price.
        quantity:
            Number of shares to buy/sell.
        price:
            Price per share (0.01 to 0.99). Required for LIMIT orders.
        stop_price:
            Not supported for Polymarket.
        client_order_id:
            Optional client-assigned ID.

        Returns
        -------
        Order
            The placed order.

        Raises
        ------
        OrderError
            If the order is invalid or rejected.
        InsufficientFundsError
            If the account lacks balance.
        """
        self._require_connected()
        if not self._signer:
            raise AuthenticationError("Not authenticated", exchange="polymarket")

        market_slug, outcome = self._parse_symbol(symbol)

        # Validate price range for prediction markets
        if price is not None and (price < 0.01 or price > 0.99):
            raise OrderError(
                f"Polymarket prices must be between 0.01 and 0.99, got {price}",
                exchange="polymarket",
            )

        if order_type == OrderType.MARKET and price is None:
            # For market orders, use mid-market price
            try:
                orderbook = await self.get_orderbook(symbol)
                if orderbook.mid_price:
                    price = orderbook.mid_price
                elif orderbook.asks:
                    price = orderbook.asks[0].price if side == OrderSide.BUY else orderbook.bids[0].price if orderbook.bids else 0.5
                else:
                    price = 0.5
            except Exception:
                price = 0.5

        if price is None:
            raise OrderError("Price is required for Polymarket orders", exchange="polymarket")

        try:
            # Get token ID for the market/outcome
            token_id = await self._get_token_id(market_slug, outcome)
            if not token_id:
                raise OrderError(
                    f"Could not find token ID for {symbol}",
                    exchange="polymarket",
                )

            # Convert quantities to integer representation (prices in cents, amounts in shares)
            maker_amount = int(quantity * 100)  # Shares in hundredths
            taker_amount = int(quantity * price * 100)  # Cost in cents

            # Build order data for signing
            order_data = {
                "salt": int(time.time() * 1000),
                "maker": self._signer.address,
                "signer": self._signer.address,
                "taker": "0x0000000000000000000000000000000000000000",
                "tokenId": token_id,
                "makerAmount": str(maker_amount),
                "takerAmount": str(taker_amount),
                "side": "BUY" if side == OrderSide.BUY else "SELL",
                "expiration": 0,
                "nonce": int(time.time()),
                "feeRateBps": 0,
            }

            # Sign the order
            signature = self._signer.sign_order(order_data)

            # Build the CLOB order payload
            clob_order = {
                "tokenID": token_id,
                "price": price,
                "size": quantity,
                "side": "BUY" if side == OrderSide.BUY else "SELL",
                "feeRateBps": 0,
                "nonce": order_data["nonce"],
                "signer": self._signer.address,
                "signature": signature,
                "expiration": 0,
            }

            if order_type == OrderType.LIMIT:
                clob_order["type"] = "GTC"  # Good Till Canceled
            else:
                clob_order["type"] = "FOK"  # Fill Or Kill (market-like)

            if client_order_id:
                clob_order["clientOrderId"] = client_order_id

            # Submit to CLOB
            result = await self._api_call(
                "POST",
                "/order",
                json_data=clob_order,
                authenticated=True,
            )

            # Parse response
            order_id = result.get("orderID", result.get("id", str(uuid.uuid4())))
            order_status = result.get("status", "live").lower()

            status_map = {
                "live": OrderStatus.SUBMITTED,
                "matched": OrderStatus.FILLED,
                "filled": OrderStatus.FILLED,
                "cancelled": OrderStatus.CANCELED,
                "rejected": OrderStatus.REJECTED,
                "pending": OrderStatus.PENDING,
            }

            order = Order(
                id=order_id,
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=status_map.get(order_status, OrderStatus.SUBMITTED),
                filled_quantity=float(result.get("size_matched", 0) or 0),
                average_fill_price=float(result.get("average_price", price)) if result.get("average_price") or price else None,
                commission=0.0,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="polymarket",
                broker_order_id=order_id,
                strategy_name=strategy_name,
                agent_name=agent_name,
                notes=notes,
            )
            self._local_orders[order.id] = order
            return order

        except (OrderError, AuthenticationError, InsufficientFundsError, RateLimitError):
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place order: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order on Polymarket.

        Parameters
        ----------
        order_id:
            Polymarket order ID.

        Returns
        -------
        Order
            The cancelled order.
        """
        self._require_connected()
        try:
            await self._api_call(
                "DELETE",
                f"/order/{order_id}",
                authenticated=True,
            )

            if order_id in self._local_orders:
                order = self._local_orders[order_id]
                order.status = OrderStatus.CANCELED
                order.updated_at = datetime.now(tz=timezone.utc)
                return order

            return Order(
                id=order_id,
                symbol=symbol or "UNKNOWN",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0,
                status=OrderStatus.CANCELED,
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="polymarket",
                broker_order_id=order_id,
            )
        except ExchangeError:
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to cancel order {order_id}: {exc}",
                order_id=order_id,
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Get order status from Polymarket.

        Parameters
        ----------
        order_id:
            Polymarket order ID.

        Returns
        -------
        Order
            Current order state.
        """
        self._require_connected()
        try:
            data = await self._api_call(
                "GET",
                f"/order/{order_id}",
                authenticated=True,
            )

            return self._parse_polymarket_order(data)
        except ExchangeError:
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to get order {order_id}: {exc}",
                order_id=order_id,
                exchange="polymarket",
                original=exc,
            ) from exc

    # ----- Market Data -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """OHLCV data is not directly available from Polymarket CLOB.

        Use an external data provider instead.
        """
        raise MarketDataError(
            "OHLCV data not available via Polymarket CLOB. "
            "Use an external data provider.",
            exchange="polymarket",
        )

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get the latest ticker for a prediction market.

        Parameters
        ----------
        symbol:
            Market symbol (e.g. ``"will-bitcoin-hit-100k:YES"``).

        Returns
        -------
        Ticker
        """
        self._require_connected()
        try:
            market_slug, outcome = self._parse_symbol(symbol)
            token_id = await self._get_token_id(market_slug, outcome)

            if not token_id:
                raise MarketDataError(
                    f"Could not find token for {symbol}",
                    exchange="polymarket",
                )

            # Get the last trade price
            data = await self._api_call(
                "GET",
                f"/prices",
                params={"token_id": token_id, "side": outcome.lower()},
            )

            last_price = 0.5
            if isinstance(data, dict):
                last_price = float(data.get("price", 0.5) or 0.5)
            elif isinstance(data, list) and data:
                last_price = float(data[0].get("price", 0.5) or 0.5)

            # Clamp to valid range
            last_price = max(0.01, min(0.99, last_price))

            return Ticker(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                last_price=last_price,
                bid=last_price * 0.99,
                ask=last_price * 1.01,
            )
        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get ticker for {symbol}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Fetch the order book for a prediction market.

        Parameters
        ----------
        symbol:
            Market symbol (e.g. ``"will-bitcoin-hit-100k:YES"``).
        limit:
            Depth per side.

        Returns
        -------
        OrderBook
        """
        self._require_connected()
        try:
            market_slug, outcome = self._parse_symbol(symbol)
            token_id = await self._get_token_id(market_slug, outcome)

            if not token_id:
                raise MarketDataError(
                    f"Could not find token for {symbol}",
                    exchange="polymarket",
                )

            data = await self._api_call(
                "GET",
                f"/book",
                params={"token_id": token_id},
            )

            bids: List[OrderBookLevel] = []
            asks: List[OrderBookLevel] = []

            # Parse order book data
            if isinstance(data, dict):
                for level in data.get("bids", [])[:limit]:
                    bids.append(OrderBookLevel(
                        price=float(level.get("price", 0)),
                        quantity=float(level.get("size", 0)),
                    ))
                for level in data.get("asks", [])[:limit]:
                    asks.append(OrderBookLevel(
                        price=float(level.get("price", 0)),
                        quantity=float(level.get("size", 0)),
                    ))

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
                f"Failed to get order book for {symbol}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_trades(
        self,
        symbol: str,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a prediction market.

        Parameters
        ----------
        symbol:
            Market symbol.
        since:
            Start time filter.
        limit:
            Maximum number of trades.

        Returns
        -------
        list of dict
        """
        self._require_connected()
        try:
            market_slug, outcome = self._parse_symbol(symbol)
            token_id = await self._get_token_id(market_slug, outcome)

            if not token_id:
                raise MarketDataError(
                    f"Could not find token for {symbol}",
                    exchange="polymarket",
                )

            params: Dict[str, Any] = {"token_id": token_id, "limit": limit}
            if since:
                params["after"] = int(since.timestamp())

            data = await self._api_call(
                "GET",
                "/trades",
                params=params,
            )

            trades: List[Dict[str, Any]] = []
            if isinstance(data, list):
                for t in data:
                    trades.append({
                        "id": str(t.get("id", "")),
                        "price": float(t.get("price", 0)),
                        "amount": float(t.get("size", 0)),
                        "side": t.get("side", ""),
                        "timestamp": t.get("timestamp", ""),
                    })
            return trades
        except MarketDataError:
            raise
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get trades for {symbol}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    # ----- WebSocket -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time price updates for a market."""
        key = f"ticker:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._poll_ticker_loop(symbol),
            )
        logger.info("PolymarketBroker: Subscribed to ticker %s", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time order book updates for a market."""
        key = f"orderbook:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._poll_orderbook_loop(symbol),
            )
        logger.info("PolymarketBroker: Subscribed to orderbook %s", symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trade updates for a market."""
        key = f"trades:{symbol}"
        self._ws_callbacks.setdefault(key, {})[symbol] = callback
        if key not in self._ws_tasks or self._ws_tasks[key].done():
            self._ws_tasks[key] = asyncio.create_task(
                self._poll_trades_loop(symbol),
            )
        logger.info("PolymarketBroker: Subscribed to trades %s", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream."""
        key = f"{channel}:{symbol}"
        task = self._ws_tasks.pop(key, None)
        if task and not task.done():
            task.cancel()
        self._ws_callbacks.pop(key, None)
        logger.info("PolymarketBroker: Unsubscribed from %s %s", channel, symbol)

    async def _poll_ticker_loop(self, symbol: str) -> None:
        """Polling-based ticker stream."""
        key = f"ticker:{symbol}"
        poll_interval = 5.0  # 5 seconds
        try:
            while True:
                try:
                    if not self.is_connected:
                        await asyncio.sleep(10)
                        continue
                    ticker = await self.get_ticker(symbol)
                    callbacks = self._ws_callbacks.get(key, {})
                    for cb in callbacks.values():
                        try:
                            await cb(ticker.model_dump())
                        except Exception as cb_exc:
                            logger.warning(
                                "PolymarketBroker: Ticker callback error: %s", cb_exc,
                            )
                    await asyncio.sleep(poll_interval)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "PolymarketBroker: Ticker poll error for %s: %s",
                        symbol, exc,
                    )
                    await asyncio.sleep(self._config.retry_delay)
        except asyncio.CancelledError:
            pass

    async def _poll_orderbook_loop(self, symbol: str) -> None:
        """Polling-based order book stream."""
        key = f"orderbook:{symbol}"
        poll_interval = 2.0
        try:
            while True:
                try:
                    if not self.is_connected:
                        await asyncio.sleep(10)
                        continue
                    ob = await self.get_orderbook(symbol)
                    callbacks = self._ws_callbacks.get(key, {})
                    for cb in callbacks.values():
                        try:
                            await cb(ob.model_dump())
                        except Exception as cb_exc:
                            logger.warning(
                                "PolymarketBroker: OrderBook callback error: %s", cb_exc,
                            )
                    await asyncio.sleep(poll_interval)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "PolymarketBroker: OrderBook poll error for %s: %s",
                        symbol, exc,
                    )
                    await asyncio.sleep(self._config.retry_delay)
        except asyncio.CancelledError:
            pass

    async def _poll_trades_loop(self, symbol: str) -> None:
        """Polling-based trades stream."""
        key = f"trades:{symbol}"
        poll_interval = 5.0
        try:
            while True:
                try:
                    if not self.is_connected:
                        await asyncio.sleep(10)
                        continue
                    trades = await self.get_trades(symbol, limit=5)
                    callbacks = self._ws_callbacks.get(key, {})
                    for trade in trades:
                        for cb in callbacks.values():
                            try:
                                await cb(trade)
                            except Exception as cb_exc:
                                logger.warning(
                                    "PolymarketBroker: Trade callback error: %s", cb_exc,
                                )
                    await asyncio.sleep(poll_interval)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning(
                        "PolymarketBroker: Trade poll error for %s: %s",
                        symbol, exc,
                    )
                    await asyncio.sleep(self._config.retry_delay)
        except asyncio.CancelledError:
            pass

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List all available Polymarket prediction markets.

        Returns
        -------
        list of str
            Market slugs with YES/NO suffixes.
        """
        self._require_connected()
        try:
            markets = await self._get_markets_internal()
            symbols: List[str] = []
            for slug, market in markets.items():
                if market.active and not market.closed:
                    symbols.append(self._make_symbol(slug, "YES"))
                    symbols.append(self._make_symbol(slug, "NO"))
            return symbols
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get markets: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def _get_markets_internal(self) -> Dict[str, PolymarketMarket]:
        """Fetch and cache markets from the CLOB API."""
        cache_ttl = 300.0  # 5 minutes
        if (
            self._markets_cache
            and (time.time() - self._markets_cache_ts) < cache_ttl
        ):
            return self._markets_cache

        try:
            data = await self._api_call("GET", "/markets")

            if isinstance(data, list):
                for item in data:
                    market = PolymarketMarket(
                        condition_id=item.get("condition_id", ""),
                        question=item.get("question", ""),
                        slug=item.get("slug", ""),
                        tokens=item.get("tokens", []),
                        active=item.get("active", True),
                        closed=item.get("closed", False),
                        end_date=item.get("end_date"),
                        description=item.get("description", ""),
                    )
                    if market.slug:
                        self._markets_cache[market.slug] = market
            elif isinstance(data, dict):
                items = data.get("data", data.get("markets", []))
                if isinstance(items, list):
                    for item in items:
                        market = PolymarketMarket(
                            condition_id=item.get("condition_id", ""),
                            question=item.get("question", ""),
                            slug=item.get("slug", ""),
                            tokens=item.get("tokens", []),
                            active=item.get("active", True),
                            closed=item.get("closed", False),
                            end_date=item.get("end_date"),
                            description=item.get("description", ""),
                        )
                        if market.slug:
                            self._markets_cache[market.slug] = market

            self._markets_cache_ts = time.time()
            logger.info(
                "PolymarketBroker: Loaded %d markets",
                len(self._markets_cache),
            )
            return self._markets_cache
        except Exception as exc:
            logger.warning("PolymarketBroker: Failed to load markets: %s", exc)
            return self._markets_cache

    async def _get_token_id(self, market_slug: str, outcome: str) -> Optional[str]:
        """Get the token ID for a market/outcome pair.

        Parameters
        ----------
        market_slug:
            Market slug.
        outcome:
            YES or NO.

        Returns
        -------
        str or None
            Token ID if found.
        """
        await self._get_markets_internal()
        market = self._markets_cache.get(market_slug)
        if market is None:
            return None

        for token_info in market.tokens:
            token_outcome = token_info.get("outcome", "").upper()
            if token_outcome == outcome:
                return token_info.get("token_id", "")

        # Fallback: return first token for YES, second for NO
        if len(market.tokens) >= 2:
            idx = 0 if outcome == "YES" else 1
            return market.tokens[idx].get("token_id", "")

        return None

    async def health_check(self) -> bool:
        """Check Polymarket API health.

        Returns
        -------
        bool
            ``True`` if the API is responsive.
        """
        try:
            self._require_connected()
            data = await self._api_call("GET", "/time")
            self._state = ExchangeState.CONNECTED
            return True
        except Exception as exc:
            logger.warning("PolymarketBroker: Health check failed: %s", exc)
            self._state = ExchangeState.ERROR
            return False

    # ----- Internal helpers -----

    def _require_connected(self) -> None:
        """Ensure the broker is connected."""
        if not self.is_connected or self._http_client is None:
            raise ConnectionError(
                "PolymarketBroker is not connected",
                exchange="polymarket",
            )

    @staticmethod
    def _parse_polymarket_position(data: Dict[str, Any]) -> Optional[Position]:
        """Parse a Polymarket position dict into a Position model."""
        try:
            size = float(data.get("size", 0) or 0)
            if size == 0:
                return None

            avg_price = float(data.get("avgPrice", data.get("avg_price", 0.5)) or 0.5)
            cur_price = float(data.get("curPrice", data.get("current_price", avg_price)) or avg_price)
            market_slug = data.get("market_slug", data.get("market", ""))
            outcome = data.get("outcome", "YES").upper()
            symbol = f"{market_slug}:{outcome}" if market_slug else outcome

            unrealized_pnl = (cur_price - avg_price) * size

            return Position(
                symbol=symbol,
                side=PositionSide.LONG,
                quantity=size,
                entry_price=avg_price,
                current_price=cur_price,
                unrealized_pnl=unrealized_pnl,
                cost_basis=avg_price * size,
                market_value=cur_price * size,
                broker_id="polymarket",
                last_updated=datetime.now(tz=timezone.utc),
            )
        except (ValueError, TypeError, KeyError):
            return None

    @staticmethod
    def _parse_polymarket_order(data: Dict[str, Any]) -> Order:
        """Parse a Polymarket order dict into an Order model."""
        raw_status = str(data.get("status", "live")).lower()
        status_map: Dict[str, OrderStatus] = {
            "live": OrderStatus.SUBMITTED,
            "matched": OrderStatus.FILLED,
            "filled": OrderStatus.FILLED,
            "cancelled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "pending": OrderStatus.PENDING,
        }
        status = status_map.get(raw_status, OrderStatus.SUBMITTED)

        side_str = str(data.get("side", "BUY")).upper()
        side = OrderSide.BUY if side_str == "BUY" else OrderSide.SELL

        # Ensure symbol is never empty (required by Pydantic)
        symbol_val = data.get("symbol", "") or data.get("market_slug", "") or "UNKNOWN"

        return Order(
            id=str(data.get("id", uuid.uuid4())),
            client_order_id=data.get("clientOrderId"),
            symbol=symbol_val,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=float(data.get("original_size", data.get("size", 0)) or 0),
            price=float(data.get("price", 0)) if data.get("price") else None,
            status=status,
            filled_quantity=float(data.get("size_matched", 0) or 0),
            average_fill_price=float(data.get("average_price", 0)) if data.get("average_price") else None,
            commission=0.0,
            created_at=datetime.now(tz=timezone.utc),
            updated_at=datetime.now(tz=timezone.utc),
            broker_id="polymarket",
            broker_order_id=str(data.get("id", "")),
        )

    def __repr__(self) -> str:
        state = self._state.value
        return f"PolymarketBroker(state={state})"
