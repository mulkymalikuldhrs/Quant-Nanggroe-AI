"""
Polymarket Broker — Prediction Market Execution
================================================
Integration with the Polymarket CLOB (Central Limit Order Book) API
for prediction market trading. Supports buying/selling shares,
market discovery, and position management.

Enhanced with features from the sim repo TypeScript tools and
polymarket-cli Rust reference (C2-CORE merge, Task 8-c):
    - Full Gamma API: events, markets, tags, series, search, profiles
    - Full CLOB API: orderbook, price, midpoint, spread, tick_size,
      price_history, batch queries, fee_rate, neg_risk, sampling markets
    - Full CLOB Auth: orders, trades, balance/allowance, notifications,
      rewards, API key management, account status, market orders
    - Full Data API: positions, trades, closed positions, value,
      activity, holders, open interest, volume, leaderboards
    - Bridge API: deposit addresses, supported assets, deposit status
    - Market discovery and search
    - Buy/sell shares with limit and market orders (GTC, GTD, FOK, FAK)
    - Position tracking and PnL
    - Order cancellation (single, batch, market, all)
    - CLOB API integration with rate limiting
    - Order signing via EIP-712 (Ethereum)
    - Signature types: EOA, Proxy, GnosisSafe

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


# ── New models from polymarket-cli Rust reference (Task 8-c) ────────


class PolymarketClobMarket(BaseModel):
    """CLOB market info (different structure from Gamma market)."""

    condition_id: str = ""
    question_id: str = ""
    tokens: list[dict[str, Any]] = Field(default_factory=list)
    minimum_order_size: float = 0.0
    minimum_tick_size: float = 0.01
    active: bool = True
    closed: bool = False
    archived: bool = False
    accepting_orders: bool = True
    neg_risk: bool = False
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketNotification(BaseModel):
    """A notification from the Polymarket CLOB."""

    id: str = ""
    type: str = ""
    title: str = ""
    body: str = ""
    read: bool = False
    created_at: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketOrderDetail(BaseModel):
    """Detailed order information from the CLOB."""

    id: str = ""
    market: str = ""
    asset_id: str = ""
    side: str = ""
    price: str = ""
    original_size: str = ""
    remaining_size: str = ""
    order_type: str = ""
    status: str = ""
    created_at: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketLeaderboardEntry(BaseModel):
    """A single entry on the Polymarket leaderboard."""

    rank: int = 0
    username: str = ""
    address: str = ""
    pnl: float = 0.0
    volume: float = 0.0
    trades: int = 0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketHolderInfo(BaseModel):
    """Top holder information for a market."""

    address: str = ""
    shares: str = ""
    size: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketOpenInterest(BaseModel):
    """Open interest data for a market."""

    condition_id: str = ""
    asset_id: str = ""
    open_interest: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketLiveVolume(BaseModel):
    """Live volume data for an event."""

    event_id: str = ""
    volume: str = ""
    liquidity: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketDepositAddress(BaseModel):
    """Deposit addresses for a Polymarket wallet."""

    evm_address: str = ""
    solana_address: str = ""
    bitcoin_address: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketProfile(BaseModel):
    """Public profile information for a Polymarket wallet."""

    address: str = ""
    username: str = ""
    bio: str = ""
    profile_image: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PolymarketRewardEarning(BaseModel):
    """Reward earning record from Polymarket."""

    market: str = ""
    earning: str = ""
    date: str = ""
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

    # ══════════════════════════════════════════════════════════════════
    # CLOB HEALTH & STATUS (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def check_health(self) -> bool:
        """
        Check CLOB API health.

        Ported from polymarket-cli clob ok command.

        Returns:
            True if CLOB API is healthy
        """
        client = await self._get_http_client()
        try:
            response = await client.get(f"{self.CLOB_URL}/ok")
            response.raise_for_status()
            return True
        except Exception as exc:
            logger.error("CLOB health check failed: %s", exc)
            return False

    async def get_server_time(self) -> str:
        """
        Get CLOB server time.

        Ported from polymarket-cli clob time command.

        Returns:
            Server time string
        """
        client = await self._get_http_client()
        try:
            response = await client.get(f"{self.CLOB_URL}/time")
            response.raise_for_status()
            data = response.json()
            return data.get("time", str(data)) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get server time failed: %s", exc)
            return ""

    async def check_geoblock(self) -> dict[str, Any]:
        """
        Check geoblock status.

        Ported from polymarket-cli clob geoblock command.

        Returns:
            Dict with geoblock status
        """
        client = await self._get_http_client()
        try:
            response = await client.get(f"{self.CLOB_URL}/geoblock")
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("Check geoblock failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # CLOB BATCH QUERIES (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_batch_prices(
        self, token_ids: list[str], side: str = "buy"
    ) -> list[dict[str, Any]]:
        """
        Get prices for multiple tokens at once.

        Ported from polymarket-cli clob batch-prices command.

        Args:
            token_ids: List of CLOB token IDs
            side: "buy" or "sell"

        Returns:
            List of price dicts, one per token
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/prices",
                params={"token_ids": ",".join(token_ids), "side": side},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else [data]
        except Exception as exc:
            logger.error("Get batch prices failed: %s", exc)
            return []

    async def get_midpoints(self, token_ids: list[str]) -> list[dict[str, Any]]:
        """
        Get midpoint prices for multiple tokens.

        Ported from polymarket-cli clob midpoints command.

        Args:
            token_ids: List of CLOB token IDs

        Returns:
            List of midpoint dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/midpoints",
                params={"token_ids": ",".join(token_ids)},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else [data]
        except Exception as exc:
            logger.error("Get midpoints failed: %s", exc)
            return []

    async def get_batch_orderbooks(
        self, token_ids: list[str]
    ) -> list[PolymarketOrderbook]:
        """
        Get order books for multiple tokens.

        Ported from polymarket-cli clob books command.

        Args:
            token_ids: List of CLOB token IDs

        Returns:
            List of PolymarketOrderbook objects
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/books",
                params={"token_ids": ",".join(token_ids)},
            )
            response.raise_for_status()
            data = response.json()
            books = data if isinstance(data, list) else [data]
            result = []
            for b in books:
                result.append(PolymarketOrderbook(
                    market=b.get("market", ""),
                    asset_id=b.get("asset_id", ""),
                    hash=b.get("hash", ""),
                    timestamp=b.get("timestamp", ""),
                    bids=[PolymarketOrderbookEntry(
                        price=x.get("price", ""), size=x.get("size", "")
                    ) for x in b.get("bids", [])],
                    asks=[PolymarketOrderbookEntry(
                        price=x.get("price", ""), size=x.get("size", "")
                    ) for x in b.get("asks", [])],
                ))
            return result
        except Exception as exc:
            logger.error("Get batch orderbooks failed: %s", exc)
            return []

    async def get_last_trades_prices(
        self, token_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Get last trade prices for multiple tokens.

        Ported from polymarket-cli clob last-trades command.

        Args:
            token_ids: List of CLOB token IDs

        Returns:
            List of price dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/last-trade-prices",
                params={"token_ids": ",".join(token_ids)},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else [data]
        except Exception as exc:
            logger.error("Get last trades prices failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # CLOB MARKET INFO (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_clob_market(self, condition_id: str) -> PolymarketClobMarket | None:
        """
        Get CLOB market info by condition ID.

        Different from Gamma market — includes CLOB-specific fields
        like accepting_orders, neg_risk, minimum_order_size.

        Ported from polymarket-cli clob market command.

        Args:
            condition_id: Market condition ID (0x-prefixed hex)

        Returns:
            PolymarketClobMarket or None
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/markets/{condition_id}"
            )
            response.raise_for_status()
            data = response.json()
            return PolymarketClobMarket(
                condition_id=data.get("condition_id", condition_id),
                question_id=data.get("question_id", ""),
                tokens=data.get("tokens", []),
                minimum_order_size=float(data.get("minimum_order_size", 0)),
                minimum_tick_size=float(data.get("minimum_tick_size", 0.01)),
                active=data.get("active", True),
                closed=data.get("closed", False),
                archived=data.get("archived", False),
                accepting_orders=data.get("accepting_orders", True),
                neg_risk=data.get("neg_risk", False),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Get CLOB market failed: %s", exc)
            return None

    async def get_clob_markets(
        self, cursor: str | None = None
    ) -> list[PolymarketClobMarket]:
        """
        List CLOB markets with optional pagination.

        Ported from polymarket-cli clob markets command.

        Args:
            cursor: Pagination cursor

        Returns:
            List of PolymarketClobMarket
        """
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await client.get(
                f"{self.CLOB_URL}/markets", params=params
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("data", data.get("markets", []))
            markets = []
            for m in items:
                markets.append(PolymarketClobMarket(
                    condition_id=m.get("condition_id", ""),
                    question_id=m.get("question_id", ""),
                    tokens=m.get("tokens", []),
                    minimum_order_size=float(m.get("minimum_order_size", 0)),
                    minimum_tick_size=float(m.get("minimum_tick_size", 0.01)),
                    active=m.get("active", True),
                    closed=m.get("closed", False),
                    neg_risk=m.get("neg_risk", False),
                    raw_response=m,
                ))
            return markets
        except Exception as exc:
            logger.error("Get CLOB markets failed: %s", exc)
            return []

    async def get_sampling_markets(
        self, cursor: str | None = None
    ) -> list[PolymarketClobMarket]:
        """
        List sampling markets (reward-eligible).

        Ported from polymarket-cli clob sampling-markets command.

        Args:
            cursor: Pagination cursor

        Returns:
            List of PolymarketClobMarket
        """
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await client.get(
                f"{self.CLOB_URL}/sampling-markets", params=params
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("data", [])
            return [
                PolymarketClobMarket(
                    condition_id=m.get("condition_id", ""),
                    neg_risk=m.get("neg_risk", False),
                    raw_response=m,
                )
                for m in items
            ]
        except Exception as exc:
            logger.error("Get sampling markets failed: %s", exc)
            return []

    async def get_simplified_markets(
        self, cursor: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List simplified markets (reduced detail for fast browsing).

        Ported from polymarket-cli clob simplified-markets command.

        Args:
            cursor: Pagination cursor

        Returns:
            List of simplified market dicts
        """
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await client.get(
                f"{self.CLOB_URL}/simplified-markets", params=params
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("data", [])
        except Exception as exc:
            logger.error("Get simplified markets failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # CLOB TOKEN METADATA (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_fee_rate(self, token_id: str) -> str:
        """
        Get the fee rate in basis points for a token.

        Ported from polymarket-cli clob fee-rate command.

        Args:
            token_id: CLOB token ID

        Returns:
            Fee rate in basis points as a string
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/fee-rate",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("fee_rate_bps", data)) if isinstance(data, dict) else str(data)
        except Exception as exc:
            logger.error("Get fee rate failed: %s", exc)
            return ""

    async def check_neg_risk(self, token_id: str) -> bool:
        """
        Check if a token is in a neg-risk market.

        Ported from polymarket-cli clob neg-risk command.

        Args:
            token_id: CLOB token ID

        Returns:
            True if neg-risk market
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/neg-risk",
                params={"token_id": token_id},
            )
            response.raise_for_status()
            data = response.json()
            return bool(data.get("neg_risk", False))
        except Exception as exc:
            logger.error("Check neg risk failed: %s", exc)
            return False

    # ══════════════════════════════════════════════════════════════════
    # AUTHENTICATED ORDER MANAGEMENT (from polymarket-cli Rust ref)
    # ══════════════════════════════════════════════════════════════════

    async def create_market_order(
        self,
        token_id: str,
        side: str,
        amount: float,
        order_type: str = "FOK",
    ) -> PolymarketOrder:
        """
        Create a market order (immediate execution).

        For BUY: amount is in USDC (cost of the order).
        For SELL: amount is in shares.

        Ported from polymarket-cli clob market-order command.

        Args:
            token_id: CLOB token ID
            side: "BUY" or "SELL"
            amount: USDC amount (for buys) or shares (for sells)
            order_type: "FOK" or "FAK"

        Returns:
            PolymarketOrder with submission details
        """
        if not self._api_key:
            return PolymarketOrder(
                market_id=token_id, side=side, outcome="",
                price=0.0, size=amount,
                status="REJECTED",
                raw_response={"error": "API credentials required"},
            )

        client = await self._get_http_client()

        payload: dict[str, Any] = {
            "token_id": token_id,
            "side": side.upper(),
            "order_type": order_type,
        }
        if side.upper() == "BUY":
            payload["amount"] = amount  # USDC for buys
        else:
            payload["size"] = amount  # shares for sells

        if self._wallet_key:
            try:
                signature = self._sign_order(payload)
                payload["signature"] = signature
            except Exception as exc:
                logger.warning("Market order signing failed: %s", exc)

        try:
            response = await self._retry_request(
                client.post,
                f"{self.CLOB_URL}/market-order",
                json=payload,
            )
            data = response.json() if response else {}
            return PolymarketOrder(
                order_id=data.get("orderID", data.get("id", "")),
                market_id=token_id,
                side=side,
                outcome="",
                price=float(data.get("price", 0)),
                size=float(data.get("size", amount)),
                order_type=order_type,
                status=data.get("status", "PENDING"),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Market order failed: %s", exc)
            return PolymarketOrder(
                market_id=token_id, side=side, outcome="",
                price=0.0, size=amount,
                status="REJECTED",
                raw_response={"error": str(exc)},
            )

    async def get_orders(
        self,
        market: str | None = None,
        asset_id: str | None = None,
        cursor: str | None = None,
    ) -> list[PolymarketOrderDetail]:
        """
        List open orders (authenticated).

        Ported from polymarket-cli clob orders command.

        Args:
            market: Filter by market condition ID
            asset_id: Filter by token/asset ID
            cursor: Pagination cursor

        Returns:
            List of PolymarketOrderDetail
        """
        if not self._api_key:
            logger.warning("API credentials required for orders")
            return []

        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if market:
            params["market"] = market
        if asset_id:
            params["asset_id"] = asset_id
        if cursor:
            params["cursor"] = cursor

        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/orders", params=params
            )
            data = response.json() if response else {}
            items = data if isinstance(data, list) else data.get("orders", [])
            return [
                PolymarketOrderDetail(
                    id=o.get("id", ""),
                    market=o.get("market", ""),
                    asset_id=o.get("asset_id", ""),
                    side=o.get("side", ""),
                    price=o.get("price", ""),
                    original_size=o.get("original_size", ""),
                    remaining_size=o.get("size", o.get("remaining_size", "")),
                    order_type=o.get("order_type", ""),
                    status=o.get("status", ""),
                    created_at=o.get("created_at", ""),
                    raw_response=o,
                )
                for o in items
            ]
        except Exception as exc:
            logger.error("Get orders failed: %s", exc)
            return []

    async def get_order(self, order_id: str) -> PolymarketOrderDetail | None:
        """
        Get a single order by ID (authenticated).

        Ported from polymarket-cli clob order command.

        Args:
            order_id: Order ID

        Returns:
            PolymarketOrderDetail or None
        """
        if not self._api_key:
            return None
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/order/{order_id}"
            )
            data = response.json() if response else {}
            return PolymarketOrderDetail(
                id=data.get("id", order_id),
                market=data.get("market", ""),
                asset_id=data.get("asset_id", ""),
                side=data.get("side", ""),
                price=data.get("price", ""),
                original_size=data.get("original_size", ""),
                remaining_size=data.get("size", data.get("remaining_size", "")),
                order_type=data.get("order_type", ""),
                status=data.get("status", ""),
                created_at=data.get("created_at", ""),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Get order failed: %s", exc)
            return None

    async def cancel_orders(self, order_ids: list[str]) -> dict[str, Any]:
        """
        Cancel multiple orders by IDs (authenticated).

        Ported from polymarket-cli clob cancel-orders command.

        Args:
            order_ids: List of order IDs to cancel

        Returns:
            Cancellation result dict
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.delete,
                f"{self.CLOB_URL}/orders",
                json={"ids": order_ids},
            )
            data = response.json() if response else {}
            logger.info("Cancelled %d orders", len(order_ids))
            return {"cancelled": order_ids, "data": data}
        except Exception as exc:
            logger.error("Cancel orders failed: %s", exc)
            return {"error": str(exc)}

    async def cancel_all_orders(self) -> dict[str, Any]:
        """
        Cancel all open orders (authenticated).

        Ported from polymarket-cli clob cancel-all command.

        Returns:
            Cancellation result dict
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.delete, f"{self.CLOB_URL}/cancel-all"
            )
            data = response.json() if response else {}
            logger.info("Cancelled all open orders")
            return {"status": "all_cancelled", "data": data}
        except Exception as exc:
            logger.error("Cancel all orders failed: %s", exc)
            return {"error": str(exc)}

    async def cancel_market_orders(
        self,
        market: str | None = None,
        asset_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Cancel orders for a specific market (authenticated).

        Ported from polymarket-cli clob cancel-market command.

        Args:
            market: Market condition ID
            asset_id: Token/asset ID

        Returns:
            Cancellation result dict
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if market:
            params["market"] = market
        if asset_id:
            params["asset_id"] = asset_id
        try:
            response = await self._retry_request(
                client.delete, f"{self.CLOB_URL}/cancel-market-orders",
                params=params,
            )
            data = response.json() if response else {}
            logger.info("Cancelled market orders: market=%s", market)
            return {"status": "cancelled", "data": data}
        except Exception as exc:
            logger.error("Cancel market orders failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # AUTHENTICATED TRADE & BALANCE (from polymarket-cli Rust ref)
    # ══════════════════════════════════════════════════════════════════

    async def get_authenticated_trades(
        self,
        market: str | None = None,
        asset_id: str | None = None,
        cursor: str | None = None,
    ) -> list[PolymarketTradeRecord]:
        """
        Get authenticated trade history (CLOB API).

        Ported from polymarket-cli clob trades command.

        Args:
            market: Filter by market condition ID
            asset_id: Filter by token ID
            cursor: Pagination cursor

        Returns:
            List of PolymarketTradeRecord
        """
        if not self._api_key:
            return []
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if market:
            params["market"] = market
        if asset_id:
            params["asset_id"] = asset_id
        if cursor:
            params["cursor"] = cursor
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/trades", params=params
            )
            data = response.json() if response else {}
            items = data if isinstance(data, list) else data.get("trades", [])
            return [
                PolymarketTradeRecord(
                    id=str(t.get("id", "")),
                    market=t.get("market", ""),
                    asset_id=t.get("asset_id", ""),
                    side=t.get("side", ""),
                    size=t.get("size", ""),
                    price=t.get("price", ""),
                    timestamp=t.get("timestamp", ""),
                    maker=t.get("maker", ""),
                    taker=t.get("taker", ""),
                    raw_response=t,
                )
                for t in items
            ]
        except Exception as exc:
            logger.error("Get authenticated trades failed: %s", exc)
            return []

    async def get_balance_allowance(
        self,
        asset_type: str = "collateral",
        token_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get balance and allowance (authenticated).

        Ported from polymarket-cli clob balance command.

        Args:
            asset_type: "collateral" or "conditional"
            token_id: Required for conditional assets

        Returns:
            Dict with balance and allowance info
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        params: dict[str, Any] = {"asset_type": asset_type}
        if token_id:
            params["token_id"] = token_id
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/balance-allowance", params=params
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Get balance/allowance failed: %s", exc)
            return {"error": str(exc)}

    async def update_balance_allowance(
        self,
        asset_type: str = "collateral",
        token_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Refresh balance allowance on-chain (authenticated).

        Ported from polymarket-cli clob update-balance command.

        Args:
            asset_type: "collateral" or "conditional"
            token_id: Required for conditional assets

        Returns:
            Dict with update result
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        payload: dict[str, Any] = {"asset_type": asset_type}
        if token_id:
            payload["token_id"] = token_id
        try:
            response = await self._retry_request(
                client.post, f"{self.CLOB_URL}/update-balance-allowance",
                json=payload,
            )
            data = response.json() if response else {}
            return {"success": True, "data": data}
        except Exception as exc:
            logger.error("Update balance/allowance failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # NOTIFICATIONS (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_notifications(self) -> list[PolymarketNotification]:
        """
        List notifications (authenticated).

        Ported from polymarket-cli clob notifications command.

        Returns:
            List of PolymarketNotification
        """
        if not self._api_key:
            return []
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/notifications"
            )
            data = response.json() if response else {}
            items = data if isinstance(data, list) else data.get("notifications", [])
            return [
                PolymarketNotification(
                    id=str(n.get("id", "")),
                    type=n.get("type", ""),
                    title=n.get("title", ""),
                    body=n.get("body", ""),
                    read=n.get("read", False),
                    created_at=n.get("created_at", ""),
                    raw_response=n,
                )
                for n in items
            ]
        except Exception as exc:
            logger.error("Get notifications failed: %s", exc)
            return []

    async def delete_notifications(
        self, notification_ids: list[str]
    ) -> dict[str, Any]:
        """
        Delete notifications by IDs (authenticated).

        Ported from polymarket-cli clob delete-notifications command.

        Args:
            notification_ids: List of notification IDs to delete

        Returns:
            Dict with deletion result
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.delete, f"{self.CLOB_URL}/notifications",
                json={"ids": notification_ids},
            )
            data = response.json() if response else {}
            return {"deleted": notification_ids, "data": data}
        except Exception as exc:
            logger.error("Delete notifications failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # REWARDS (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_reward_earnings(
        self, date: str, cursor: str | None = None
    ) -> list[PolymarketRewardEarning]:
        """
        Get reward earnings for a date (authenticated).

        Ported from polymarket-cli clob rewards command.

        Args:
            date: Date in YYYY-MM-DD format
            cursor: Pagination cursor

        Returns:
            List of PolymarketRewardEarning
        """
        if not self._api_key:
            return []
        client = await self._get_http_client()
        params: dict[str, Any] = {"date": date}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/rewards", params=params
            )
            data = response.json() if response else {}
            items = data if isinstance(data, list) else data.get("rewards", [])
            return [
                PolymarketRewardEarning(
                    market=r.get("market", ""),
                    earning=r.get("earning", ""),
                    date=r.get("date", date),
                    raw_response=r,
                )
                for r in items
            ]
        except Exception as exc:
            logger.error("Get reward earnings failed: %s", exc)
            return []

    async def get_total_earnings(self, date: str) -> dict[str, Any]:
        """
        Get total earnings for a date (authenticated).

        Ported from polymarket-cli clob earnings command.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Dict with total earnings
        """
        if not self._api_key:
            return {}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/earnings",
                params={"date": date},
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Get total earnings failed: %s", exc)
            return {}

    async def get_reward_percentages(self) -> dict[str, Any]:
        """
        Get reward percentages (authenticated).

        Ported from polymarket-cli clob reward-percentages command.

        Returns:
            Dict with reward percentages
        """
        if not self._api_key:
            return {}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/reward-percentages"
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Get reward percentages failed: %s", exc)
            return {}

    async def get_current_rewards(
        self, cursor: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List current reward programs (authenticated).

        Ported from polymarket-cli clob current-rewards command.

        Args:
            cursor: Pagination cursor

        Returns:
            List of reward program dicts
        """
        if not self._api_key:
            return []
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/current-rewards", params=params
            )
            data = response.json() if response else {}
            return data if isinstance(data, list) else data.get("rewards", [])
        except Exception as exc:
            logger.error("Get current rewards failed: %s", exc)
            return []

    async def get_market_reward(
        self, condition_id: str, cursor: str | None = None
    ) -> dict[str, Any]:
        """
        Get reward details for a market (authenticated).

        Ported from polymarket-cli clob market-reward command.

        Args:
            condition_id: Market condition ID
            cursor: Pagination cursor

        Returns:
            Dict with market reward details
        """
        if not self._api_key:
            return {}
        client = await self._get_http_client()
        params: dict[str, Any] = {}
        if cursor:
            params["cursor"] = cursor
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/markets/{condition_id}/rewards",
                params=params,
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Get market reward failed: %s", exc)
            return {}

    async def check_order_scoring(self, order_id: str) -> dict[str, Any]:
        """
        Check if an order is scoring rewards (authenticated).

        Ported from polymarket-cli clob order-scoring command.

        Args:
            order_id: Order ID

        Returns:
            Dict with scoring status
        """
        if not self._api_key:
            return {}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/order-scoring/{order_id}"
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Check order scoring failed: %s", exc)
            return {}

    # ══════════════════════════════════════════════════════════════════
    # ACCOUNT MANAGEMENT (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_api_keys(self) -> list[dict[str, Any]]:
        """
        List API keys (authenticated).

        Ported from polymarket-cli clob api-keys command.

        Returns:
            List of API key dicts
        """
        if not self._api_key:
            return []
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/api-keys"
            )
            data = response.json() if response else {}
            return data if isinstance(data, list) else data.get("api_keys", [])
        except Exception as exc:
            logger.error("Get API keys failed: %s", exc)
            return []

    async def delete_api_key(self) -> dict[str, Any]:
        """
        Delete current API key (authenticated).

        Ported from polymarket-cli clob delete-api-key command.

        Returns:
            Dict with deletion result
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.delete, f"{self.CLOB_URL}/api-key"
            )
            data = response.json() if response else {}
            return {"success": True, "data": data}
        except Exception as exc:
            logger.error("Delete API key failed: %s", exc)
            return {"error": str(exc)}

    async def create_api_key(self) -> dict[str, Any]:
        """
        Create or derive an API key (authenticated).

        Ported from polymarket-cli clob create-api-key command.

        Returns:
            Dict with new API key details
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.post, f"{self.CLOB_URL}/api-key"
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Create API key failed: %s", exc)
            return {"error": str(exc)}

    async def get_account_status(self) -> dict[str, Any]:
        """
        Check account status / closed-only mode (authenticated).

        Ported from polymarket-cli clob account-status command.

        Returns:
            Dict with account status info
        """
        if not self._api_key:
            return {"error": "API credentials required"}
        client = await self._get_http_client()
        try:
            response = await self._retry_request(
                client.get, f"{self.CLOB_URL}/closed-only-mode"
            )
            return response.json() if response else {}
        except Exception as exc:
            logger.error("Get account status failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # DATA API EXTENDED (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_closed_positions(
        self, address: str, limit: int = 25, offset: int = 0
    ) -> list[PolymarketPosition]:
        """
        Get closed positions for a wallet (Data API).

        Ported from polymarket-cli data closed-positions command.

        Args:
            address: Wallet address (0x...)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of PolymarketPosition
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/closed-positions",
                params={"user": address, "limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("positions", [])
            return [
                PolymarketPosition(
                    market_id=p.get("market", ""),
                    condition_id=p.get("asset_id", ""),
                    outcome="",
                    size=float(p.get("size", 0)),
                    avg_price=0.0,
                    current_price=float(p.get("curPrice", 0)),
                    pnl=float(p.get("pnl", 0)),
                )
                for p in items
            ]
        except Exception as exc:
            logger.error("Get closed positions failed: %s", exc)
            return []

    async def get_position_value(self, address: str) -> dict[str, Any]:
        """
        Get total position value for a wallet (Data API).

        Ported from polymarket-cli data value command.

        Args:
            address: Wallet address (0x...)

        Returns:
            Dict with position value info
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/value",
                params={"user": address},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("Get position value failed: %s", exc)
            return {}

    async def get_traded_count(self, address: str) -> dict[str, Any]:
        """
        Get count of unique markets traded by a wallet (Data API).

        Ported from polymarket-cli data traded command.

        Args:
            address: Wallet address (0x...)

        Returns:
            Dict with traded count
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/traded",
                params={"user": address},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("Get traded count failed: %s", exc)
            return {}

    async def get_activity(
        self, address: str, limit: int = 25, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get on-chain activity for a wallet (Data API).

        Ported from polymarket-cli data activity command.

        Args:
            address: Wallet address (0x...)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of activity dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/activity",
                params={"user": address, "limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("activity", [])
        except Exception as exc:
            logger.error("Get activity failed: %s", exc)
            return []

    async def get_holders(
        self, condition_id: str, limit: int = 10
    ) -> list[PolymarketHolderInfo]:
        """
        Get top token holders for a market (Data API).

        Ported from polymarket-cli data holders command.

        Args:
            condition_id: Market condition ID (0x...)
            limit: Max results per token

        Returns:
            List of PolymarketHolderInfo
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/holders",
                params={"markets": condition_id, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("holders", [])
            return [
                PolymarketHolderInfo(
                    address=h.get("address", ""),
                    shares=h.get("shares", ""),
                    size=float(h.get("size", 0)),
                    raw_response=h,
                )
                for h in items
            ]
        except Exception as exc:
            logger.error("Get holders failed: %s", exc)
            return []

    async def get_open_interest(
        self, condition_id: str
    ) -> list[PolymarketOpenInterest]:
        """
        Get open interest for markets (Data API).

        Ported from polymarket-cli data open-interest command.

        Args:
            condition_id: Market condition ID (0x...)

        Returns:
            List of PolymarketOpenInterest
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/open-interest",
                params={"markets": condition_id},
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("open_interest", [])
            return [
                PolymarketOpenInterest(
                    condition_id=oi.get("condition_id", ""),
                    asset_id=oi.get("asset_id", ""),
                    open_interest=oi.get("open_interest", ""),
                    raw_response=oi,
                )
                for oi in items
            ]
        except Exception as exc:
            logger.error("Get open interest failed: %s", exc)
            return []

    async def get_live_volume(self, event_id: int) -> PolymarketLiveVolume | None:
        """
        Get live volume for an event (Data API).

        Ported from polymarket-cli data volume command.

        Args:
            event_id: Event ID

        Returns:
            PolymarketLiveVolume or None
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/live-volume",
                params={"id": event_id},
            )
            response.raise_for_status()
            data = response.json()
            return PolymarketLiveVolume(
                event_id=str(data.get("id", event_id)),
                volume=data.get("volume", ""),
                liquidity=data.get("liquidity", ""),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Get live volume failed: %s", exc)
            return None

    async def get_leaderboard(
        self,
        period: str = "all",
        order_by: str = "pnl",
        limit: int = 25,
        offset: int = 0,
    ) -> list[PolymarketLeaderboardEntry]:
        """
        Get trader leaderboard (Data API).

        Ported from polymarket-cli data leaderboard command.

        Args:
            period: "day", "week", "month", or "all"
            order_by: "pnl" or "vol"
            limit: Max results
            offset: Pagination offset

        Returns:
            List of PolymarketLeaderboardEntry
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/leaderboard",
                params={
                    "time_period": period,
                    "order_by": order_by,
                    "limit": limit,
                    "offset": offset,
                },
            )
            response.raise_for_status()
            data = response.json()
            items = data if isinstance(data, list) else data.get("leaderboard", [])
            return [
                PolymarketLeaderboardEntry(
                    rank=int(e.get("rank", 0)),
                    username=e.get("username", ""),
                    address=e.get("address", ""),
                    pnl=float(e.get("pnl", 0)),
                    volume=float(e.get("vol", 0)),
                    trades=int(e.get("trades", 0)),
                    raw_response=e,
                )
                for e in items
            ]
        except Exception as exc:
            logger.error("Get leaderboard failed: %s", exc)
            return []

    async def get_builder_leaderboard(
        self, period: str = "all", limit: int = 25, offset: int = 0
    ) -> list[dict[str, Any]]:
        """
        Get builder leaderboard (Data API).

        Ported from polymarket-cli data builder-leaderboard command.

        Args:
            period: "day", "week", "month", or "all"
            limit: Max results
            offset: Pagination offset

        Returns:
            List of builder leaderboard entry dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/builder-leaderboard",
                params={"time_period": period, "limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("leaderboard", [])
        except Exception as exc:
            logger.error("Get builder leaderboard failed: %s", exc)
            return []

    async def get_builder_volume(
        self, period: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Get builder volume time-series (Data API).

        Ported from polymarket-cli data builder-volume command.

        Args:
            period: "day", "week", "month", or "all"

        Returns:
            List of volume time-series dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.DATA_URL}/builder-volume",
                params={"time_period": period},
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("volume", [])
        except Exception as exc:
            logger.error("Get builder volume failed: %s", exc)
            return []

    # ══════════════════════════════════════════════════════════════════
    # BRIDGE API (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_deposit_addresses(self, address: str) -> PolymarketDepositAddress | None:
        """
        Get deposit addresses for a wallet (Bridge API).

        Ported from polymarket-cli bridge deposit command.

        Args:
            address: Polymarket wallet address (0x...)

        Returns:
            PolymarketDepositAddress or None
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/bridge/deposit",
                params={"address": address},
            )
            response.raise_for_status()
            data = response.json()
            return PolymarketDepositAddress(
                evm_address=data.get("evm_address", data.get("address", "")),
                solana_address=data.get("solana_address", ""),
                bitcoin_address=data.get("bitcoin_address", ""),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Get deposit addresses failed: %s", exc)
            return None

    async def get_supported_assets(self) -> list[dict[str, Any]]:
        """
        List supported chains and tokens for deposits (Bridge API).

        Ported from polymarket-cli bridge supported-assets command.

        Returns:
            List of supported asset dicts
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/bridge/supported-assets"
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("assets", [])
        except Exception as exc:
            logger.error("Get supported assets failed: %s", exc)
            return []

    async def get_deposit_status(self, address: str) -> dict[str, Any]:
        """
        Check deposit transaction status (Bridge API).

        Ported from polymarket-cli bridge status command.

        Args:
            address: Deposit address (EVM, Solana, or Bitcoin)

        Returns:
            Dict with deposit status
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.CLOB_URL}/bridge/status",
                params={"address": address},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error("Get deposit status failed: %s", exc)
            return {"error": str(exc)}

    # ══════════════════════════════════════════════════════════════════
    # PROFILES (from polymarket-cli Rust reference)
    # ══════════════════════════════════════════════════════════════════

    async def get_profile(self, address: str) -> PolymarketProfile | None:
        """
        Get public profile for a wallet (Gamma API).

        Ported from polymarket-cli profiles get command.

        Args:
            address: Wallet address (0x...)

        Returns:
            PolymarketProfile or None
        """
        client = await self._get_http_client()
        try:
            response = await client.get(
                f"{self.GAMMA_URL}/profiles",
                params={"address": address},
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                data = data[0]
            elif isinstance(data, dict) and "profiles" in data:
                data = data["profiles"][0] if data["profiles"] else {}
            return PolymarketProfile(
                address=data.get("address", address),
                username=data.get("username", ""),
                bio=data.get("bio", ""),
                profile_image=data.get("profile_image", ""),
                raw_response=data,
            )
        except Exception as exc:
            logger.error("Get profile failed: %s", exc)
            return None

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════
