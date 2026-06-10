"""
Kalshi Broker — Prediction Market Execution
============================================
Integration with the Kalshi Trade API v2 for prediction market trading.
Supports market data, order management, position tracking, and account queries.

Adapted from the sim repo TypeScript tools (apps/sim/tools/kalshi/).
Converted to Python async patterns with proper type annotations.

Features:
    - Market discovery and search (markets, events, series)
    - Full order lifecycle (create, amend, cancel)
    - Position and fill tracking
    - Orderbook and candlestick data
    - RSA-PSS authenticated API requests
    - Account balance queries
    - Exchange status monitoring

Kalshi API Docs: https://docs.kalshi.com
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════


class KalshiMarket(BaseModel):
    """A prediction market on Kalshi."""

    ticker: str = ""
    event_ticker: str = ""
    market_type: str = ""
    title: str = ""
    subtitle: str = ""
    yes_sub_title: str = ""
    no_sub_title: str = ""
    open_time: str = ""
    close_time: str = ""
    expiration_time: str = ""
    status: str = ""
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    last_price: float = 0.0
    previous_yes_bid: float = 0.0
    previous_yes_ask: float = 0.0
    previous_price: float = 0.0
    volume: float = 0.0
    volume_24h: float = 0.0
    liquidity: float = 0.0
    open_interest: float = 0.0
    result: str = ""
    cap_strike: float = 0.0
    floor_strike: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiEvent(BaseModel):
    """An event containing one or more markets on Kalshi."""

    event_ticker: str = ""
    series_ticker: str = ""
    sub_title: str = ""
    title: str = ""
    mutually_exclusive: bool = False
    category: str = ""
    strike_date: str = ""
    status: str = ""
    markets: list[KalshiMarket] = Field(default_factory=list)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiSeries(BaseModel):
    """A series of related events on Kalshi."""

    ticker: str = ""
    title: str = ""
    frequency: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    settlement_sources: list[dict[str, str]] = Field(default_factory=list)
    contract_url: str = ""
    contract_terms_url: str = ""
    fee_type: str = ""
    fee_multiplier: float = 0.0
    additional_prohibitions: list[str] = Field(default_factory=list)
    product_metadata: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiBalance(BaseModel):
    """Account balance on Kalshi (amounts in cents)."""

    balance: int = 0
    portfolio_value: int = 0


class KalshiPosition(BaseModel):
    """Position in a Kalshi prediction market."""

    ticker: str = ""
    event_ticker: str = ""
    event_title: str = ""
    market_title: str = ""
    position: int = 0
    market_exposure: float = 0.0
    realized_pnl: float = 0.0
    total_traded: int = 0
    resting_orders_count: int = 0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiOrder(BaseModel):
    """Order placed on Kalshi."""

    order_id: str = ""
    ticker: str = ""
    event_ticker: str = ""
    status: str = ""
    side: str = ""
    type: str = ""
    yes_price: int = 0
    no_price: int = 0
    action: str = ""
    count: int = 0
    remaining_count: int = 0
    created_time: str = ""
    expiration_time: str = ""
    place_count: int = 0
    decrease_count: int = 0
    maker_fill_count: int = 0
    taker_fill_count: int = 0
    taker_fees: int = 0
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiOrderbookLevel(BaseModel):
    """A single price level in the orderbook."""

    price: int = 0
    quantity: int = 0


class KalshiOrderbook(BaseModel):
    """Orderbook data for a Kalshi market."""

    yes: list[KalshiOrderbookLevel] = Field(default_factory=list)
    no: list[KalshiOrderbookLevel] = Field(default_factory=list)


class KalshiTrade(BaseModel):
    """A trade executed on Kalshi."""

    ticker: str = ""
    yes_price: int = 0
    no_price: int = 0
    count: int = 0
    created_time: str = ""
    taker_side: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiCandlestick(BaseModel):
    """OHLCV candlestick data from Kalshi."""

    open_time: str = ""
    close_time: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


class KalshiFill(BaseModel):
    """A fill (execution) on Kalshi."""

    created_time: str = ""
    ticker: str = ""
    is_taker: bool = False
    side: str = ""
    yes_price: int = 0
    no_price: int = 0
    count: int = 0
    order_id: str = ""
    trade_id: str = ""
    raw_response: dict[str, Any] = Field(default_factory=dict)


class KalshiExchangeStatus(BaseModel):
    """Exchange status from Kalshi."""

    trading_active: bool = False
    exchange_active: bool = False


# ══════════════════════════════════════════════════════════════════════
# KALSHI BROKER
# ══════════════════════════════════════════════════════════════════════


class KalshiBroker:
    """
    Kalshi prediction market broker.

    Connects to the Kalshi Trade API v2 for order execution,
    market data, position management, and account queries.

    Uses RSA-PSS signature authentication as required by Kalshi.

    Args:
        api_key_id: Kalshi API Key ID
        private_key: RSA Private Key in PEM format
        base_url: Trade API base URL (default: production)
        max_retries: Maximum retry attempts on failures

    Example:
        broker = KalshiBroker(
            api_key_id="your-key-id",
            private_key="-----BEGIN RSA PRIVATE KEY-----\\n...",
        )
        markets = await broker.get_markets(status="open")
        order = await broker.create_order(
            ticker="KXBTC-24DEC31",
            side="yes",
            action="buy",
            count=10,
            yes_price=55,
        )
    """

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    DEMO_URL = "https://demo-api.kalshi.co/trade-api/v2"

    def __init__(
        self,
        api_key_id: str = "",
        private_key: str = "",
        base_url: str | None = None,
        demo: bool = False,
        max_retries: int = 3,
    ) -> None:
        self._api_key_id = api_key_id
        self._private_key = private_key
        self._base_url = base_url or (self.DEMO_URL if demo else self.BASE_URL)
        self._max_retries = max_retries

        self._http_client: httpx.AsyncClient | None = None

        if api_key_id and private_key:
            logger.info("Kalshi broker initialized with API credentials")
        else:
            logger.warning(
                "Kalshi broker initialized without API keys. "
                "Only public endpoints will work."
            )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    # ══════════════════════════════════════════════════════════════════
    # AUTHENTICATION
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _normalize_pem_key(private_key: str) -> str:
        """
        Normalize PEM key format.

        Handles: literal \\n strings, missing line breaks, various PEM formats.
        Adapted from sim repo kalshi/types.ts normalizePemKey().
        """
        key = private_key.strip()

        # Convert literal \n strings to actual newlines
        key = key.replace("\\n", "\n")

        # Extract key type and base64 content
        begin_match = re.search(r"-----BEGIN ([A-Z\s]+)-----", key)
        end_match = re.search(r"-----END ([A-Z\s]+)-----", key)

        if begin_match and end_match:
            key_type = begin_match.group(1).strip()

            # Extract base64 content between headers
            start_idx = key.index("-----", key.index("-----") + 5) + 5
            end_idx = key.rindex("-----END")
            base64_content = key[start_idx:end_idx]

            # Remove all whitespace from base64
            base64_content = re.sub(r"\s", "", base64_content)

            # Reconstruct with 64-char line breaks
            lines = [
                base64_content[i : i + 64]
                for i in range(0, len(base64_content), 64)
            ]

            return f"-----BEGIN {key_type}-----\n{''.join(lines)}\n-----END {key_type}-----"

        # No PEM headers — assume raw base64, wrap in PKCS#8
        clean_key = re.sub(r"\s", "", key)
        lines = [clean_key[i : i + 64] for i in range(0, len(clean_key), 64)]
        return f"-----BEGIN PRIVATE KEY-----\n{''.join(lines)}\n-----END PRIVATE KEY-----"

    def _generate_signature(
        self, timestamp: str, method: str, path: str
    ) -> str:
        """
        Generate RSA-PSS signature for authenticated Kalshi requests.

        Kalshi requires RSA-PSS with SHA256 (not PKCS#1 v1.5).
        Signs: timestamp + METHOD + path (without query params).

        Adapted from sim repo kalshi/types.ts generateKalshiSignature().
        """
        # Strip query params from path for signing
        path_without_query = path.split("?")[0]
        message = f"{timestamp}{method.upper()}{path_without_query}"

        # Normalize PEM key
        pem_key = self._normalize_pem_key(self._private_key)

        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding, utils

            private_key_obj = serialization.load_pem_private_key(
                pem_key.encode(), password=None
            )
            signature = private_key_obj.sign(
                message.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except ImportError:
            logger.warning(
                "cryptography package not installed. "
                "Kalshi authenticated requests will fail. "
                "Install with: pip install cryptography"
            )
            return ""
        except Exception as exc:
            logger.error("Kalshi signature generation failed: %s", exc)
            return ""

    def _build_auth_headers(
        self, method: str, path: str
    ) -> dict[str, str]:
        """Build authentication headers for Kalshi API requests."""
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, method, path)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if signature:
            headers["KALSHI-ACCESS-KEY"] = self._api_key_id
            headers["KALSHI-ACCESS-TIMESTAMP"] = timestamp
            headers["KALSHI-ACCESS-SIGNATURE"] = signature
        return headers

    # ══════════════════════════════════════════════════════════════════
    # MARKET DISCOVERY
    # ══════════════════════════════════════════════════════════════════

    async def get_markets(
        self,
        status: str | None = None,
        series_ticker: str | None = None,
        event_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiMarket]:
        """
        Retrieve a list of markets from Kalshi.

        Args:
            status: Filter by status (unopened, open, closed, settled)
            series_ticker: Filter by series ticker
            event_ticker: Filter by event ticker
            limit: Number of results (1-1000, default 100)
            cursor: Pagination cursor

        Returns:
            List of KalshiMarket objects
        """
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if cursor:
            params["cursor"] = cursor

        data = await self._public_request("GET", "/markets", params=params)

        markets = []
        for item in data.get("markets", []):
            markets.append(KalshiMarket(
                ticker=item.get("ticker", ""),
                event_ticker=item.get("event_ticker", ""),
                market_type=item.get("market_type", ""),
                title=item.get("title", ""),
                subtitle=item.get("subtitle", ""),
                yes_sub_title=item.get("yes_sub_title", ""),
                no_sub_title=item.get("no_sub_title", ""),
                open_time=item.get("open_time", ""),
                close_time=item.get("close_time", ""),
                expiration_time=item.get("expiration_time", ""),
                status=item.get("status", ""),
                yes_bid=float(item.get("yes_bid", 0)),
                yes_ask=float(item.get("yes_ask", 0)),
                no_bid=float(item.get("no_bid", 0)),
                no_ask=float(item.get("no_ask", 0)),
                last_price=float(item.get("last_price", 0)),
                previous_yes_bid=float(item.get("previous_yes_bid", 0)),
                previous_yes_ask=float(item.get("previous_yes_ask", 0)),
                previous_price=float(item.get("previous_price", 0)),
                volume=float(item.get("volume", 0)),
                volume_24h=float(item.get("volume_24h", 0)),
                liquidity=float(item.get("liquidity", 0)),
                open_interest=float(item.get("open_interest", 0)),
                result=item.get("result", ""),
                cap_strike=float(item.get("cap_strike", 0)),
                floor_strike=float(item.get("floor_strike", 0)),
                raw_response=item,
            ))

        logger.info("Retrieved %d Kalshi markets", len(markets))
        return markets

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        """
        Get a specific market by ticker.

        Args:
            ticker: Market ticker (e.g., KXBTC-24DEC31)

        Returns:
            KalshiMarket or None if not found
        """
        try:
            data = await self._public_request("GET", f"/markets/{ticker}")
            market_data = data.get("market", data)

            return KalshiMarket(
                ticker=market_data.get("ticker", ticker),
                event_ticker=market_data.get("event_ticker", ""),
                market_type=market_data.get("market_type", ""),
                title=market_data.get("title", ""),
                status=market_data.get("status", ""),
                yes_bid=float(market_data.get("yes_bid", 0)),
                yes_ask=float(market_data.get("yes_ask", 0)),
                no_bid=float(market_data.get("no_bid", 0)),
                no_ask=float(market_data.get("no_ask", 0)),
                last_price=float(market_data.get("last_price", 0)),
                volume=float(market_data.get("volume", 0)),
                volume_24h=float(market_data.get("volume_24h", 0)),
                liquidity=float(market_data.get("liquidity", 0)),
                open_interest=float(market_data.get("open_interest", 0)),
                raw_response=market_data,
            )
        except Exception as exc:
            logger.error("Get Kalshi market %s failed: %s", ticker, exc)
            return None

    async def get_events(
        self,
        status: str | None = None,
        series_ticker: str | None = None,
        with_nested_markets: bool = False,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiEvent]:
        """
        Retrieve a list of events from Kalshi.

        Args:
            status: Filter by status
            series_ticker: Filter by series ticker
            with_nested_markets: Include markets within each event
            limit: Number of results (1-1000)
            cursor: Pagination cursor

        Returns:
            List of KalshiEvent objects
        """
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if with_nested_markets:
            params["with_nested_markets"] = "true"
        if cursor:
            params["cursor"] = cursor

        data = await self._public_request("GET", "/events", params=params)

        events = []
        for item in data.get("events", []):
            event = KalshiEvent(
                event_ticker=item.get("event_ticker", ""),
                series_ticker=item.get("series_ticker", ""),
                sub_title=item.get("sub_title", ""),
                title=item.get("title", ""),
                mutually_exclusive=item.get("mutually_exclusive", False),
                category=item.get("category", ""),
                strike_date=item.get("strike_date", ""),
                status=item.get("status", ""),
                raw_response=item,
            )
            if with_nested_markets and "markets" in item:
                for m in item["markets"]:
                    event.markets.append(KalshiMarket(
                        ticker=m.get("ticker", ""),
                        title=m.get("title", ""),
                        status=m.get("status", ""),
                        raw_response=m,
                    ))
            events.append(event)

        logger.info("Retrieved %d Kalshi events", len(events))
        return events

    async def get_event(self, event_ticker: str) -> KalshiEvent | None:
        """
        Get a specific event by ticker.

        Args:
            event_ticker: Event ticker

        Returns:
            KalshiEvent or None if not found
        """
        try:
            data = await self._public_request(
                "GET", f"/events/{event_ticker}"
            )
            event_data = data.get("event", data)

            return KalshiEvent(
                event_ticker=event_data.get("event_ticker", event_ticker),
                series_ticker=event_data.get("series_ticker", ""),
                title=event_data.get("title", ""),
                category=event_data.get("category", ""),
                status=event_data.get("status", ""),
                raw_response=event_data,
            )
        except Exception as exc:
            logger.error("Get Kalshi event %s failed: %s", event_ticker, exc)
            return None

    async def get_series_by_ticker(
        self, series_ticker: str
    ) -> KalshiSeries | None:
        """
        Get a specific series by ticker.

        Args:
            series_ticker: Series ticker

        Returns:
            KalshiSeries or None if not found
        """
        try:
            data = await self._public_request(
                "GET", f"/series/{series_ticker}"
            )
            series_data = data.get("series", data)

            return KalshiSeries(
                ticker=series_data.get("ticker", series_ticker),
                title=series_data.get("title", ""),
                frequency=series_data.get("frequency", ""),
                category=series_data.get("category", ""),
                tags=series_data.get("tags", []),
                fee_type=series_data.get("fee_type", ""),
                fee_multiplier=float(series_data.get("fee_multiplier", 0)),
                raw_response=series_data,
            )
        except Exception as exc:
            logger.error("Get Kalshi series %s failed: %s", series_ticker, exc)
            return None

    async def get_exchange_status(self) -> KalshiExchangeStatus:
        """
        Get the current exchange status.

        Returns:
            KalshiExchangeStatus with trading/exchange active flags
        """
        try:
            data = await self._public_request("GET", "/exchange/status")
            return KalshiExchangeStatus(
                trading_active=data.get("trading_active", False),
                exchange_active=data.get("exchange_active", False),
            )
        except Exception as exc:
            logger.error("Get Kalshi exchange status failed: %s", exc)
            return KalshiExchangeStatus()

    # ══════════════════════════════════════════════════════════════════
    # MARKET DATA
    # ══════════════════════════════════════════════════════════════════

    async def get_orderbook(self, ticker: str) -> KalshiOrderbook:
        """
        Get the order book for a specific market.

        Args:
            ticker: Market ticker

        Returns:
            KalshiOrderbook with bid/ask levels
        """
        data = await self._public_request(
            "GET", f"/markets/{ticker}/orderbook"
        )

        yes_levels = [
            KalshiOrderbookLevel(
                price=int(k), quantity=int(v)
            )
            for k, v in data.get("yes", []).items()
        ] if isinstance(data.get("yes"), dict) else [
            KalshiOrderbookLevel(
                price=level.get("price", 0),
                quantity=level.get("quantity", 0),
            )
            for level in data.get("yes", [])
        ]

        no_levels = [
            KalshiOrderbookLevel(
                price=int(k), quantity=int(v)
            )
            for k, v in data.get("no", []).items()
        ] if isinstance(data.get("no"), dict) else [
            KalshiOrderbookLevel(
                price=level.get("price", 0),
                quantity=level.get("quantity", 0),
            )
            for level in data.get("no", [])
        ]

        return KalshiOrderbook(yes=yes_levels, no=no_levels)

    async def get_trades(
        self,
        ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiTrade]:
        """
        Get recent trades.

        Args:
            ticker: Filter by market ticker
            limit: Number of results
            cursor: Pagination cursor

        Returns:
            List of KalshiTrade objects
        """
        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if cursor:
            params["cursor"] = cursor

        data = await self._public_request("GET", "/trades", params=params)

        trades = []
        for item in data.get("trades", []):
            trades.append(KalshiTrade(
                ticker=item.get("ticker", ""),
                yes_price=int(item.get("yes_price", 0)),
                no_price=int(item.get("no_price", 0)),
                count=int(item.get("count", 0)),
                created_time=item.get("created_time", ""),
                taker_side=item.get("taker_side", ""),
                raw_response=item,
            ))
        return trades

    async def get_candlesticks(
        self,
        series_ticker: str,
        ticker: str,
        start_ts: int,
        end_ts: int,
        period_interval: int = 60,
    ) -> list[KalshiCandlestick]:
        """
        Get candlestick (OHLCV) data for a market.

        Args:
            series_ticker: Series ticker
            ticker: Market ticker
            start_ts: Start timestamp (Unix seconds)
            end_ts: End timestamp (Unix seconds)
            period_interval: Candle period in minutes (1, 60, 1440)

        Returns:
            List of KalshiCandlestick objects
        """
        params = {
            "series_ticker": series_ticker,
            "ticker": ticker,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "period_interval": period_interval,
        }

        data = await self._public_request(
            "GET", "/markets/candlesticks", params=params
        )

        candles = []
        for item in data.get("candlesticks", []):
            candles.append(KalshiCandlestick(
                open_time=str(item.get("open_time", "")),
                close_time=str(item.get("close_time", "")),
                open=float(item.get("open", 0)),
                high=float(item.get("high", 0)),
                low=float(item.get("low", 0)),
                close=float(item.get("close", 0)),
                volume=float(item.get("volume", 0)),
            ))
        return candles

    # ══════════════════════════════════════════════════════════════════
    # ACCOUNT & AUTHENTICATED QUERIES
    # ══════════════════════════════════════════════════════════════════

    async def get_balance(self) -> KalshiBalance:
        """
        Get account balance and portfolio value.

        Returns:
            KalshiBalance with balance and portfolio_value (in cents)
        """
        self._require_auth()
        data = await self._authenticated_request("GET", "/portfolio/balance")

        return KalshiBalance(
            balance=int(data.get("balance", 0)),
            portfolio_value=int(data.get("portfolio_value", 0)),
        )

    async def get_positions(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        settlement_status: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiPosition]:
        """
        Get current positions.

        Args:
            ticker: Filter by market ticker
            event_ticker: Filter by event ticker
            settlement_status: Filter by settlement status (unsettled, settled)
            limit: Number of results
            cursor: Pagination cursor

        Returns:
            List of KalshiPosition objects
        """
        self._require_auth()

        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if settlement_status:
            params["settlement_status"] = settlement_status
        if cursor:
            params["cursor"] = cursor

        data = await self._authenticated_request(
            "GET", "/portfolio/positions", params=params
        )

        positions = []
        for item in data.get("positions", []):
            positions.append(KalshiPosition(
                ticker=item.get("ticker", ""),
                event_ticker=item.get("event_ticker", ""),
                event_title=item.get("event_title", ""),
                market_title=item.get("market_title", ""),
                position=int(item.get("position", 0)),
                market_exposure=float(item.get("market_exposure", 0)),
                realized_pnl=float(item.get("realized_pnl", 0)),
                total_traded=int(item.get("total_traded", 0)),
                resting_orders_count=int(item.get("resting_orders_count", 0)),
                raw_response=item,
            ))
        return positions

    async def get_orders(
        self,
        ticker: str | None = None,
        event_ticker: str | None = None,
        status: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiOrder]:
        """
        Get orders.

        Args:
            ticker: Filter by market ticker
            event_ticker: Filter by event ticker
            status: Filter by status (resting, canceled, executed)
            limit: Number of results
            cursor: Pagination cursor

        Returns:
            List of KalshiOrder objects
        """
        self._require_auth()

        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor

        data = await self._authenticated_request(
            "GET", "/portfolio/orders", params=params
        )

        orders = []
        for item in data.get("orders", []):
            orders.append(self._parse_order(item))
        return orders

    async def get_order(self, order_id: str) -> KalshiOrder | None:
        """
        Get a specific order by ID.

        Args:
            order_id: The order ID

        Returns:
            KalshiOrder or None if not found
        """
        self._require_auth()

        try:
            data = await self._authenticated_request(
                "GET", f"/portfolio/orders/{order_id}"
            )
            order_data = data.get("order", data)
            return self._parse_order(order_data)
        except Exception as exc:
            logger.error("Get Kalshi order %s failed: %s", order_id, exc)
            return None

    async def get_fills(
        self,
        ticker: str | None = None,
        order_id: str | None = None,
        min_ts: int | None = None,
        max_ts: int | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiFill]:
        """
        Get fill (execution) history.

        Args:
            ticker: Filter by market ticker
            order_id: Filter by order ID
            min_ts: Minimum timestamp (Unix milliseconds)
            max_ts: Maximum timestamp (Unix milliseconds)
            limit: Number of results
            cursor: Pagination cursor

        Returns:
            List of KalshiFill objects
        """
        self._require_auth()

        params: dict[str, Any] = {"limit": min(limit, 1000)}
        if ticker:
            params["ticker"] = ticker
        if order_id:
            params["order_id"] = order_id
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts
        if cursor:
            params["cursor"] = cursor

        data = await self._authenticated_request(
            "GET", "/portfolio/fills", params=params
        )

        fills = []
        for item in data.get("fills", []):
            fills.append(KalshiFill(
                created_time=item.get("created_time", ""),
                ticker=item.get("ticker", ""),
                is_taker=item.get("is_taker", False),
                side=item.get("side", ""),
                yes_price=int(item.get("yes_price", 0)),
                no_price=int(item.get("no_price", 0)),
                count=int(item.get("count", 0)),
                order_id=item.get("order_id", ""),
                trade_id=item.get("trade_id", ""),
                raw_response=item,
            ))
        return fills

    # ══════════════════════════════════════════════════════════════════
    # ORDER EXECUTION
    # ══════════════════════════════════════════════════════════════════

    async def create_order(
        self,
        ticker: str,
        side: Literal["yes", "no"],
        action: Literal["buy", "sell"],
        count: int,
        order_type: Literal["limit", "market"] = "limit",
        yes_price: int | None = None,
        no_price: int | None = None,
        yes_price_dollars: str | None = None,
        no_price_dollars: str | None = None,
        client_order_id: str | None = None,
        expiration_ts: int | None = None,
        time_in_force: Literal[
            "fill_or_kill", "good_till_canceled", "immediate_or_cancel"
        ] = "good_till_canceled",
        buy_max_cost: int | None = None,
        post_only: bool = False,
        reduce_only: bool = False,
        self_trade_prevention_type: Literal["taker_at_cross", "maker"] | None = None,
        order_group_id: str | None = None,
    ) -> KalshiOrder:
        """
        Create a new order on a Kalshi prediction market.

        Args:
            ticker: Market ticker (e.g., KXBTC-24DEC31)
            side: Side of order ('yes' or 'no')
            action: Action type ('buy' or 'sell')
            count: Number of contracts (minimum 1)
            order_type: 'limit' or 'market' (default: limit)
            yes_price: Yes price in cents (1-99)
            no_price: No price in cents (1-99)
            yes_price_dollars: Yes price in dollars (e.g., "0.56")
            no_price_dollars: No price in dollars (e.g., "0.56")
            client_order_id: Custom order identifier
            expiration_ts: Unix timestamp for order expiration
            time_in_force: Time in force policy
            buy_max_cost: Maximum cost in cents
            post_only: Maker-only order
            reduce_only: Position reduction only
            self_trade_prevention_type: Self-trade prevention mode
            order_group_id: Associated order group ID

        Returns:
            KalshiOrder with submission details
        """
        self._require_auth()

        if count < 1:
            return KalshiOrder(
                ticker=ticker, side=side, action=action, count=count,
                status="REJECTED",
                raw_response={"error": "Count must be >= 1"},
            )

        body: dict[str, Any] = {
            "ticker": ticker,
            "side": side.lower(),
            "action": action.lower(),
            "count": count,
        }

        if order_type:
            body["type"] = order_type.lower()
        if yes_price is not None:
            body["yes_price"] = yes_price
        if no_price is not None:
            body["no_price"] = no_price
        if yes_price_dollars:
            body["yes_price_dollars"] = yes_price_dollars
        if no_price_dollars:
            body["no_price_dollars"] = no_price_dollars
        if client_order_id:
            body["client_order_id"] = client_order_id
        if expiration_ts:
            body["expiration_ts"] = expiration_ts
        if time_in_force:
            body["time_in_force"] = time_in_force
        if buy_max_cost:
            body["buy_max_cost"] = buy_max_cost
        if post_only:
            body["post_only"] = True
        if reduce_only:
            body["reduce_only"] = True
        if self_trade_prevention_type:
            body["self_trade_prevention_type"] = self_trade_prevention_type
        if order_group_id:
            body["order_group_id"] = order_group_id

        try:
            data = await self._authenticated_request(
                "POST", "/portfolio/orders", json=body
            )
            order_data = data.get("order", data)

            logger.info(
                "Kalshi order created: %s %s %s x%d (id=%s)",
                action.upper(), side.upper(), ticker, count,
                order_data.get("order_id", "N/A")[:8],
            )

            return self._parse_order(order_data)

        except Exception as exc:
            logger.error("Kalshi create order failed: %s", exc)
            return KalshiOrder(
                ticker=ticker, side=side, action=action, count=count,
                status="REJECTED",
                raw_response={"error": str(exc)},
            )

    async def cancel_order(self, order_id: str) -> KalshiOrder:
        """
        Cancel an existing order.

        Args:
            order_id: The order ID to cancel

        Returns:
            KalshiOrder with cancellation details
        """
        self._require_auth()

        try:
            data = await self._authenticated_request(
                "DELETE", f"/portfolio/orders/{order_id}"
            )
            order_data = data.get("order", data)

            logger.info("Kalshi order cancelled: %s", order_id[:8])
            return self._parse_order(order_data)

        except Exception as exc:
            logger.error("Kalshi cancel order %s failed: %s", order_id[:8], exc)
            return KalshiOrder(
                order_id=order_id, status="CANCEL_FAILED",
                raw_response={"error": str(exc)},
            )

    async def amend_order(
        self,
        order_id: str,
        ticker: str,
        side: Literal["yes", "no"],
        action: Literal["buy", "sell"],
        client_order_id: str,
        updated_client_order_id: str,
        count: int | None = None,
        yes_price: int | None = None,
        no_price: int | None = None,
        yes_price_dollars: str | None = None,
        no_price_dollars: str | None = None,
    ) -> KalshiOrder:
        """
        Amend an existing order's price or quantity.

        Args:
            order_id: Order ID to amend
            ticker: Market ticker
            side: Side of order ('yes' or 'no')
            action: Action type ('buy' or 'sell')
            client_order_id: Original client order ID
            updated_client_order_id: New client order ID
            count: Updated quantity (optional)
            yes_price: Updated yes price in cents (optional)
            no_price: Updated no price in cents (optional)
            yes_price_dollars: Updated yes price in dollars (optional)
            no_price_dollars: Updated no price in dollars (optional)

        Returns:
            KalshiOrder with amendment details
        """
        self._require_auth()

        body: dict[str, Any] = {
            "ticker": ticker,
            "side": side.lower(),
            "action": action.lower(),
            "client_order_id": client_order_id,
            "updated_client_order_id": updated_client_order_id,
        }

        if count is not None:
            body["count"] = count
        if yes_price is not None:
            body["yes_price"] = yes_price
        if no_price is not None:
            body["no_price"] = no_price
        if yes_price_dollars:
            body["yes_price_dollars"] = yes_price_dollars
        if no_price_dollars:
            body["no_price_dollars"] = no_price_dollars

        try:
            data = await self._authenticated_request(
                "POST", f"/portfolio/orders/{order_id}/amend", json=body
            )
            order_data = data.get("order", data)

            logger.info("Kalshi order amended: %s", order_id[:8])
            return self._parse_order(order_data)

        except Exception as exc:
            logger.error("Kalshi amend order %s failed: %s", order_id[:8], exc)
            return KalshiOrder(
                order_id=order_id, ticker=ticker, side=side, action=action,
                status="AMEND_FAILED",
                raw_response={"error": str(exc)},
            )

    # ══════════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════

    def _require_auth(self) -> None:
        """Raise if API credentials are not configured."""
        if not self._api_key_id or not self._private_key:
            raise ValueError(
                "Kalshi API credentials required for this operation. "
                "Provide api_key_id and private_key."
            )

    @staticmethod
    def _parse_order(item: dict[str, Any]) -> KalshiOrder:
        """Parse an order from API response."""
        return KalshiOrder(
            order_id=item.get("order_id", ""),
            ticker=item.get("ticker", ""),
            event_ticker=item.get("event_ticker", ""),
            status=item.get("status", ""),
            side=item.get("side", ""),
            type=item.get("type", ""),
            yes_price=int(item.get("yes_price", 0)),
            no_price=int(item.get("no_price", 0)),
            action=item.get("action", ""),
            count=int(item.get("count", 0)),
            remaining_count=int(item.get("remaining_count", 0)),
            created_time=item.get("created_time", ""),
            expiration_time=item.get("expiration_time", ""),
            place_count=int(item.get("place_count", 0)),
            decrease_count=int(item.get("decrease_count", 0)),
            maker_fill_count=int(item.get("maker_fill_count", 0)),
            taker_fill_count=int(item.get("taker_fill_count", 0)),
            taker_fees=int(item.get("taker_fees", 0)),
            raw_response=item,
        )

    async def _public_request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an unauthenticated API request."""
        client = await self._get_http_client()
        url = f"{self._base_url}{path}"

        response = await self._retry_request(
            client.request, method, url, params=params,
        )
        return response.json() if response else {}

    async def _authenticated_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request with RSA-PSS signature."""
        client = await self._get_http_client()

        api_path = f"/trade-api/v2{path}"
        headers = self._build_auth_headers(method, api_path)
        url = f"{self._base_url}{path}"

        response = await self._retry_request(
            client.request, method, url,
            params=params, json=json, headers=headers,
        )
        return response.json() if response else {}

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
