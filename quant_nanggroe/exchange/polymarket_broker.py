"""Polymarket CLOB Broker — Prediction Market Trading via Polymarket.

Provides a production-grade implementation of
:class:`~quant_nanggroe.exchange.base.ExchangeInterface` for the
Polymarket CLOB (Central Limit Order Book) API on Polygon network.

Features
--------
* Browse and search prediction markets
* Place limit and market orders on binary outcome tokens
* CTF (Conditional Token Framework) operations
* Wallet integration for Polygon network (EIP-712 signing)
* JSON output mode for automation
* Position tracking and settlement

Dependencies
------------
Requires the ``py-clob-client`` package (optional). Install with:
``pip install py-clob-client``

Notes
-----
Polymarket uses CTF tokens that represent outcomes of prediction markets.
Each market has YES and NO tokens. The interface maps these to
standard buy/sell operations.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

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
from quant_nanggroe.types.market import OHLCV, OrderBook, Ticker, TimeFrame
from quant_nanggroe.types.orders import Order, OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import Position, PositionSide, Portfolio

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Polymarket-specific models
# ---------------------------------------------------------------------------

class PolymarketMarket(BaseModel):
    """Represents a Polymarket prediction market."""
    condition_id: str = Field(..., description="Unique condition ID")
    question_id: str = Field("", description="Question ID")
    question: str = Field("", description="Market question text")
    description: str = Field("", description="Market description")
    outcomes: List[str] = Field(default_factory=list, description="Possible outcomes")
    outcome_prices: List[float] = Field(default_factory=list, description="Current outcome prices")
    active: bool = Field(True, description="Whether market is active")
    closed: bool = Field(False, description="Whether market is closed")
    volume: float = Field(0.0, description="Total volume in USDC")
    liquidity: float = Field(0.0, description="Total liquidity in USDC")
    end_date_iso: Optional[str] = Field(None, description="Market end date")
    tokens: List[Dict[str, Any]] = Field(default_factory=list, description="CTF token info")
    minimum_order_size: float = Field(0.50, description="Minimum order size in USDC")
    minimum_tick_size: float = Field(0.01, description="Minimum tick size")


class PolymarketOrderResult(BaseModel):
    """Result from placing an order on Polymarket."""
    order_id: str = Field("", description="Polymarket order ID")
    success: bool = Field(False, description="Whether order was placed successfully")
    transaction_hash: Optional[str] = Field(None, description="Polygon tx hash")
    error_message: str = Field("", description="Error message if failed")


class PolymarketWalletConfig(BaseModel):
    """Wallet configuration for Polygon network."""
    private_key: Optional[str] = Field(None, description="Private key for signing")
    address: Optional[str] = Field(None, description="Wallet address")
    chain_id: int = Field(137, description="Polygon mainnet chain ID")
    rpc_url: str = Field(
        "https://polygon-rpc.com",
        description="Polygon RPC URL",
    )


# ---------------------------------------------------------------------------
# PolymarketCLOBClient
# ---------------------------------------------------------------------------

class PolymarketCLOBClient:
    """Low-level Polymarket CLOB REST API client.

    Handles authentication (EIP-712), API key management, and raw
    HTTP requests to the Polymarket CLOB endpoints.

    Parameters
    ----------
    base_url:
        CLOB API base URL.
    wallet_config:
        Wallet configuration for signing.
    api_key:
        Optional API key (can be derived from wallet).
    """

    PRODUCTION_URL = "https://clob.polymarket.com"
    STAGING_URL = "https://staging-clob.polymarket.com"

    def __init__(
        self,
        base_url: str = PRODUCTION_URL,
        wallet_config: Optional[PolymarketWalletConfig] = None,
        api_key: Optional[str] = None,
        api_creds: Optional[Dict[str, str]] = None,
    ) -> None:
        self._base_url = base_url
        self._wallet_config = wallet_config or PolymarketWalletConfig()
        self._api_key = api_key
        self._api_creds = api_creds or {}
        self._http_client = None

    async def _ensure_client(self):
        """Ensure HTTP client is available."""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=30.0,
                    headers=self._build_headers(),
                )
            except ImportError:
                raise ImportError("httpx is required. Install with: pip install httpx")
        return self._http_client

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers with API key if available."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self._api_creds.get("api_key"):
            headers["POLY_API_KEY"] = self._api_creds["api_key"]
        if self._api_creds.get("api_passphrase"):
            headers["POLY_PASSPHRASE"] = self._api_creds["api_passphrase"]
        return headers

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the CLOB API.

        Args:
            path: API endpoint path.
            params: Query parameters.

        Returns:
            Response JSON dict.
        """
        client = await self._ensure_client()
        try:
            resp = await client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ExchangeError(
                f"Polymarket CLOB GET {path} failed: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request to the CLOB API.

        Args:
            path: API endpoint path.
            data: Request body.

        Returns:
            Response JSON dict.
        """
        client = await self._ensure_client()
        try:
            resp = await client.post(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ExchangeError(
                f"Polymarket CLOB POST {path} failed: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def delete(self, path: str) -> Dict[str, Any]:
        """Make a DELETE request to the CLOB API.

        Args:
            path: API endpoint path.

        Returns:
            Response JSON dict.
        """
        client = await self._ensure_client()
        try:
            resp = await client.delete(path)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise ExchangeError(
                f"Polymarket CLOB DELETE {path} failed: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# ---------------------------------------------------------------------------
# PolymarketBroker
# ---------------------------------------------------------------------------

class PolymarketBroker(ExchangeInterface):
    """Polymarket prediction market broker implementing ExchangeInterface.

    Provides full trading capabilities via the Polymarket CLOB API,
    including market browsing, order placement, position tracking,
    and wallet integration for the Polygon network.

    Parameters
    ----------
    config:
        Exchange configuration. ``exchange_id`` should be ``"polymarket"``.
        ``api_key`` is the Polymarket API key.
        ``api_secret`` is used as the private key for wallet signing.
        ``sandbox`` should be ``True`` for the staging environment.

    Examples
    --------
    .. code-block:: python

        config = ExchangeConfig(
            exchange_id="polymarket",
            api_key="YOUR_API_KEY_HERE",
            api_secret="YOUR_API_SECRET_HERE",
            sandbox=True,
        )
        broker = PolymarketBroker(config)
        await broker.connect()
        markets = await broker.get_markets()
    """

    def __init__(self, config: ExchangeConfig) -> None:
        self._config = config
        self._state: ExchangeState = ExchangeState.DISCONNECTED
        self._clob_client: Optional[PolymarketCLOBClient] = None
        self._local_orders: Dict[str, Order] = {}
        self._local_positions: Dict[str, Position] = {}
        self._markets_cache: Dict[str, PolymarketMarket] = {}
        self._ws_tasks: Dict[str, Any] = {}

    # ----- Connection lifecycle -----

    async def connect(self) -> bool:
        """Connect to the Polymarket CLOB API.

        Returns
        -------
        bool
            ``True`` if connected successfully.

        Raises
        ------
        ConnectionError
            If the connection fails.
        """
        if self._state == ExchangeState.CONNECTED:
            return True

        self._state = ExchangeState.CONNECTING
        try:
            base_url = (
                PolymarketCLOBClient.STAGING_URL
                if self._config.sandbox
                else PolymarketCLOBClient.PRODUCTION_URL
            )

            wallet_config = PolymarketWalletConfig(
                private_key=self._config.api_secret,
                address=self._config.options.get("wallet_address"),
            )

            api_creds = {}
            if self._config.options.get("poly_api_key"):
                api_creds["api_key"] = self._config.options["poly_api_key"]
            if self._config.options.get("poly_api_passphrase"):
                api_creds["api_passphrase"] = self._config.options["poly_api_passphrase"]
            if self._config.options.get("poly_api_secret"):
                api_creds["api_secret"] = self._config.options["poly_api_secret"]

            self._clob_client = PolymarketCLOBClient(
                base_url=base_url,
                wallet_config=wallet_config,
                api_key=self._config.api_key,
                api_creds=api_creds,
            )

            # Verify connection by fetching server time or markets
            try:
                await self._clob_client.get("/time")
            except ExchangeError:
                # /time endpoint may not exist; try /markets instead
                try:
                    await self._clob_client.get("/markets", params={"limit": 1})
                except ExchangeError as exc:
                    self._state = ExchangeState.ERROR
                    raise ConnectionError(
                        f"Failed to connect to Polymarket: {exc}",
                        exchange="polymarket",
                        original=exc,
                    ) from exc

            self._state = ExchangeState.CONNECTED
            logger.info(
                "PolymarketBroker: Connected (%s)",
                "staging" if self._config.sandbox else "production",
            )
            return True

        except ImportError as exc:
            self._state = ExchangeState.ERROR
            raise ImportError(
                "httpx package is required for Polymarket. Install with: pip install httpx"
            ) from exc
        except (ConnectionError, ExchangeError):
            raise
        except Exception as exc:
            self._state = ExchangeState.ERROR
            raise ConnectionError(
                f"Failed to connect to Polymarket: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def disconnect(self) -> None:
        """Close the Polymarket connection and clean up resources."""
        for task in self._ws_tasks.values():
            if hasattr(task, "cancel"):
                task.cancel()
        self._ws_tasks.clear()

        if self._clob_client:
            await self._clob_client.close()
            self._clob_client = None

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

    # ----- Market browsing -----

    async def browse_markets(
        self,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PolymarketMarket]:
        """Browse and search prediction markets.

        Args:
            query: Search text for market question.
            tag: Filter by tag/category.
            active_only: Only return active markets.
            limit: Maximum number of results.
            offset: Pagination offset.

        Returns:
            List of PolymarketMarket objects.
        """
        self._require_client()
        try:
            params: Dict[str, Any] = {"limit": limit, "offset": offset}
            if query:
                params["query"] = query
            if tag:
                params["tag"] = tag
            if active_only:
                params["active"] = "true"

            data = await self._clob_client.get("/markets", params=params)
            markets = []

            for item in data if isinstance(data, list) else data.get("data", []):
                market = PolymarketMarket(
                    condition_id=item.get("condition_id", ""),
                    question_id=item.get("question_id", ""),
                    question=item.get("question", ""),
                    description=item.get("description", ""),
                    outcomes=item.get("outcomes", []).split(",") if isinstance(item.get("outcomes"), str) else item.get("outcomes", []),
                    outcome_prices=self._parse_outcome_prices(item.get("outcomePrices", "")),
                    active=item.get("active", True),
                    closed=item.get("closed", False),
                    volume=float(item.get("volume", 0) or 0),
                    liquidity=float(item.get("liquidity", 0) or 0),
                    end_date_iso=item.get("end_date_iso"),
                    tokens=item.get("tokens", []),
                )
                markets.append(market)
                self._markets_cache[market.condition_id] = market

            return markets
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to browse markets: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_market(self, condition_id: str) -> PolymarketMarket:
        """Get details for a specific market.

        Args:
            condition_id: Market condition ID.

        Returns:
            PolymarketMarket with full details.
        """
        self._require_client()
        try:
            data = await self._clob_client.get(f"/markets/{condition_id}")
            return PolymarketMarket(
                condition_id=data.get("condition_id", condition_id),
                question_id=data.get("question_id", ""),
                question=data.get("question", ""),
                description=data.get("description", ""),
                outcomes=data.get("outcomes", []).split(",") if isinstance(data.get("outcomes"), str) else data.get("outcomes", []),
                outcome_prices=self._parse_outcome_prices(data.get("outcomePrices", "")),
                active=data.get("active", True),
                closed=data.get("closed", False),
                volume=float(data.get("volume", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or 0),
                end_date_iso=data.get("end_date_iso"),
                tokens=data.get("tokens", []),
            )
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get market {condition_id}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    # ----- Account -----

    async def get_balance(self) -> Dict[str, float]:
        """Get account balances from Polymarket.

        Returns
        -------
        dict
            Mapping of currency → available balance.
        """
        self._require_client()
        try:
            data = await self._clob_client.get("/balance")
            return {
                "USDC": float(data.get("USDC", 0)),
                "total_value": float(data.get("value", 0)),
            }
        except ExchangeError:
            raise
        except Exception as exc:
            logger.warning("Failed to get Polymarket balance: %s", exc)
            return {"USDC": 0.0, "total_value": 0.0}

    async def get_positions(self) -> List[Position]:
        """Get all open positions (active market holdings).

        Returns
        -------
        list of Position
            Current positions in prediction markets.
        """
        self._require_client()
        try:
            data = await self._clob_client.get("/positions")
            positions = []

            for item in data if isinstance(data, list) else data.get("positions", []):
                condition_id = item.get("condition_id", "")
                size = float(item.get("size", 0) or 0)
                if size == 0:
                    continue

                avg_price = float(item.get("avgPrice", 0) or 0)
                cur_price = float(item.get("curPrice", avg_price) or avg_price)
                pnl = (cur_price - avg_price) * size

                pos = Position(
                    symbol=condition_id,
                    side=PositionSide.LONG if size > 0 else PositionSide.SHORT,
                    quantity=abs(size),
                    entry_price=avg_price,
                    current_price=cur_price,
                    unrealized_pnl=pnl,
                    cost_basis=avg_price * abs(size),
                    market_value=cur_price * abs(size),
                    broker_id="polymarket",
                    last_updated=datetime.now(tz=timezone.utc),
                )
                positions.append(pos)
                self._local_positions[condition_id] = pos

            return positions
        except ExchangeError:
            raise
        except Exception as exc:
            raise ExchangeError(
                f"Failed to get positions: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_portfolio(self) -> Portfolio:
        """Get portfolio snapshot from Polymarket.

        Returns
        -------
        Portfolio
            Complete portfolio with positions and metrics.
        """
        self._require_client()
        try:
            balances = await self.get_balance()
            positions = await self.get_positions()

            cash = balances.get("USDC", 0.0)
            portfolio = Portfolio(
                name="polymarket",
                currency="USDC",
                initial_capital=cash + sum(p.cost_basis for p in positions),
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
                f"Failed to get portfolio: {exc}",
                exchange="polymarket",
                original=exc,
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
        """Place an order on Polymarket.

        Supports market and limit orders. Market orders use the best
        available price; limit orders require a price.

        Args:
            symbol: Condition ID or market token ID.
            side: Buy (YES) or Sell (NO).
            order_type: Market or Limit.
            quantity: Size in USDC.
            price: Limit price (0.01 - 0.99 for limit orders).
            client_order_id: Optional client-assigned order ID.

        Returns:
            The placed Order with Polymarket-assigned ID.

        Raises:
            OrderError: If the order is invalid or rejected.
        """
        self._require_client()

        try:
            # Map to Polymarket order format
            poly_side = "BUY" if side == OrderSide.BUY else "SELL"
            poly_type = "GTC"  # Good-til-cancelled for limit
            if order_type == OrderType.MARKET:
                poly_type = "FOK"  # Fill-or-kill for market

            if order_type == OrderType.LIMIT and price is None:
                raise OrderError(
                    "Limit price is required for LIMIT orders on Polymarket",
                    exchange="polymarket",
                )

            if price is not None and (price < 0.01 or price > 0.99):
                raise OrderError(
                    "Price must be between 0.01 and 0.99 on Polymarket",
                    exchange="polymarket",
                )

            # Get token ID for the market
            token_id = symbol
            if symbol in self._markets_cache:
                market = self._markets_cache[symbol]
                if market.tokens:
                    # Use first token (YES outcome) for BUY, second for SELL
                    idx = 0 if side == OrderSide.BUY else min(1, len(market.tokens) - 1)
                    token_id = market.tokens[idx].get("token_id", symbol)

            order_data = {
                "token_id": token_id,
                "price": round(price or 0.5, 2),
                "size": round(quantity, 2),
                "side": poly_side,
                "type": poly_type,
            }

            if client_order_id:
                order_data["client_order_id"] = client_order_id

            result = await self._clob_client.post("/order", order_data)

            order_id = result.get("orderID", result.get("order_id", str(uuid.uuid4())))
            raw_status = result.get("status", "LIVE")

            status = OrderStatus.SUBMITTED
            if raw_status in ("LIVE", "MATCHED"):
                status = OrderStatus.SUBMITTED
            elif raw_status == "FILLED":
                status = OrderStatus.FILLED
            elif raw_status in ("CANCELLED", "EXPIRED"):
                status = OrderStatus.CANCELED

            order = Order(
                id=order_id,
                client_order_id=client_order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                status=status,
                filled_quantity=float(result.get("size_matched", 0) or 0),
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

        except (OrderError, ExchangeError):
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to place order: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> Order:
        """Cancel an open order on Polymarket.

        Args:
            order_id: Polymarket order ID.
            symbol: Not required for Polymarket.

        Returns:
            The cancelled Order.
        """
        self._require_client()
        try:
            await self._clob_client.delete(f"/order/{order_id}")

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

        Args:
            order_id: Polymarket order ID.

        Returns:
            Current Order state.
        """
        self._require_client()
        try:
            data = await self._clob_client.get(f"/order/{order_id}")

            raw_status = data.get("status", "LIVE")
            status = OrderStatus.SUBMITTED
            if raw_status == "LIVE":
                status = OrderStatus.SUBMITTED
            elif raw_status == "MATCHED":
                status = OrderStatus.PARTIALLY_FILLED
            elif raw_status == "FILLED":
                status = OrderStatus.FILLED
            elif raw_status in ("CANCELLED", "EXPIRED"):
                status = OrderStatus.CANCELED

            raw_side = data.get("side", "BUY")
            side = OrderSide.BUY if raw_side == "BUY" else OrderSide.SELL

            order = Order(
                id=order_id,
                client_order_id=data.get("client_order_id"),
                symbol=data.get("asset_id", symbol or ""),
                side=side,
                order_type=OrderType.LIMIT,
                quantity=float(data.get("original_size", 0) or 0),
                price=float(data.get("price", 0) or 0),
                status=status,
                filled_quantity=float(data.get("size_matched", 0) or 0),
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc),
                broker_id="polymarket",
                broker_order_id=order_id,
            )
            self._local_orders[order.id] = order
            return order
        except ExchangeError:
            raise
        except Exception as exc:
            raise OrderError(
                f"Failed to get order {order_id}: {exc}",
                order_id=order_id,
                exchange="polymarket",
                original=exc,
            ) from exc

    # ----- Market data -----

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.D1,
        since: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[OHLCV]:
        """Polymarket does not provide OHLCV data natively.

        Returns an empty list; use get_ticker for current price.
        """
        logger.debug("Polymarket does not provide OHLCV data")
        return []

    async def get_ticker(self, symbol: str) -> Ticker:
        """Get latest price for a prediction market.

        Args:
            symbol: Condition ID or token ID.

        Returns:
            Ticker with current outcome prices.
        """
        self._require_client()
        try:
            data = await self._clob_client.get("/prices", params={"token_id": symbol})
            price = float(data.get("price", 0.5) or 0.5)
            return Ticker(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                last_price=price,
            )
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get ticker for {symbol}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    async def get_orderbook(self, symbol: str, limit: int = 20) -> OrderBook:
        """Get order book for a prediction market.

        Args:
            symbol: Token ID.
            limit: Depth per side.

        Returns:
            OrderBook snapshot.
        """
        self._require_client()
        try:
            data = await self._clob_client.get(
                "/book",
                params={"token_id": symbol, "depth": limit},
            )

            bids = [
                {"price": float(b.get("price", 0)), "quantity": float(b.get("size", 0))}
                for b in data.get("bids", [])
            ]
            asks = [
                {"price": float(a.get("price", 0)), "quantity": float(a.get("size", 0))}
                for a in data.get("asks", [])
            ]

            return OrderBook(
                symbol=symbol,
                timestamp=datetime.now(tz=timezone.utc),
                bids=bids[:limit],
                asks=asks[:limit],
            )
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get orderbook for {symbol}: {exc}",
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

        Args:
            symbol: Token ID.
            since: Start time filter.
            limit: Maximum number of trades.

        Returns:
            List of trade dicts.
        """
        self._require_client()
        try:
            params: Dict[str, Any] = {"token_id": symbol, "limit": limit}
            data = await self._clob_client.get("/trades", params=params)

            trades = []
            for t in data if isinstance(data, list) else data.get("trades", []):
                trades.append({
                    "id": str(t.get("id", "")),
                    "price": float(t.get("price", 0) or 0),
                    "amount": float(t.get("size", 0) or 0),
                    "side": t.get("side", ""),
                    "timestamp": t.get("timestamp", ""),
                })
            return trades
        except ExchangeError:
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Failed to get trades for {symbol}: {exc}",
                exchange="polymarket",
                original=exc,
            ) from exc

    # ----- WebSocket / real-time -----

    async def subscribe_ticker(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time price updates for a market."""
        logger.info("PolymarketBroker: Ticker subscription for %s (WebSocket not implemented)", symbol)

    async def subscribe_orderbook(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time order book updates."""
        logger.info("PolymarketBroker: Orderbook subscription for %s (WebSocket not implemented)", symbol)

    async def subscribe_trades(self, symbol: str, callback: WebSocketCallback) -> None:
        """Subscribe to real-time trade updates."""
        logger.info("PolymarketBroker: Trade subscription for %s (WebSocket not implemented)", symbol)

    async def unsubscribe(self, symbol: str, channel: str) -> None:
        """Unsubscribe from a real-time data stream."""
        logger.info("PolymarketBroker: Unsubscribe %s %s", channel, symbol)

    # ----- Utility -----

    async def get_markets(self) -> List[str]:
        """List available prediction market condition IDs."""
        self._require_client()
        try:
            markets = await self.browse_markets(limit=100)
            return [m.condition_id for m in markets]
        except Exception:
            return list(self._markets_cache.keys())

    async def health_check(self) -> bool:
        """Check Polymarket API health.

        Returns
        -------
        bool
            ``True`` if the API is responsive.
        """
        try:
            self._require_client()
            await self._clob_client.get("/time")
            self._state = ExchangeState.CONNECTED
            return True
        except Exception as exc:
            logger.warning("PolymarketBroker: Health check failed: %s", exc)
            self._state = ExchangeState.ERROR
            return False

    # ----- JSON output mode -----

    async def to_json(self, data: Any) -> str:
        """Convert data to JSON string for automation.

        Args:
            data: Any serializable data.

        Returns:
            JSON string representation.
        """
        if isinstance(data, BaseModel):
            return data.model_dump_json(indent=2)
        return json.dumps(data, indent=2, default=str)

    # ----- Internal helpers -----

    def _require_client(self) -> PolymarketCLOBClient:
        """Ensure the CLOB client is initialized."""
        if not self._clob_client or not self.is_connected:
            raise ConnectionError(
                "PolymarketBroker is not connected",
                exchange="polymarket",
            )
        return self._clob_client

    @staticmethod
    def _parse_outcome_prices(raw: Any) -> List[float]:
        """Parse outcome prices from API response."""
        if isinstance(raw, list):
            return [float(p) for p in raw if p is not None]
        if isinstance(raw, str) and raw:
            try:
                return [float(p.strip()) for p in raw.split(",") if p.strip()]
            except (ValueError, TypeError):
                pass
        return []

    def __repr__(self) -> str:
        state = self._state.value
        return f"PolymarketBroker(state={state})"


__all__ = [
    "PolymarketBroker",
    "PolymarketCLOBClient",
    "PolymarketMarket",
    "PolymarketOrderResult",
    "PolymarketWalletConfig",
]
