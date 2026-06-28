"""Comprehensive tests for the Polymarket Broker.

All tests use mocked HTTP responses — no real API calls.

Tests cover:
- PolymarketMarket, PolymarketOrderResult, PolymarketWalletConfig models
- PolymarketCLOBClient HTTP methods and headers
- PolymarketBroker initialization and config
- Connection lifecycle
- Market browsing methods
- Account / balance / positions / portfolio
- Order placement, cancellation, retrieval
- Market data (ticker, orderbook, trades, OHLCV)
- JSON output mode
- Internal helpers
- Error handling
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from quant_nanggroe.exchange.polymarket_broker import (
    PolymarketBroker,
    PolymarketCLOBClient,
    PolymarketMarket,
    PolymarketOrderResult,
    PolymarketWalletConfig,
)
from quant_nanggroe.exchange.base import (
    ExchangeConfig,
    ExchangeState,
    ConnectionError,
    OrderError,
    MarketDataError,
)
from quant_nanggroe.types.orders import OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import PositionSide


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def poly_config():
    """Create an ExchangeConfig for Polymarket."""
    return ExchangeConfig(
        exchange_id="polymarket",
        api_key="<placeholder>",
        api_secret="0xdeadbeef",
        sandbox=True,
        options={
            "wallet_address": "0xABC",
            "poly_api_key": "cpk1",
            "poly_api_passphrase": "pass1",
            "poly_api_secret": "cs1",
        },
    )


@pytest.fixture
def poly_broker(poly_config):
    """Create a PolymarketBroker instance."""
    return PolymarketBroker(poly_config)


@pytest.fixture
def connected_broker(poly_broker):
    """Create a connected PolymarketBroker with mocked CLOB client."""
    poly_broker._state = ExchangeState.CONNECTED
    mock_client = AsyncMock(spec=PolymarketCLOBClient)
    poly_broker._clob_client = mock_client
    return poly_broker


# ======================================================================
# 1. PolymarketWalletConfig
# ======================================================================

class TestPolymarketWalletConfig:
    """Tests for PolymarketWalletConfig model validation."""

    def test_default_values(self):
        wc = PolymarketWalletConfig()
        assert wc.private_key is None
        assert wc.address is None
        assert wc.chain_id == 137
        assert wc.rpc_url == "https://polygon-rpc.com"

    def test_custom_values(self):
        wc = PolymarketWalletConfig(
            private_key="0xkey",
            address="0xAddr",
            chain_id=80001,
            rpc_url="https://rpc-mumbai.maticvigil.com",
        )
        assert wc.private_key == "0xkey"
        assert wc.address == "0xAddr"
        assert wc.chain_id == 80001

    def test_serialization_round_trip(self):
        wc = PolymarketWalletConfig(private_key="0xkey", address="0xAddr")
        data = wc.model_dump()
        wc2 = PolymarketWalletConfig(**data)
        assert wc2.private_key == wc.private_key
        assert wc2.chain_id == wc.chain_id


# ======================================================================
# 2. PolymarketMarket Model
# ======================================================================

class TestPolymarketMarket:
    """Tests for PolymarketMarket model validation."""

    def test_required_field(self):
        m = PolymarketMarket(condition_id="cond-123")
        assert m.condition_id == "cond-123"

    def test_default_values(self):
        m = PolymarketMarket(condition_id="c1")
        assert m.question == ""
        assert m.outcomes == []
        assert m.outcome_prices == []
        assert m.active is True
        assert m.closed is False
        assert m.volume == 0.0
        assert m.liquidity == 0.0
        assert m.end_date_iso is None
        assert m.tokens == []
        assert m.minimum_order_size == 0.50
        assert m.minimum_tick_size == 0.01

    def test_custom_values(self):
        m = PolymarketMarket(
            condition_id="c2",
            question="Will it rain?",
            outcomes=["Yes", "No"],
            outcome_prices=[0.65, 0.35],
            active=True,
            volume=100000.0,
        )
        assert m.question == "Will it rain?"
        assert m.outcomes == ["Yes", "No"]
        assert m.outcome_prices == [0.65, 0.35]

    def test_missing_condition_id_rejected(self):
        with pytest.raises(ValidationError):
            PolymarketMarket()

    def test_serialization_round_trip(self):
        m = PolymarketMarket(condition_id="c3", question="Test", volume=500)
        data = m.model_dump()
        m2 = PolymarketMarket(**data)
        assert m2.condition_id == m.condition_id
        assert m2.volume == m.volume


# ======================================================================
# 3. PolymarketOrderResult Model
# ======================================================================

class TestPolymarketOrderResult:
    """Tests for PolymarketOrderResult model validation."""

    def test_default_values(self):
        r = PolymarketOrderResult()
        assert r.order_id == ""
        assert r.success is False
        assert r.transaction_hash is None
        assert r.error_message == ""

    def test_success_result(self):
        r = PolymarketOrderResult(
            order_id="ord-1",
            success=True,
            transaction_hash="0xtx",
        )
        assert r.success is True
        assert r.transaction_hash == "0xtx"

    def test_failure_result(self):
        r = PolymarketOrderResult(
            order_id="ord-2",
            success=False,
            error_message="Insufficient funds",
        )
        assert r.error_message == "Insufficient funds"


# ======================================================================
# 4. PolymarketCLOBClient
# ======================================================================

class TestPolymarketCLOBClient:
    """Tests for the low-level CLOB HTTP client."""

    def test_default_initialization(self):
        client = PolymarketCLOBClient()
        assert client._base_url == PolymarketCLOBClient.PRODUCTION_URL
        assert client._api_key is None
        assert client._http_client is None

    def test_custom_initialization(self):
        wc = PolymarketWalletConfig(private_key="0xkey")
        client = PolymarketCLOBClient(
            base_url=PolymarketCLOBClient.STAGING_URL,
            wallet_config=wc,
            api_key="<placeholder>",
            api_creds={"api_key": "ck1"},
        )
        assert client._base_url == PolymarketCLOBClient.STAGING_URL
        assert client._wallet_config.private_key == "0xkey"
        assert client._api_key == "my-key"

    def test_build_headers_no_auth(self):
        client = PolymarketCLOBClient()
        headers = client._build_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
        assert "POLY_API_KEY" not in headers

    def test_build_headers_with_api_key(self):
        client = PolymarketCLOBClient(api_key="<placeholder>")
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer bearer-token"

    def test_build_headers_with_api_creds(self):
        client = PolymarketCLOBClient(
            api_creds={"api_key": "ck", "api_passphrase": "cp"},
        )
        headers = client._build_headers()
        assert headers["POLY_API_KEY"] == "ck"
        assert headers["POLY_PASSPHRASE"] == "cp"

    @pytest.mark.asyncio
    async def test_get_raises_exchange_error(self):
        client = PolymarketCLOBClient()
        mock_http = AsyncMock()
        mock_http.get.side_effect = Exception("Network error")
        client._http_client = mock_http
        with pytest.raises(Exception):
            await client.get("/markets")

    @pytest.mark.asyncio
    async def test_post_raises_exchange_error(self):
        client = PolymarketCLOBClient()
        mock_http = AsyncMock()
        mock_http.post.side_effect = Exception("Network error")
        client._http_client = mock_http
        with pytest.raises(Exception):
            await client.post("/order", {})

    @pytest.mark.asyncio
    async def test_delete_raises_exchange_error(self):
        client = PolymarketCLOBClient()
        mock_http = AsyncMock()
        mock_http.delete.side_effect = Exception("Network error")
        client._http_client = mock_http
        with pytest.raises(Exception):
            await client.delete("/order/1")

    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        client = PolymarketCLOBClient()
        mock_http = AsyncMock()
        client._http_client = mock_http
        await client.close()
        mock_http.aclose.assert_called_once()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self):
        client = PolymarketCLOBClient()
        await client.close()  # Should not raise
        assert client._http_client is None


# ======================================================================
# 5. PolymarketBroker Initialization
# ======================================================================

class TestPolymarketBrokerInit:
    """Tests for PolymarketBroker initialization and properties."""

    def test_initial_state(self, poly_broker):
        assert poly_broker.is_connected is False
        assert poly_broker.state == ExchangeState.DISCONNECTED
        assert poly_broker.name == "polymarket"

    def test_repr(self, poly_broker):
        result = repr(poly_broker)
        assert "PolymarketBroker" in result
        assert "disconnected" in result

    def test_internal_state_empty(self, poly_broker):
        assert poly_broker._local_orders == {}
        assert poly_broker._local_positions == {}
        assert poly_broker._markets_cache == {}
        assert poly_broker._ws_tasks == {}


# ======================================================================
# 6. Connection Lifecycle
# ======================================================================

class TestPolymarketBrokerConnection:
    """Tests for connection lifecycle."""

    @pytest.mark.asyncio
    async def test_operations_require_connection(self, poly_broker):
        with pytest.raises(ConnectionError):
            await poly_broker.get_balance()

    @pytest.mark.asyncio
    async def test_browse_markets_requires_connection(self, poly_broker):
        with pytest.raises(ConnectionError):
            await poly_broker.browse_markets()

    @pytest.mark.asyncio
    async def test_place_order_requires_connection(self, poly_broker):
        with pytest.raises(ConnectionError):
            await poly_broker.place_order("BTC", OrderSide.BUY, OrderType.MARKET, 10)

    @pytest.mark.asyncio
    async def test_connect_sandbox_uses_staging(self, poly_broker):
        """Sandbox config should use staging URL."""
        with patch.object(PolymarketCLOBClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}
            await poly_broker.connect()
            assert poly_broker._clob_client._base_url == PolymarketCLOBClient.STAGING_URL

    @pytest.mark.asyncio
    async def test_connect_production_url(self):
        """Non-sandbox config should use production URL."""
        config = ExchangeConfig(exchange_id="polymarket", sandbox=False)
        broker = PolymarketBroker(config)
        with patch.object(PolymarketCLOBClient, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {}
            await broker.connect()
            assert broker._clob_client._base_url == PolymarketCLOBClient.PRODUCTION_URL

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, connected_broker):
        result = await connected_broker.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_broker):
        await connected_broker.disconnect()
        assert connected_broker.state == ExchangeState.DISCONNECTED
        assert connected_broker._clob_client is None

    @pytest.mark.asyncio
    async def test_disconnect_cancels_ws_tasks(self, poly_broker):
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        poly_broker._ws_tasks["test"] = mock_task
        await poly_broker.disconnect()
        mock_task.cancel.assert_called_once()
        assert poly_broker._ws_tasks == {}


# ======================================================================
# 7. Market Browsing
# ======================================================================

class TestPolymarketBrokerMarketBrowsing:
    """Tests for market browsing methods."""

    @pytest.mark.asyncio
    async def test_browse_markets_list_response(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {
                "condition_id": "c1",
                "question": "Will X happen?",
                "outcomes": "Yes,No",
                "outcomePrices": "0.6,0.4",
                "active": True,
                "volume": 50000,
                "liquidity": 10000,
            },
        ]
        markets = await connected_broker.browse_markets()
        assert len(markets) == 1
        assert markets[0].condition_id == "c1"
        assert markets[0].question == "Will X happen?"
        assert markets[0].outcomes == ["Yes", "No"]
        assert markets[0].outcome_prices == [0.6, 0.4]

    @pytest.mark.asyncio
    async def test_browse_markets_dict_response(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "data": [
                {"condition_id": "c2", "question": "Test?"},
            ]
        }
        markets = await connected_broker.browse_markets()
        assert len(markets) == 1
        assert markets[0].condition_id == "c2"

    @pytest.mark.asyncio
    async def test_browse_markets_caches(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {"condition_id": "c3"},
        ]
        await connected_broker.browse_markets()
        assert "c3" in connected_broker._markets_cache

    @pytest.mark.asyncio
    async def test_browse_markets_with_params(self, connected_broker):
        connected_broker._clob_client.get.return_value = []
        await connected_broker.browse_markets(query="election", tag="politics", active_only=True)
        call_args = connected_broker._clob_client.get.call_args
        params = call_args[1].get("params") or call_args[0][1] if len(call_args[0]) > 1 else {}
        assert params.get("query") == "election" or "query" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_market(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "condition_id": "c10",
            "question": "Special market?",
            "outcomes": ["Yes", "No"],
            "outcomePrices": [0.7, 0.3],
        }
        market = await connected_broker.get_market("c10")
        assert market.condition_id == "c10"
        assert market.question == "Special market?"

    @pytest.mark.asyncio
    async def test_get_markets(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {"condition_id": "c1"},
            {"condition_id": "c2"},
        ]
        ids = await connected_broker.get_markets()
        assert "c1" in ids
        assert "c2" in ids

    @pytest.mark.asyncio
    async def test_get_markets_fallback_to_cache(self, connected_broker):
        connected_broker._clob_client.get.side_effect = Exception("fail")
        connected_broker._markets_cache = {"c1": PolymarketMarket(condition_id="c1")}
        ids = await connected_broker.get_markets()
        assert ids == ["c1"]


# ======================================================================
# 8. Account / Balance / Positions
# ======================================================================

class TestPolymarketBrokerAccount:
    """Tests for account, balance, positions, and portfolio."""

    @pytest.mark.asyncio
    async def test_get_balance(self, connected_broker):
        connected_broker._clob_client.get.return_value = {"USDC": 5000, "value": 7500}
        bal = await connected_broker.get_balance()
        assert bal["USDC"] == 5000
        assert bal["total_value"] == 7500

    @pytest.mark.asyncio
    async def test_get_balance_error_returns_zero(self, connected_broker):
        connected_broker._clob_client.get.side_effect = Exception("fail")
        bal = await connected_broker.get_balance()
        assert bal["USDC"] == 0.0
        assert bal["total_value"] == 0.0

    @pytest.mark.asyncio
    async def test_get_positions(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {
                "condition_id": "c1",
                "size": 100,
                "avgPrice": 0.5,
                "curPrice": 0.6,
            },
        ]
        positions = await connected_broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "c1"
        assert positions[0].side == PositionSide.LONG
        assert positions[0].quantity == 100
        assert positions[0].entry_price == 0.5
        assert positions[0].current_price == 0.6

    @pytest.mark.asyncio
    async def test_get_positions_zero_size_skipped(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {"condition_id": "c1", "size": 0, "avgPrice": 0, "curPrice": 0},
        ]
        positions = await connected_broker.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_get_positions_short_side(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {"condition_id": "c2", "size": -50, "avgPrice": 0.5, "curPrice": 0.4},
        ]
        positions = await connected_broker.get_positions()
        assert positions[0].side == PositionSide.SHORT

    @pytest.mark.asyncio
    async def test_get_positions_dict_response(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "positions": [
                {"condition_id": "c3", "size": 20, "avgPrice": 0.3, "curPrice": 0.35},
            ]
        }
        positions = await connected_broker.get_positions()
        assert len(positions) == 1

    @pytest.mark.asyncio
    async def test_get_portfolio(self, connected_broker):
        connected_broker._clob_client.get.return_value = {"USDC": 1000, "value": 1000}
        # Mock get_balance and get_positions
        with patch.object(connected_broker, "get_balance", new_callable=AsyncMock) as mock_bal, \
             patch.object(connected_broker, "get_positions", new_callable=AsyncMock) as mock_pos:
            mock_bal.return_value = {"USDC": 1000.0, "total_value": 1000.0}
            mock_pos.return_value = []
            portfolio = await connected_broker.get_portfolio()
            assert portfolio.name == "polymarket"
            assert portfolio.currency == "USDC"


# ======================================================================
# 9. Order Placement
# ======================================================================

class TestPolymarketBrokerOrders:
    """Tests for order placement, cancellation, retrieval."""

    @pytest.mark.asyncio
    async def test_place_market_order(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-1",
            "status": "LIVE",
            "size_matched": 50,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=50,
        )
        assert order.id == "ord-1"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.SUBMITTED
        assert order.broker_id == "polymarket"

    @pytest.mark.asyncio
    async def test_place_limit_order(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-2",
            "status": "LIVE",
            "size_matched": 0,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100,
            price=0.55,
        )
        assert order.price == 0.55

    @pytest.mark.asyncio
    async def test_place_limit_without_price_raises(self, connected_broker):
        with pytest.raises(OrderError, match="Limit price is required"):
            await connected_broker.place_order(
                symbol="c1",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
            )

    @pytest.mark.asyncio
    async def test_place_order_price_out_of_range(self, connected_broker):
        with pytest.raises(OrderError, match="Price must be between"):
            await connected_broker.place_order(
                symbol="c1",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=1.50,
            )

    @pytest.mark.asyncio
    async def test_place_order_price_below_min(self, connected_broker):
        with pytest.raises(OrderError, match="Price must be between"):
            await connected_broker.place_order(
                symbol="c1",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=0.005,
            )

    @pytest.mark.asyncio
    async def test_place_order_sell_side(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-3",
            "status": "LIVE",
            "size_matched": 0,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=30,
        )
        assert order.side == OrderSide.SELL

    @pytest.mark.asyncio
    async def test_place_order_stored_locally(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-4",
            "status": "LIVE",
            "size_matched": 0,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        assert "ord-4" in connected_broker._local_orders

    @pytest.mark.asyncio
    async def test_place_order_filled_status(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-5",
            "status": "FILLED",
            "size_matched": 100,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=100,
        )
        assert order.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_place_order_cancelled_status(self, connected_broker):
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-6",
            "status": "CANCELLED",
            "size_matched": 0,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        assert order.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_order_existing(self, connected_broker):
        # Place order first
        connected_broker._local_orders["ord-1"] = MagicMock(
            id="ord-1", status=OrderStatus.SUBMITTED,
        )
        connected_broker._clob_client.delete.return_value = {}
        order = await connected_broker.cancel_order("ord-1")
        assert order.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_order_not_local(self, connected_broker):
        """Cancel order not in local cache — broker creates order with quantity=0 which fails validation."""
        connected_broker._clob_client.delete.return_value = {}
        with pytest.raises(OrderError):
            await connected_broker.cancel_order("ord-999", symbol="c1")

    @pytest.mark.asyncio
    async def test_get_order(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "status": "LIVE",
            "side": "BUY",
            "asset_id": "c1",
            "original_size": 100,
            "price": 0.55,
            "size_matched": 50,
            "client_order_id": "cli-1",
        }
        order = await connected_broker.get_order("ord-1")
        assert order.id == "ord-1"
        assert order.side == OrderSide.BUY
        assert order.quantity == 100.0

    @pytest.mark.asyncio
    async def test_get_order_matched_status(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "status": "MATCHED",
            "side": "BUY",
            "asset_id": "c1",
            "original_size": 100,
            "price": 0.55,
            "size_matched": 50,
        }
        order = await connected_broker.get_order("ord-1")
        assert order.status == OrderStatus.PARTIALLY_FILLED

    @pytest.mark.asyncio
    async def test_place_order_with_market_cache(self, connected_broker):
        connected_broker._markets_cache["c1"] = PolymarketMarket(
            condition_id="c1",
            tokens=[
                {"token_id": "token-yes"},
                {"token_id": "token-no"},
            ],
        )
        connected_broker._clob_client.post.return_value = {
            "orderID": "ord-7",
            "status": "LIVE",
            "size_matched": 0,
        }
        order = await connected_broker.place_order(
            symbol="c1",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10,
        )
        assert order.id == "ord-7"


# ======================================================================
# 10. Market Data
# ======================================================================

class TestPolymarketBrokerMarketData:
    """Tests for market data methods."""

    @pytest.mark.asyncio
    async def test_get_ohlcv_returns_empty(self, connected_broker):
        result = await connected_broker.get_ohlcv("c1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_ticker(self, connected_broker):
        connected_broker._clob_client.get.return_value = {"price": 0.65}
        ticker = await connected_broker.get_ticker("c1")
        assert ticker.symbol == "c1"
        assert ticker.last_price == 0.65

    @pytest.mark.asyncio
    async def test_get_orderbook(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "bids": [{"price": "0.55", "size": "100"}],
            "asks": [{"price": "0.60", "size": "200"}],
        }
        book = await connected_broker.get_orderbook("c1")
        assert book.symbol == "c1"
        assert len(book.bids) == 1
        assert len(book.asks) == 1
        assert book.bids[0].price == 0.55
        assert book.asks[0].price == 0.60

    @pytest.mark.asyncio
    async def test_get_orderbook_empty(self, connected_broker):
        connected_broker._clob_client.get.return_value = {"bids": [], "asks": []}
        book = await connected_broker.get_orderbook("c1")
        assert len(book.bids) == 0
        assert len(book.asks) == 0

    @pytest.mark.asyncio
    async def test_get_trades(self, connected_broker):
        connected_broker._clob_client.get.return_value = [
            {"id": "t1", "price": "0.55", "size": "100", "side": "BUY", "timestamp": "2024-01-01"},
        ]
        trades = await connected_broker.get_trades("c1")
        assert len(trades) == 1
        assert trades[0]["price"] == 0.55

    @pytest.mark.asyncio
    async def test_get_trades_dict_response(self, connected_broker):
        connected_broker._clob_client.get.return_value = {
            "trades": [
                {"id": "t2", "price": "0.50", "size": "50", "side": "SELL", "timestamp": ""},
            ]
        }
        trades = await connected_broker.get_trades("c1")
        assert len(trades) == 1


# ======================================================================
# 11. Health Check & WebSocket Stubs
# ======================================================================

class TestPolymarketBrokerHealthAndWS:
    """Tests for health check and WebSocket stubs."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, connected_broker):
        connected_broker._clob_client.get.return_value = {}
        result = await connected_broker.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, connected_broker):
        connected_broker._clob_client.get.side_effect = Exception("fail")
        result = await connected_broker.health_check()
        assert result is False
        assert connected_broker.state == ExchangeState.ERROR

    @pytest.mark.asyncio
    async def test_subscribe_ticker(self, connected_broker):
        await connected_broker.subscribe_ticker("c1", lambda d: None)

    @pytest.mark.asyncio
    async def test_subscribe_orderbook(self, connected_broker):
        await connected_broker.subscribe_orderbook("c1", lambda d: None)

    @pytest.mark.asyncio
    async def test_subscribe_trades(self, connected_broker):
        await connected_broker.subscribe_trades("c1", lambda d: None)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connected_broker):
        await connected_broker.unsubscribe("c1", "ticker")


# ======================================================================
# 12. JSON Output Mode
# ======================================================================

class TestPolymarketBrokerJSON:
    """Tests for JSON output mode."""

    @pytest.mark.asyncio
    async def test_to_json_pydantic_model(self, connected_broker):
        market = PolymarketMarket(condition_id="c1", question="Test?")
        result = await connected_broker.to_json(market)
        parsed = json.loads(result)
        assert parsed["condition_id"] == "c1"

    @pytest.mark.asyncio
    async def test_to_json_plain_dict(self, connected_broker):
        data = {"key": "value", "num": 42}
        result = await connected_broker.to_json(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    @pytest.mark.asyncio
    async def test_to_json_list(self, connected_broker):
        data = [1, 2, 3]
        result = await connected_broker.to_json(data)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]


# ======================================================================
# 13. Internal Helpers
# ======================================================================

class TestPolymarketBrokerHelpers:
    """Tests for internal helper methods."""

    def test_parse_outcome_prices_list(self):
        result = PolymarketBroker._parse_outcome_prices([0.6, 0.4])
        assert result == [0.6, 0.4]

    def test_parse_outcome_prices_string(self):
        result = PolymarketBroker._parse_outcome_prices("0.65, 0.35")
        assert result == [0.65, 0.35]

    def test_parse_outcome_prices_empty_string(self):
        result = PolymarketBroker._parse_outcome_prices("")
        assert result == []

    def test_parse_outcome_prices_none(self):
        result = PolymarketBroker._parse_outcome_prices(None)
        assert result == []

    def test_parse_outcome_prices_invalid_string(self):
        result = PolymarketBroker._parse_outcome_prices("not,valid")
        assert result == []

    def test_require_client_raises_when_disconnected(self, poly_broker):
        with pytest.raises(ConnectionError):
            poly_broker._require_client()
