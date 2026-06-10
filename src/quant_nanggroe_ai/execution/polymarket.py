"""
Polymarket Broker — Prediction Market Execution
================================================
Integration with the Polymarket CLOB (Central Limit Order Book) API
for prediction market trading. Supports buying/selling shares,
market discovery, and position management.

Features:
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
