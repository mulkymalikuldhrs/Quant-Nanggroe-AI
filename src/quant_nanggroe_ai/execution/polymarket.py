"""
Polymarket Broker — Prediction Market Execution
================================================
Integration with the Polymarket CLOB (Central Limit Order Book) API
for prediction market trading. Supports buying/selling shares,
market discovery, and position management.

Enhanced with features from the sim repo TypeScript tools:
    - Full Gamma API: events, markets, tags, series, search
    - Full CLOB API: orderbook, price, midpoint, spread, tick_size, price_history
    - Full Data API: positions, trades
    - Market discovery and search
    - Buy/sell shares with limit and market orders
    - Position tracking and PnL
    - Order cancellation
    - CLOB API integration with rate limiting
    - Order signing via EIP-712 (Ethereum)

Polymarket API Docs: https://docs.polymarket.com
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class MarketOutcome(BaseModel):
    """A possible outcome for a prediction market."""

    outcome: str
    price: float = 0.0
    token_id: str = ""
    volume: float = 0.0


class PolymarketMarket(BaseModel):
    """A prediction market on Polymarket."""

    condition_id: str
    question: str
    slug: str = ""
    end_date: str = ""
    active: bool = True
    closed: bool = False
    outcomes: list[MarketOutcome] = Field(default_factory=list)
    volume: float = 0.0
    liquidity: float = 0.0
    category: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketOrder(BaseModel):
    """Order placed on Polymarket."""

    order_id: str = ""
    market_id: str
    side: str  # BUY / SELL
    outcome: str  # YES / NO
    price: float
    size: float
    order_type: str = "GTC"  # GTC, GTD, FOK
    status: str = "PENDING"
    filled_size: float = 0.0
    filled_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.now)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketPosition(BaseModel):
    """Position in a prediction market."""

    market_id: str
    condition_id: str = ""
    outcome: str
    size: float
    avg_price: float
    current_price: float = 0.0
    pnl: float = 0.0
    question: str = ""


class PolymarketBalance(BaseModel):
    """Account balance on Polymarket."""

    usdc_balance: float = 0.0
    total_position_value: float = 0.0
    total_pnl: float = 0.0
    positions: list[PolymarketPosition] = Field(default_factory=list)


class PolymarketEvent(BaseModel):
    """An event containing one or more markets on Polymarket."""

    id: str = ""
    ticker: str = ""
    slug: str = ""
    title: str = ""
    description: str = ""
    start_date: str = ""
    creation_date: str = ""
    end_date: str = ""
    image: str = ""
    icon: str = ""
    active: bool = True
    closed: bool = False
    archived: bool = False
    featured: bool = False
    restricted: bool = False
    liquidity: float = 0.0
    volume: float = 0.0
    open_interest: float = 0.0
    comment_count: int = 0
    markets: list[PolymarketMarket] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketTag(BaseModel):
    """A tag/category on Polymarket."""

    id: str = ""
    label: str = ""
    slug: str = ""


class PolymarketSeries(BaseModel):
    """A series of related events on Polymarket."""

    id: str = ""
    ticker: str = ""
    slug: str = ""
    title: str = ""
    series_type: str = ""
    recurrence: str = ""
    image: str = ""
    icon: str = ""
    active: bool = True
    closed: bool = False
    archived: bool = False
    featured: bool = False
    restricted: bool = False
    created_at: str = ""
    updated_at: str = ""
    volume: float = 0.0
    liquidity: float = 0.0
    comment_count: int = 0
    event_count: int = 0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketOrderbookEntry(BaseModel):
    """A single entry in the Polymarket orderbook."""

    price: str = ""
    size: str = ""


class PolymarketOrderbook(BaseModel):
    """Orderbook data from Polymarket CLOB."""

    market: str = ""
    asset_id: str = ""
    hash: str = ""
    timestamp: str = ""
    bids: list[PolymarketOrderbookEntry] = Field(default_factory=list)
    asks: list[PolymarketOrderbookEntry] = Field(default_factory=list)


class PolymarketPriceHistoryEntry(BaseModel):
    """A single entry in price history."""

    timestamp: int = 0
    price: float = 0.0


class PolymarketSearchResult(BaseModel):
    """Search results from Polymarket."""

    markets: list[PolymarketMarket] = Field(default_factory=list)
    events: list[PolymarketEvent] = Field(default_factory=list)


class PolymarketSpread(BaseModel):
    """Bid-ask spread from Polymarket."""

    bid: str = ""
    ask: str = ""


class PolymarketTradeRecord(BaseModel):
    """A trade record from Polymarket Data API."""

    id: str = ""
    market: str = ""
    asset_id: str = ""
    side: str = ""
    size: str = ""
    price: str = ""
    timestamp: str = ""
    maker: str = ""
    taker: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# POLYMARKET BROKER
# ══════════════════════════════════════════════════════════════════════


class PolymarketBroker:
    """
    Polymarket prediction market broker.

    Connects to the Polymarket CLOB API for order execution,
    market data, and position management.

    Args:
        api_key: Polymarket API key
        api_secret: Polymarket API secret
        api_passphrase: Polymarket API passphrase
        wallet_private_key: Ethereum private key for signing
        base_url: CLOB API base URL
        chain_id: Chain ID (137 for Polygon)
        max_retries: Maximum retry attempts on failures

    Example:
        broker = PolymarketBroker(
            api_key="...",
            api_secret="...",
            api_passphrase="...",
            wallet_private_key="0x...",
        )
        markets = await broker.get_markets(query="election")
        order = await broker.buy_shares(market_id, "YES", 0.55, 100)
    """

    CLOB_URL = "https://clob.polymarket.com"
    GAMMA_URL = "https://gamma-api.polymarket.com"
    DATA_URL = "https://data-api.polymarket.com"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        api_passphrase: str = "",
        wallet_private_key: str = "",
        base_url: str | None = None,
        chain_id: int = 137,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._api_passphrase = api_passphrase
        self._wallet_key = wallet_private_key
        self._base_url = base_url or self.CLOB_URL
        self._chain_id = chain_id
        self._max_retries = max_retries

        self._http_client: httpx.AsyncClient | None = None
        self._nonce = 0
        self._positions_cache: dict[str, PolymarketPosition] = {}

        if api_key and api_secret:
            logger.info("Polymarket broker initialized with API credentials")
        else:
            logger.warning(
                "Polymarket broker initialized without API keys. "
                "Market queries will work; trading requires credentials."
            )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication headers."""
        if self._http_client is None or self._http_client.is_closed:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["POLY_API_KEY"] = self._api_key
                headers["POLY_API_SECRET"] = self._api_secret
                headers["POLY_PASSPHRASE"] = self._api_passphrase

            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers=headers,
            )
        return self._http_client

    # ══════════════════════════════════════════════════════════════════
    # MARKET DISCOVERY
    # ══════════════════════════════════════════════════════════════════

    async def get_markets(
        self,
        query: str | None = None,
        active_only: bool = True,
        limit: int = 20,
        offset: int = 0,
        tag: str | None = None,
    ) -> list[PolymarketMarket]:
        """
        Search and retrieve prediction markets.

        Args:
            query: Search query string
            active_only: Only return active markets
            limit: Maximum number of results
            offset: Pagination offset
            tag: Category tag filter

        Returns:
            List of PolymarketMarket objects
        """
        client = await self._get_http_client()

        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "closed": "false" if active_only else "true",
        }
        if query:
            params["tag"] = query
        if tag:
            params["tag"] = tag

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/markets", params=params
            )
            response.raise_for_status()
            data = response.json()

            markets = []
            for item in data:
                outcomes = self._parse_market_outcomes(item)
                market = PolymarketMarket(
                    condition_id=item.get("conditionId", ""),
                    question=item.get("question", ""),
                    slug=item.get("slug", ""),
                    end_date=item.get("endDate", ""),
                    active=item.get("active", True),
                    closed=item.get("closed", False),
                    outcomes=outcomes,
                    volume=float(item.get("volume", 0)),
                    liquidity=float(item.get("liquidity", 0)),
                    category=item.get("category", ""),
                    raw_response=item,
                )
                markets.append(market)

            logger.info("Retrieved %d markets (query=%s)", len(markets), query)
            return markets

        except Exception as exc:
            logger.error("Get markets failed: %s", exc)
            return []

    async def get_market(self, condition_id: str) -> PolymarketMarket | None:
        """
        Get a specific market by condition ID.

        Args:
            condition_id: Market condition ID

        Returns:
            PolymarketMarket or None if not found
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/markets/{condition_id}"
            )
            response.raise_for_status()
            item = response.json()

            outcomes = self._parse_market_outcomes(item)
            return PolymarketMarket(
                condition_id=item.get("conditionId", condition_id),
                question=item.get("question", ""),
                slug=item.get("slug", ""),
                end_date=item.get("endDate", ""),
                active=item.get("active", True),
                closed=item.get("closed", False),
                outcomes=outcomes,
                volume=float(item.get("volume", 0)),
                liquidity=float(item.get("liquidity", 0)),
                raw_response=item,
            )
        except Exception as exc:
            logger.error("Get market %s failed: %s", condition_id[:8], exc)
            return None

    def _parse_market_outcomes(self, data: dict[str, Any]) -> list[MarketOutcome]:
        """Parse market outcome data from API response."""
        outcomes = []
        tokens = data.get("tokens", [])
        for token in tokens:
            outcomes.append(MarketOutcome(
                outcome=token.get("outcome", ""),
                price=float(token.get("price", 0)),
                token_id=token.get("tokenID", ""),
                volume=float(token.get("volume", 0)),
            ))

        # Fallback if no tokens field
        if not outcomes:
            for outcome_str in data.get("outcomes", ["Yes", "No"]):
                outcomes.append(MarketOutcome(outcome=outcome_str))

        return outcomes

    @staticmethod
    def _parse_market_from_gamma(data: dict[str, Any]) -> PolymarketMarket:
        """Parse a market from Gamma API response."""
        clob_token_ids = data.get("clobTokenIds", [])
        if isinstance(clob_token_ids, str):
            try:
                import json
                clob_token_ids = json.loads(clob_token_ids)
            except (json.JSONDecodeError, ValueError):
                clob_token_ids = []

        outcomes = data.get("outcomes", "")
        outcome_prices = data.get("outcomePrices", "")

        return PolymarketMarket(
            condition_id=data.get("conditionId", data.get("id", "")),
            question=data.get("question", ""),
            slug=data.get("slug", ""),
            end_date=data.get("endDate", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
            outcomes=outcomes if isinstance(outcomes, list) else [],
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            category=data.get("category", ""),
            raw_response=data,
        )

    @staticmethod
    def _parse_event(data: dict[str, Any]) -> PolymarketEvent:
        """Parse an event from Gamma API response."""
        return PolymarketEvent(
            id=str(data.get("id", "")),
            ticker=data.get("ticker", ""),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            start_date=data.get("startDate", ""),
            creation_date=data.get("creationDate", ""),
            end_date=data.get("endDate", ""),
            image=data.get("image", ""),
            icon=data.get("icon", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
            archived=data.get("archived", False),
            featured=data.get("featured", False),
            restricted=data.get("restricted", False),
            liquidity=float(data.get("liquidity", 0)),
            volume=float(data.get("volume", 0)),
            open_interest=float(data.get("openInterest", 0)),
            comment_count=int(data.get("commentCount", 0)),
            raw_response=data,
        )

    @staticmethod
    def _parse_series(data: dict[str, Any]) -> PolymarketSeries:
        """Parse a series from Gamma API response."""
        return PolymarketSeries(
            id=str(data.get("id", "")),
            ticker=data.get("ticker", ""),
            slug=data.get("slug", ""),
            title=data.get("title", ""),
            series_type=data.get("seriesType", ""),
            recurrence=data.get("recurrence", ""),
            image=data.get("image", ""),
            icon=data.get("icon", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
            archived=data.get("archived", False),
            featured=data.get("featured", False),
            restricted=data.get("restricted", False),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            volume=float(data.get("volume", 0)),
            liquidity=float(data.get("liquidity", 0)),
            comment_count=int(data.get("commentCount", 0)),
            event_count=int(data.get("eventCount", 0)),
            raw_response=data,
        )

    # ══════════════════════════════════════════════════════════════════
    # ORDER EXECUTION
    # ══════════════════════════════════════════════════════════════════

    async def buy_shares(
        self,
        market_id: str,
        outcome: str,
        price: float,
        size: float,
        order_type: str = "GTC",
    ) -> PolymarketOrder:
        """
        Buy shares in a prediction market.

        Args:
            market_id: Market condition ID
            outcome: "YES" or "NO"
            price: Price per share (0.0 - 1.0)
            size: Number of shares
            order_type: "GTC", "GTD", or "FOK"

        Returns:
            PolymarketOrder with submission details
        """
        return await self._place_order(
            market_id=market_id,
            side="BUY",
            outcome=outcome,
            price=price,
            size=size,
            order_type=order_type,
        )

    async def sell_shares(
        self,
        market_id: str,
        outcome: str,
        price: float,
        size: float,
        order_type: str = "GTC",
    ) -> PolymarketOrder:
        """
        Sell shares in a prediction market.

        Args:
            market_id: Market condition ID
            outcome: "YES" or "NO"
            price: Price per share (0.0 - 1.0)
            size: Number of shares
            order_type: Order type

        Returns:
            PolymarketOrder with submission details
        """
        return await self._place_order(
            market_id=market_id,
            side="SELL",
            outcome=outcome,
            price=price,
            size=size,
            order_type=order_type,
        )

    async def _place_order(
        self,
        market_id: str,
        side: str,
        outcome: str,
        price: float,
        size: float,
        order_type: str = "GTC",
    ) -> PolymarketOrder:
        """Internal order placement with signing."""
        if not self._api_key:
            return PolymarketOrder(
                market_id=market_id,
                side=side,
                outcome=outcome,
                price=price,
                size=size,
                status="REJECTED",
                raw_response={"error": "API credentials required for trading"},
            )

        # Validate price range for prediction markets
        if not (0.01 <= price <= 0.99):
            return PolymarketOrder(
                market_id=market_id,
                side=side,
                outcome=outcome,
                price=price,
                size=size,
                status="REJECTED",
                raw_response={"error": f"Price {price} out of valid range [0.01, 0.99]"},
            )

        client = await self._get_http_client()

        # Build order payload
        self._nonce += 1
        order_payload = {
            "market": market_id,
            "side": side.upper(),
            "outcome": outcome.upper(),
            "price": round(price, 2),
            "size": size,
            "order_type": order_type,
            "nonce": self._nonce,
        }

        # Sign order if wallet key available
        if self._wallet_key:
            try:
                signature = self._sign_order(order_payload)
                order_payload["signature"] = signature
            except Exception as exc:
                logger.warning("Order signing failed, proceeding unsigned: %s", exc)

        try:
            response = await self._retry_request(
                client.post,
                f"{self._base_url}/order",
                json=order_payload,
            )
            data = response.json() if response else {}

            order_id = data.get("orderID", data.get("id", ""))
            status = data.get("status", "PENDING")

            logger.info(
                "Polymarket order: %s %s %s @ %.2f x%.0f (id=%s, status=%s)",
                side, outcome, market_id[:8], price, size, order_id[:8] if order_id else "N/A", status,
            )

            return PolymarketOrder(
                order_id=order_id,
                market_id=market_id,
                side=side,
                outcome=outcome,
                price=price,
                size=size,
                order_type=order_type,
                status=status,
                raw_response=data,
            )

        except Exception as exc:
            logger.error("Polymarket order failed: %s", exc)
            return PolymarketOrder(
                market_id=market_id,
                side=side,
                outcome=outcome,
                price=price,
                size=size,
                status="REJECTED",
                raw_response={"error": str(exc)},
            )

    # ══════════════════════════════════════════════════════════════════
    # POSITION & BALANCE QUERIES
    # ══════════════════════════════════════════════════════════════════

    async def get_positions(self) -> list[PolymarketPosition]:
        """
        Get all current positions.

        Returns:
            List of PolymarketPosition objects
        """
        if not self._api_key:
            logger.warning("API credentials required for position queries")
            return []

        client = await self._get_http_client()

        try:
            response = await self._retry_request(
                client.get, f"{self._base_url}/positions"
            )
            data = response.json() if response else {}

            positions = []
            for item in data if isinstance(data, list) else data.get("positions", []):
                pos = PolymarketPosition(
                    market_id=item.get("market", ""),
                    condition_id=item.get("conditionId", ""),
                    outcome=item.get("outcome", ""),
                    size=float(item.get("size", 0)),
                    avg_price=float(item.get("avgPrice", 0)),
                    current_price=float(item.get("curPrice", 0)),
                    pnl=float(item.get("pnl", 0)),
                    question=item.get("question", ""),
                )
                positions.append(pos)
                self._positions_cache[pos.market_id] = pos

            return positions

        except Exception as exc:
            logger.error("Get positions failed: %s", exc)
            return list(self._positions_cache.values())

    async def get_balance(self) -> PolymarketBalance:
        """
        Get account balance and position summary.

        Returns:
            PolymarketBalance with USDC balance and position values
        """
        if not self._api_key:
            return PolymarketBalance()

        client = await self._get_http_client()

        try:
            response = await self._retry_request(
                client.get, f"{self._base_url}/balance"
            )
            data = response.json() if response else {}

            positions = await self.get_positions()
            total_pos_value = sum(p.size * p.current_price for p in positions)
            total_pnl = sum(p.pnl for p in positions)

            return PolymarketBalance(
                usdc_balance=float(data.get("balance", 0)),
                total_position_value=round(total_pos_value, 2),
                total_pnl=round(total_pnl, 2),
                positions=positions,
            )
        except Exception as exc:
            logger.error("Get balance failed: %s", exc)
            return PolymarketBalance()

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an open order.

        Args:
            order_id: Polymarket order ID

        Returns:
            Dict with cancellation status
        """
        if not self._api_key:
            return {"error": "API credentials required"}

        client = await self._get_http_client()

        try:
            response = await self._retry_request(
                client.delete, f"{self._base_url}/order/{order_id}"
            )
            data = response.json() if response else {}
            logger.info("Order cancelled: %s", order_id)
            return {"order_id": order_id, "status": "cancelled", "data": data}
        except Exception as exc:
            logger.error("Cancel order failed: %s", exc)
            return {"order_id": order_id, "status": "error", "error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # EVENT QUERIES (from sim repo Gamma API)
    # ══════════════════════════════════════════════════════════════════

    async def get_events(
        self,
        closed: bool | None = None,
        order: str | None = None,
        ascending: bool | None = None,
        tag_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PolymarketEvent]:
        """
        Retrieve a list of events from Polymarket.

        Adapted from sim repo polymarket/get_events.ts

        Args:
            closed: Filter for closed (True) or active (False) events
            order: Sort field (volume, liquidity, startDate, endDate, createdAt)
            ascending: Sort direction
            tag_id: Filter by tag ID
            limit: Number of results (max 50)
            offset: Pagination offset

        Returns:
            List of PolymarketEvent objects
        """
        client = await self._get_http_client()

        params: dict[str, Any] = {"limit": min(limit, 50), "offset": offset}
        if closed is not None:
            params["closed"] = str(closed).lower()
        if order:
            params["order"] = order
        if ascending is not None:
            params["ascending"] = str(ascending).lower()
        if tag_id:
            params["tag_id"] = tag_id

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/events", params=params
            )
            response.raise_for_status()
            data = response.json()

            events = []
            for item in data if isinstance(data, list) else []:
                event = self._parse_event(item)
                events.append(event)

            logger.info("Retrieved %d Polymarket events", len(events))
            return events
        except Exception as exc:
            logger.error("Get events failed: %s", exc)
            return []

    async def get_event(
        self,
        event_id: str | None = None,
        slug: str | None = None,
    ) -> PolymarketEvent | None:
        """
        Retrieve a specific event by ID or slug.

        Adapted from sim repo polymarket/get_event.ts

        Args:
            event_id: The event ID
            slug: The event slug (e.g., "2024-presidential-election")

        Returns:
            PolymarketEvent or None
        """
        client = await self._get_http_client()

        try:
            if slug:
                url = f"{self.GAMMA_URL}/events/slug/{slug}"
            else:
                url = f"{self.GAMMA_URL}/events/{event_id}"

            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            return self._parse_event(data)
        except Exception as exc:
            logger.error("Get event failed: %s", exc)
            return None

    # ══════════════════════════════════════════════════════════════════
    # CLOB DATA QUERIES (from sim repo CLOB API)
    # ══════════════════════════════════════════════════════════════════

    async def get_orderbook(self, token_id: str) -> PolymarketOrderbook:
        """
        Retrieve the order book for a specific token.

        Adapted from sim repo polymarket/get_orderbook.ts

        Args:
            token_id: The CLOB token ID (from market clobTokenIds)

        Returns:
            PolymarketOrderbook with bids and asks
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/book",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()

            bids = [
                PolymarketOrderbookEntry(
                    price=b.get("price", ""), size=b.get("size", "")
                )
                for b in data.get("bids", [])
            ]
            asks = [
                PolymarketOrderbookEntry(
                    price=a.get("price", ""), size=a.get("size", "")
                )
                for a in data.get("asks", [])
            ]

            return PolymarketOrderbook(
                market=data.get("market", ""),
                asset_id=data.get("asset_id", ""),
                hash=data.get("hash", ""),
                timestamp=data.get("timestamp", ""),
                bids=bids,
                asks=asks,
            )
        except Exception as exc:
            logger.error("Get orderbook failed: %s", exc)
            return PolymarketOrderbook()

    async def get_price(
        self, token_id: str, side: str = "buy"
    ) -> str:
        """
        Get the current price for a specific token and side.

        Adapted from sim repo polymarket/get_price.ts

        Args:
            token_id: The CLOB token ID
            side: "buy" or "sell"

        Returns:
            Price as a string
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/price",
                params={"token_id": token_id, "side": side},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("price", str(data)) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get price failed: %s", exc)
            return ""

    async def get_midpoint(self, token_id: str) -> str:
        """
        Get the midpoint price for a specific token.

        Adapted from sim repo polymarket/get_midpoint.ts

        Args:
            token_id: The CLOB token ID

        Returns:
            Midpoint price as a string
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/midpoint",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("mid", data.get("midpoint", str(data))) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get midpoint failed: %s", exc)
            return ""

    async def get_last_trade_price(self, token_id: str) -> str:
        """
        Get the last trade price for a specific token.

        Adapted from sim repo polymarket/get_last_trade_price.ts

        Args:
            token_id: The CLOB token ID

        Returns:
            Last trade price as a string
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/last-trade-price",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("price", str(data)) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get last trade price failed: %s", exc)
            return ""

    async def get_spread(self, token_id: str) -> PolymarketSpread:
        """
        Get the bid-ask spread for a specific token.

        Adapted from sim repo polymarket/get_spread.ts

        Args:
            token_id: The CLOB token ID

        Returns:
            PolymarketSpread with bid and ask
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/spread",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()

            return PolymarketSpread(
                bid=data.get("bid", ""),
                ask=data.get("ask", ""),
            )
        except Exception as exc:
            logger.error("Get spread failed: %s", exc)
            return PolymarketSpread()

    async def get_tick_size(self, token_id: str) -> str:
        """
        Get the minimum tick size for a specific token.

        Adapted from sim repo polymarket/get_tick_size.ts

        Args:
            token_id: The CLOB token ID

        Returns:
            Tick size as a string
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.CLOB_URL}/tick-size",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("minimum_tick_size", data.get("tick_size", str(data))) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get tick size failed: %s", exc)
            return ""

    async def get_price_history(
        self,
        market: str,
        interval: str | None = None,
        fidelity: int | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[PolymarketPriceHistoryEntry]:
        """
        Get price history for a market.

        Adapted from sim repo polymarket/get_price_history.ts

        Args:
            market: Market condition ID
            interval: Time interval ('1m', '1h', '6h', '1d', '1w', 'max')
            fidelity: Data resolution in minutes
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)

        Returns:
            List of PolymarketPriceHistoryEntry
        """
        client = await self._get_http_client()

        params: dict[str, Any] = {"market": market}
        if interval:
            params["interval"] = interval
        if fidelity:
            params["fidelity"] = fidelity
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/markets/{market}/price-history",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            history = []
            entries = data if isinstance(data, list) else data.get("history", [])
            for item in entries:
                history.append(PolymarketPriceHistoryEntry(
                    timestamp=int(item.get("t", item.get("timestamp", 0))),
                    price=float(item.get("p", item.get("price", 0))),
                ))
            return history
        except Exception as exc:
            logger.error("Get price history failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # TAGS, SERIES, SEARCH (from sim repo Gamma API)
    # ══════════════════════════════════════════════════════════════════

    async def get_tags(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PolymarketTag]:
        """
        Get available tags/categories.

        Adapted from sim repo polymarket/get_tags.ts

        Args:
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of PolymarketTag objects
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/tags",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()

            tags = []
            for item in data if isinstance(data, list) else []:
                tags.append(PolymarketTag(
                    id=str(item.get("id", "")),
                    label=item.get("label", ""),
                    slug=item.get("slug", ""),
                ))
            return tags
        except Exception as exc:
            logger.error("Get tags failed: %s", exc)
            return []

    async def get_series(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PolymarketSeries]:
        """
        Get available series.

        Adapted from sim repo polymarket/get_series.ts

        Args:
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of PolymarketSeries objects
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/series",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()

            series_list = []
            for item in data if isinstance(data, list) else []:
                series_list.append(self._parse_series(item))
            return series_list
        except Exception as exc:
            logger.error("Get series failed: %s", exc)
            return []

    async def get_series_by_id(self, series_id: str) -> PolymarketSeries | None:
        """
        Get a specific series by ID.

        Adapted from sim repo polymarket/get_series_by_id.ts

        Args:
            series_id: Series ID

        Returns:
            PolymarketSeries or None
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/series/{series_id}"
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_series(data)
        except Exception as exc:
            logger.error("Get series by ID failed: %s", exc)
            return None

    async def search(
        self,
        query: str,
        limit: int = 50,
        offset: int = 0,
    ) -> PolymarketSearchResult:
        """
        Search Polymarket for markets and events.

        Adapted from sim repo polymarket/search.ts

        Args:
            query: Search query string
            limit: Number of results
            offset: Pagination offset

        Returns:
            PolymarketSearchResult with matching markets and events
        """
        client = await self._get_http_client()

        try:
            response = await client.get(
                f"{self.GAMMA_URL}/search",
                params={"query": query, "limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()

            markets = []
            for item in data.get("markets", []):
                markets.append(self._parse_market_from_gamma(item))

            events = []
            for item in data.get("events", []):
                events.append(self._parse_event(item))

            return PolymarketSearchResult(markets=markets, events=events)
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return PolymarketSearchResult()

    # ══════════════════════════════════════════════════════════════════
    # DATA API QUERIES (from sim repo Data API)
    # ══════════════════════════════════════════════════════════════════

    async def get_trades(
        self,
        user: str | None = None,
        market: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PolymarketTradeRecord]:
        """
        Get trade history from Data API.

        Adapted from sim repo polymarket/get_trades.ts

        Args:
            user: Wallet address filter
            market: Market ID filter
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of PolymarketTradeRecord objects
        """
        client = await self._get_http_client()

        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if user:
            params["user"] = user
        if market:
            params["market"] = market

        try:
            response = await client.get(
                f"{self.DATA_URL}/trades", params=params
            )
            response.raise_for_status()
            data = response.json()

            trades = []
            for item in data if isinstance(data, list) else data.get("trades", []):
                trades.append(PolymarketTradeRecord(
                    id=str(item.get("id", "")),
                    market=item.get("market", ""),
                    asset_id=item.get("asset_id", ""),
                    side=item.get("side", ""),
                    size=item.get("size", ""),
                    price=item.get("price", ""),
                    timestamp=item.get("timestamp", ""),
                    maker=item.get("maker", ""),
                    taker=item.get("taker", ""),
                    raw_response=item,
                ))
            return trades
        except Exception as exc:
            logger.error("Get trades failed: %s", exc)
            return []

    async def get_data_positions(
        self,
        user: str,
        market: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PolymarketPosition]:
        """
        Get positions from Data API (by wallet address).

        Adapted from sim repo polymarket/get_positions.ts

        Args:
            user: Wallet address (required)
            market: Market ID filter
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of PolymarketPosition objects
        """
        client = await self._get_http_client()

        params: dict[str, Any] = {
            "user": user, "limit": limit, "offset": offset
        }
        if market:
            params["market"] = market

        try:
            response = await client.get(
                f"{self.DATA_URL}/positions", params=params
            )
            response.raise_for_status()
            data = response.json()

            positions = []
            for item in data if isinstance(data, list) else data.get("positions", []):
                positions.append(PolymarketPosition(
                    market_id=item.get("market", ""),
                    condition_id=item.get("asset_id", ""),
                    outcome="",
                    size=float(item.get("size", 0)),
                    avg_price=0.0,
                    current_price=float(item.get("curPrice", 0)),
                    pnl=0.0,
                    question="",
                ))
            return positions
        except Exception as exc:
            logger.error("Get data positions failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _sign_order(self, order_payload: dict[str, Any]) -> str:
        """
        Sign an order using EIP-712 typed data.

        For Polymarket CLOB, orders must be signed with an Ethereum key.

        Args:
            order_payload: Order data to sign

        Returns:
            Hex-encoded signature string
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_structured_data

            structured_data = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                    ],
                    "Order": [
                        {"name": "market", "type": "string"},
                        {"name": "side", "type": "string"},
                        {"name": "outcome", "type": "string"},
                        {"name": "price", "type": "uint256"},
                        {"name": "size", "type": "uint256"},
                        {"name": "nonce", "type": "uint256"},
                    ],
                },
                "primaryType": "Order",
                "domain": {
                    "name": "Polymarket CLOB",
                    "version": "1",
                    "chainId": self._chain_id,
                },
                "message": {
                    "market": order_payload["market"],
                    "side": order_payload["side"],
                    "outcome": order_payload["outcome"],
                    "price": int(order_payload["price"] * 100),
                    "size": int(order_payload["size"]),
                    "nonce": order_payload["nonce"],
                },
            }

            encoded = encode_structured_data(structured_data)
            signed = Account.sign_message(encoded, self._wallet_key)
            return signed.signature.hex()

        except ImportError:
            logger.warning("eth_account not installed. Order signing unavailable.")
            return ""
        except Exception as exc:
            logger.error("Order signing failed: %s", exc)
            return ""

    async def _retry_request(
        self, method: Any, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Execute HTTP request with retry logic."""
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await method(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 429:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning("Rate limited, retrying in %.1fs", backoff)
                    await asyncio.sleep(backoff)
                    continue
                if exc.response.status_code >= 500:
                    backoff = 0.5 * (2 ** attempt)
                    logger.warning("Server error, retrying in %.1fs", backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise

        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
