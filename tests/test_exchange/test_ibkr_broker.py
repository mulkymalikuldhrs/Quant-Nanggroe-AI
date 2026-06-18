"""Comprehensive tests for the IBKR Broker.

All tests use mocked ib_insync module — no real IBKR calls.

Tests cover:
- IBKRContract, IBKRAccountSummary, IBKRExecutionReport models
- IBKRBroker initialization and config
- Connection lifecycle
- Contract lookup
- Account summary and balance
- Positions and portfolio
- Order placement (market, limit, stop, stop-limit)
- Order cancellation and retrieval
- Execution reports
- Market data (OHLCV, ticker, orderbook, trades)
- Status and timeframe mapping
- Health check and markets listing
- Error handling when IBKR not available
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from quant_nanggroe.exchange.ibkr_broker import (
    IBKRBroker,
    IBKRContract,
    IBKRAccountSummary,
    IBKRExecutionReport,
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
from quant_nanggroe.types.market import TimeFrame


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def ibkr_config():
    """Create an ExchangeConfig for IBKR."""
    return ExchangeConfig(
        exchange_id="ibkr",
        sandbox=True,
        options={"host": "127.0.0.1", "port": 7497, "client_id": 1},
    )


@pytest.fixture
def ibkr_broker(ibkr_config):
    """Create an IBKRBroker instance."""
    return IBKRBroker(ibkr_config)


def _make_mock_ib():
    """Create a comprehensive mock ib_insync.IB instance."""
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.connectAsync = AsyncMock()
    ib.disconnect.return_value = None
    ib.managedAccounts.return_value = ["U1234567"]
    ib.accountSummaryAsync = AsyncMock()
    ib.positions.return_value = []
    ib.openTrades.return_value = []
    ib.fills.return_value = []
    ib.placeOrder.return_value = MagicMock()
    ib.cancelOrder.return_value = None
    ib.reqMktData.return_value = MagicMock()
    ib.ticker.return_value = MagicMock()
    ib.reqHistoricalDataAsync = AsyncMock()
    return ib


@pytest.fixture
def mock_ib():
    return _make_mock_ib()


@pytest.fixture
def connected_broker(ibkr_broker, mock_ib):
    """Create a connected IBKRBroker with mocked IB instance."""
    ibkr_broker._ib = mock_ib
    ibkr_broker._state = ExchangeState.CONNECTED
    return ibkr_broker


@pytest.fixture
def mock_ib_insync():
    """Create a mock ib_insync module with Stock, Contract, Order, util, ExecutionFilter."""
    mod = MagicMock()
    mod.Stock = MagicMock(return_value=MagicMock())
    mod.Contract = MagicMock(return_value=MagicMock())
    mod.Order = MagicMock
    mod.util = MagicMock()
    mod.ExecutionFilter = MagicMock(return_value=MagicMock())
    return mod


# ======================================================================
# 1. IBKRContract Model
# ======================================================================

class TestIBKRContract:
    """Tests for IBKRContract model validation."""

    def test_required_field(self):
        c = IBKRContract(symbol="AAPL")
        assert c.symbol == "AAPL"

    def test_default_values(self):
        c = IBKRContract(symbol="AAPL")
        assert c.sec_type == "STK"
        assert c.exchange == "SMART"
        assert c.currency == "USD"
        assert c.expiry is None
        assert c.strike is None
        assert c.right is None
        assert c.multiplier is None
        assert c.con_id is None

    def test_custom_values(self):
        c = IBKRContract(
            symbol="SPY",
            sec_type="OPT",
            exchange="CBOE",
            currency="USD",
            expiry="20241220",
            strike=500.0,
            right="CALL",
            multiplier="100",
            con_id=12345,
        )
        assert c.sec_type == "OPT"
        assert c.strike == 500.0
        assert c.right == "CALL"
        assert c.multiplier == "100"

    def test_missing_symbol_rejected(self):
        with pytest.raises(ValidationError):
            IBKRContract()

    def test_serialization_round_trip(self):
        c = IBKRContract(symbol="AAPL", sec_type="STK")
        data = c.model_dump()
        c2 = IBKRContract(**data)
        assert c2.symbol == c.symbol
        assert c2.sec_type == c.sec_type


# ======================================================================
# 2. IBKRAccountSummary Model
# ======================================================================

class TestIBKRAccountSummary:
    """Tests for IBKRAccountSummary model validation."""

    def test_default_values(self):
        s = IBKRAccountSummary()
        assert s.account_id == ""
        assert s.net_liquidation == 0.0
        assert s.buying_power == 0.0
        assert s.unrealized_pnl == 0.0
        assert s.currency == "USD"

    def test_custom_values(self):
        s = IBKRAccountSummary(
            account_id="U1234567",
            net_liquidation=100000.0,
            buying_power=200000.0,
            available_funds=50000.0,
        )
        assert s.account_id == "U1234567"
        assert s.net_liquidation == 100000.0

    def test_serialization_round_trip(self):
        s = IBKRAccountSummary(account_id="U1", net_liquidation=50000)
        data = s.model_dump()
        s2 = IBKRAccountSummary(**data)
        assert s2.account_id == s.account_id


# ======================================================================
# 3. IBKRExecutionReport Model
# ======================================================================

class TestIBKRExecutionReport:
    """Tests for IBKRExecutionReport model validation."""

    def test_default_values(self):
        r = IBKRExecutionReport()
        assert r.exec_id == ""
        assert r.order_id == 0
        assert r.shares == 0.0
        assert r.price == 0.0
        assert r.commission == 0.0
        assert r.commission_currency == "USD"

    def test_custom_values(self):
        r = IBKRExecutionReport(
            exec_id="exec-1",
            order_id=123,
            symbol="AAPL",
            side="BOT",
            shares=100.0,
            price=150.50,
            commission=1.0,
        )
        assert r.exec_id == "exec-1"
        assert r.shares == 100.0
        assert r.price == 150.50


# ======================================================================
# 4. IBKRBroker Initialization
# ======================================================================

class TestIBKRBrokerInit:
    """Tests for IBKRBroker initialization and properties."""

    def test_initial_state(self, ibkr_broker):
        assert ibkr_broker.is_connected is False
        assert ibkr_broker.state == ExchangeState.DISCONNECTED
        assert ibkr_broker.name == "ibkr"

    def test_repr(self, ibkr_broker):
        result = repr(ibkr_broker)
        assert "IBKRBroker" in result
        assert "disconnected" in result

    def test_internal_state_empty(self, ibkr_broker):
        assert ibkr_broker._local_orders == {}
        assert ibkr_broker._local_positions == {}
        assert ibkr_broker._execution_reports == {}


# ======================================================================
# 5. Connection Lifecycle
# ======================================================================

class TestIBKRBrokerConnection:
    """Tests for connection lifecycle."""

    @pytest.mark.asyncio
    async def test_operations_require_connection(self, ibkr_broker):
        with pytest.raises(ConnectionError):
            await ibkr_broker.get_balance()

    @pytest.mark.asyncio
    async def test_connect_without_ib_insync_raises(self, ibkr_broker):
        ibkr_broker._state = ExchangeState.DISCONNECTED
        with patch.dict("sys.modules", {"ib_insync": None}):
            with pytest.raises((ImportError, Exception)):
                await ibkr_broker.connect()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, connected_broker):
        result = await connected_broker.connect()
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_broker, mock_ib):
        await connected_broker.disconnect()
        assert connected_broker.state == ExchangeState.DISCONNECTED
        mock_ib.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_error_handled(self, connected_broker, mock_ib):
        mock_ib.disconnect.side_effect = RuntimeError("disconnect error")
        await connected_broker.disconnect()
        assert connected_broker.state == ExchangeState.DISCONNECTED

    def test_is_connected_true(self, connected_broker, mock_ib):
        mock_ib.isConnected.return_value = True
        assert connected_broker.is_connected is True

    def test_is_connected_false(self, ibkr_broker):
        assert ibkr_broker.is_connected is False

    def test_is_connected_exception(self, connected_broker, mock_ib):
        mock_ib.isConnected.side_effect = Exception("error")
        assert connected_broker.is_connected is False


# ======================================================================
# 6. Status Mapping
# ======================================================================

class TestIBKRStatusMapping:
    """Tests for IBKR status → OrderStatus mapping."""

    def test_submitted(self):
        assert IBKRBroker._map_ib_status("Submitted") == OrderStatus.SUBMITTED

    def test_pre_submitted(self):
        assert IBKRBroker._map_ib_status("PreSubmitted") == OrderStatus.SUBMITTED

    def test_filled(self):
        assert IBKRBroker._map_ib_status("Filled") == OrderStatus.FILLED

    def test_partially_filled(self):
        assert IBKRBroker._map_ib_status("PartiallyFilled") == OrderStatus.PARTIALLY_FILLED

    def test_cancelled(self):
        assert IBKRBroker._map_ib_status("Cancelled") == OrderStatus.CANCELED

    def test_api_cancelled(self):
        assert IBKRBroker._map_ib_status("ApiCancelled") == OrderStatus.CANCELED

    def test_pending_submit(self):
        assert IBKRBroker._map_ib_status("PendingSubmit") == OrderStatus.PENDING

    def test_inactive(self):
        assert IBKRBroker._map_ib_status("Inactive") == OrderStatus.REJECTED

    def test_unknown_defaults_to_pending(self):
        assert IBKRBroker._map_ib_status("UnknownStatus") == OrderStatus.PENDING


# ======================================================================
# 7. Timeframe Mapping
# ======================================================================

class TestIBKRTimeframeMapping:
    """Tests for TimeFrame → IBKR bar size mapping."""

    def test_m1(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.M1) == "1 min"

    def test_m5(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.M5) == "5 mins"

    def test_h1(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.H1) == "1 hour"

    def test_d1(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.D1) == "1 day"

    def test_w1(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.W1) == "1 week"

    def test_mo1(self):
        assert IBKRBroker._map_timeframe_to_bar(TimeFrame.MO1) == "1 month"

    def test_unknown_defaults_to_1day(self):
        assert IBKRBroker._map_timeframe_to_bar("unknown") == "1 day"


# ======================================================================
# 8. Account Summary & Balance
# ======================================================================

class TestIBKRBrokerAccount:
    """Tests for account summary and balance."""

    @pytest.mark.asyncio
    async def test_get_account_summary(self, connected_broker, mock_ib):
        mock_items = []
        for tag, value in [
            ("NetLiquidation", "100000"),
            ("GrossPositionValue", "50000"),
            ("EquityWithLoanValue", "100000"),
            ("AvailableFunds", "50000"),
            ("BuyingPower", "200000"),
            ("MaintMarginReq", "25000"),
            ("UnrealizedPnL", "1500"),
            ("RealizedPnL", "3000"),
        ]:
            item = MagicMock()
            item.tag = tag
            item.value = value
            mock_items.append(item)

        mock_ib.accountSummaryAsync.return_value = mock_items

        summary = await connected_broker.get_account_summary()
        assert summary.account_id == "U1234567"
        assert summary.net_liquidation == 100000.0
        assert summary.buying_power == 200000.0

    @pytest.mark.asyncio
    async def test_get_account_summary_no_accounts(self, connected_broker, mock_ib):
        mock_ib.managedAccounts.return_value = []
        mock_ib.accountSummaryAsync.return_value = []

        summary = await connected_broker.get_account_summary()
        assert summary.account_id == ""
        assert summary.net_liquidation == 0.0

    @pytest.mark.asyncio
    async def test_get_account_summary_invalid_values(self, connected_broker, mock_ib):
        item = MagicMock()
        item.tag = "NetLiquidation"
        item.value = "not_a_number"
        mock_ib.accountSummaryAsync.return_value = [item]

        summary = await connected_broker.get_account_summary()
        assert summary.net_liquidation == 0.0

    @pytest.mark.asyncio
    async def test_get_balance(self, connected_broker, mock_ib):
        mock_items = []
        for tag, value in [("NetLiquidation", "100000"), ("AvailableFunds", "50000"), ("BuyingPower", "200000")]:
            item = MagicMock()
            item.tag = tag
            item.value = value
            mock_items.append(item)
        mock_ib.accountSummaryAsync.return_value = mock_items

        bal = await connected_broker.get_balance()
        assert bal["USD"] == 100000.0
        assert bal["available_funds"] == 50000.0
        assert bal["buying_power"] == 200000.0


# ======================================================================
# 9. Positions & Portfolio
# ======================================================================

class TestIBKRBrokerPositions:
    """Tests for positions and portfolio."""

    @pytest.mark.asyncio
    async def test_get_positions(self, connected_broker, mock_ib):
        mock_pos = MagicMock()
        mock_pos.contract.symbol = "AAPL"
        mock_pos.position = 100
        mock_pos.avgCost = 150.0
        mock_ib.positions.return_value = [mock_pos]

        positions = await connected_broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].side == PositionSide.LONG
        assert positions[0].quantity == 100.0

    @pytest.mark.asyncio
    async def test_get_positions_short(self, connected_broker, mock_ib):
        mock_pos = MagicMock()
        mock_pos.contract.symbol = "TSLA"
        mock_pos.position = -50
        mock_pos.avgCost = 200.0
        mock_ib.positions.return_value = [mock_pos]

        positions = await connected_broker.get_positions()
        assert positions[0].side == PositionSide.SHORT
        assert positions[0].quantity == 50.0

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, connected_broker, mock_ib):
        mock_ib.positions.return_value = []
        positions = await connected_broker.get_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_get_portfolio(self, connected_broker, mock_ib):
        mock_items = []
        for tag, value in [("NetLiquidation", "100000"), ("AvailableFunds", "50000"),
                          ("BuyingPower", "200000"), ("GrossPositionValue", "50000"),
                          ("EquityWithLoanValue", "100000"), ("MaintMarginReq", "25000"),
                          ("UnrealizedPnL", "0"), ("RealizedPnL", "0")]:
            item = MagicMock()
            item.tag = tag
            item.value = value
            mock_items.append(item)
        mock_ib.accountSummaryAsync.return_value = mock_items
        mock_ib.positions.return_value = []

        portfolio = await connected_broker.get_portfolio()
        assert portfolio.name == "ibkr"
        assert portfolio.currency == "USD"


# ======================================================================
# 10. Order Placement
# ======================================================================

class TestIBKRBrokerOrders:
    """Tests for order placement."""

    @pytest.mark.asyncio
    async def test_place_market_order(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 1
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100,
            )
        assert order.id == "1"
        assert order.side == OrderSide.BUY
        assert order.status == OrderStatus.SUBMITTED
        assert order.broker_id == "ibkr"

    @pytest.mark.asyncio
    async def test_place_limit_order(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 2
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=150.0,
            )
        assert order.price == 150.0

    @pytest.mark.asyncio
    async def test_place_limit_without_price_raises(self, connected_broker, mock_ib, mock_ib_insync):
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            with pytest.raises(OrderError, match="Limit price required"):
                await connected_broker.place_order(
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=100,
                )

    @pytest.mark.asyncio
    async def test_place_stop_order(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 3
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP,
                quantity=100,
                stop_price=155.0,
            )
        assert order.stop_price == 155.0

    @pytest.mark.asyncio
    async def test_place_stop_without_price_raises(self, connected_broker, mock_ib, mock_ib_insync):
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            with pytest.raises(OrderError, match="Stop price required"):
                await connected_broker.place_order(
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    order_type=OrderType.STOP,
                    quantity=100,
                )

    @pytest.mark.asyncio
    async def test_place_stop_limit_order(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 4
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.STOP_LIMIT,
                quantity=100,
                price=150.0,
                stop_price=155.0,
            )
        assert order.price == 150.0
        assert order.stop_price == 155.0

    @pytest.mark.asyncio
    async def test_place_stop_limit_missing_prices_raises(self, connected_broker, mock_ib, mock_ib_insync):
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            with pytest.raises(OrderError, match="Both limit and stop price required"):
                await connected_broker.place_order(
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    order_type=OrderType.STOP_LIMIT,
                    quantity=100,
                    price=150.0,
                )

    @pytest.mark.asyncio
    async def test_place_sell_order(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 5
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=50,
            )
        assert order.side == OrderSide.SELL

    @pytest.mark.asyncio
    async def test_place_order_with_notes(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 6
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100,
                notes="Test note",
            )
        assert order.notes == "Test note"

    @pytest.mark.asyncio
    async def test_place_order_stored_locally(self, connected_broker, mock_ib, mock_ib_insync):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 7
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 0
        mock_trade.orderStatus.avgFillPrice = 0
        mock_ib.placeOrder.return_value = mock_trade

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            order = await connected_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=100,
            )
        assert "7" in connected_broker._local_orders


# ======================================================================
# 11. Order Cancellation & Retrieval
# ======================================================================

class TestIBKRBrokerCancelGetOrder:
    """Tests for order cancellation and retrieval."""

    @pytest.mark.asyncio
    async def test_cancel_order_from_open_trades(self, connected_broker, mock_ib):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 1
        mock_trade.contract.symbol = "AAPL"
        mock_trade.order.action = "BUY"
        mock_trade.order.totalQuantity = 100
        mock_ib.openTrades.return_value = [mock_trade]

        connected_broker._local_orders["1"] = MagicMock(
            id="1", status=OrderStatus.SUBMITTED,
        )
        order = await connected_broker.cancel_order("1")
        assert order.status == OrderStatus.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_order_not_local(self, connected_broker, mock_ib):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 2
        mock_trade.contract.symbol = "GOOGL"
        mock_trade.order.action = "SELL"
        mock_trade.order.totalQuantity = 50
        mock_ib.openTrades.return_value = [mock_trade]

        order = await connected_broker.cancel_order("2")
        assert order.status == OrderStatus.CANCELED
        assert order.symbol == "GOOGL"

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, connected_broker, mock_ib):
        mock_ib.openTrades.return_value = []
        with pytest.raises(OrderError, match="not found in open trades"):
            await connected_broker.cancel_order("999")

    @pytest.mark.asyncio
    async def test_get_order_from_open_trades(self, connected_broker, mock_ib):
        mock_trade = MagicMock()
        mock_trade.order.orderId = 1
        mock_trade.contract.symbol = "AAPL"
        mock_trade.order.action = "BUY"
        mock_trade.order.totalQuantity = 100
        mock_trade.order.lmtPrice = 150.0
        mock_trade.orderStatus.status = "Submitted"
        mock_trade.orderStatus.filled = 50
        mock_trade.orderStatus.avgFillPrice = 150.0
        mock_ib.openTrades.return_value = [mock_trade]

        order = await connected_broker.get_order("1")
        assert order.id == "1"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY

    @pytest.mark.asyncio
    async def test_get_order_from_local_cache(self, connected_broker, mock_ib):
        mock_ib.openTrades.return_value = []
        cached_order = MagicMock()
        cached_order.id = "2"
        connected_broker._local_orders["2"] = cached_order

        order = await connected_broker.get_order("2")
        assert order is cached_order

    @pytest.mark.asyncio
    async def test_get_order_not_found(self, connected_broker, mock_ib):
        mock_ib.openTrades.return_value = []
        with pytest.raises(OrderError, match="not found"):
            await connected_broker.get_order("999")


# ======================================================================
# 12. Execution Reports
# ======================================================================

class TestIBKRBrokerExecutionReports:
    """Tests for execution reports."""

    @pytest.mark.asyncio
    async def test_get_execution_reports(self, connected_broker, mock_ib):
        mock_fill = MagicMock()
        mock_fill.execution.execId = "exec-1"
        mock_fill.execution.orderId = 1
        mock_fill.contract.symbol = "AAPL"
        mock_fill.execution.side = "BOT"
        mock_fill.execution.shares = 100
        mock_fill.execution.price = 150.50
        mock_fill.execution.time = "20240101 10:00:00"
        mock_fill.commissionReport.commission = 1.0
        mock_ib.fills.return_value = [mock_fill]

        reports = await connected_broker.get_execution_reports()
        assert len(reports) == 1
        assert reports[0].exec_id == "exec-1"
        assert reports[0].shares == 100.0
        assert reports[0].price == 150.50

    @pytest.mark.asyncio
    async def test_get_execution_reports_cached(self, connected_broker, mock_ib):
        mock_fill = MagicMock()
        mock_fill.execution.execId = "exec-2"
        mock_fill.execution.orderId = 2
        mock_fill.contract.symbol = "GOOGL"
        mock_fill.execution.side = "SLD"
        mock_fill.execution.shares = 50
        mock_fill.execution.price = 2800.0
        mock_fill.execution.time = ""
        mock_fill.commissionReport.commission = 0.5
        mock_ib.fills.return_value = [mock_fill]

        await connected_broker.get_execution_reports()
        assert "exec-2" in connected_broker._execution_reports


# ======================================================================
# 13. Market Data
# ======================================================================

class TestIBKRBrokerMarketData:
    """Tests for market data methods."""

    @pytest.mark.asyncio
    async def test_get_ohlcv(self, connected_broker, mock_ib, mock_ib_insync):
        mock_bar = MagicMock()
        mock_bar.date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_bar.open = 150.0
        mock_bar.high = 155.0
        mock_bar.low = 148.0
        mock_bar.close = 153.0
        mock_bar.volume = 1000000
        mock_ib.reqHistoricalDataAsync.return_value = [mock_bar]

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            result = await connected_broker.get_ohlcv("AAPL")
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].open == 150.0
        assert result[0].close == 153.0

    @pytest.mark.asyncio
    async def test_get_ohlcv_error(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ib.reqHistoricalDataAsync.side_effect = Exception("data error")
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            with pytest.raises(MarketDataError):
                await connected_broker.get_ohlcv("AAPL")

    @pytest.mark.asyncio
    async def test_get_ticker(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ticker = MagicMock()
        mock_ticker.last = 150.50
        mock_ticker.bid = 150.40
        mock_ticker.ask = 150.60
        mock_ticker.volume = 500000
        mock_ib.ticker.return_value = mock_ticker

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            ticker = await connected_broker.get_ticker("AAPL")
        assert ticker.symbol == "AAPL"
        assert ticker.last_price == 150.50

    @pytest.mark.asyncio
    async def test_get_ticker_error(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ib.reqMktData.side_effect = Exception("error")
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            with pytest.raises(MarketDataError):
                await connected_broker.get_ticker("AAPL")

    @pytest.mark.asyncio
    async def test_get_orderbook(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ticker = MagicMock()
        mock_bid = MagicMock()
        mock_bid.price = 150.40
        mock_bid.size = 100
        mock_ask = MagicMock()
        mock_ask.price = 150.60
        mock_ask.size = 200
        mock_ticker.domBids = [mock_bid]
        mock_ticker.domAsks = [mock_ask]
        mock_ib.reqMktData.return_value = mock_ticker

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            book = await connected_broker.get_orderbook("AAPL")
        assert book.symbol == "AAPL"
        assert book.bids[0].price == 150.40
        assert book.asks[0].price == 150.60

    @pytest.mark.asyncio
    async def test_get_trades(self, connected_broker, mock_ib):
        mock_fill = MagicMock()
        mock_fill.execution.execId = "t1"
        mock_fill.contract.symbol = "AAPL"
        mock_fill.execution.price = 150.50
        mock_fill.execution.shares = 100
        mock_fill.execution.side = "BOT"
        mock_fill.execution.time = "20240101 10:00:00"
        mock_ib.fills.return_value = [mock_fill]

        trades = await connected_broker.get_trades("AAPL")
        assert len(trades) == 1
        assert trades[0]["price"] == 150.50

    @pytest.mark.asyncio
    async def test_get_trades_symbol_filter(self, connected_broker, mock_ib):
        fill1 = MagicMock()
        fill1.contract.symbol = "AAPL"
        fill1.execution.execId = "t1"
        fill1.execution.price = 150.0
        fill1.execution.shares = 100
        fill1.execution.side = "BOT"
        fill1.execution.time = ""

        fill2 = MagicMock()
        fill2.contract.symbol = "GOOGL"
        fill2.execution.execId = "t2"
        fill2.execution.price = 2800.0
        fill2.execution.shares = 50
        fill2.execution.side = "SLD"
        fill2.execution.time = ""

        mock_ib.fills.return_value = [fill1, fill2]
        trades = await connected_broker.get_trades("AAPL")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "AAPL"


# ======================================================================
# 14. Health Check & Markets
# ======================================================================

class TestIBKRBrokerUtility:
    """Tests for utility methods."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, connected_broker, mock_ib):
        mock_ib.isConnected.return_value = True
        result = await connected_broker.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, connected_broker, mock_ib):
        mock_ib.isConnected.return_value = False
        result = await connected_broker.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, connected_broker, mock_ib):
        mock_ib.isConnected.side_effect = Exception("error")
        result = await connected_broker.health_check()
        assert result is False
        assert connected_broker.state == ExchangeState.ERROR

    @pytest.mark.asyncio
    async def test_get_markets(self, connected_broker):
        markets = await connected_broker.get_markets()
        assert isinstance(markets, list)
        assert "AAPL" in markets
        assert "SPY" in markets

    @pytest.mark.asyncio
    async def test_subscribe_ticker(self, connected_broker):
        await connected_broker.subscribe_ticker("AAPL", lambda d: None)

    @pytest.mark.asyncio
    async def test_subscribe_orderbook(self, connected_broker):
        await connected_broker.subscribe_orderbook("AAPL", lambda d: None)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connected_broker):
        await connected_broker.unsubscribe("AAPL", "ticker")

    @pytest.mark.asyncio
    async def test_require_ib_raises_when_disconnected(self, ibkr_broker):
        with pytest.raises(ConnectionError):
            ibkr_broker._require_ib()

    @pytest.mark.asyncio
    async def test_lookup_contract(self, connected_broker, mock_ib, mock_ib_insync):
        mock_detail = MagicMock()
        mock_detail.contract.symbol = "AAPL"
        mock_detail.contract.secType = "STK"
        mock_detail.contract.exchange = "SMART"
        mock_detail.contract.currency = "USD"
        mock_detail.contract.conId = 12345
        mock_ib.reqContractDetailsAsync = AsyncMock(return_value=[mock_detail])

        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            result = await connected_broker.lookup_contract("AAPL")
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.con_id == 12345

    @pytest.mark.asyncio
    async def test_lookup_contract_not_found(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ib.reqContractDetailsAsync = AsyncMock(return_value=[])
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            result = await connected_broker.lookup_contract("UNKNOWN")
        assert result is None

    @pytest.mark.asyncio
    async def test_lookup_contract_exception(self, connected_broker, mock_ib, mock_ib_insync):
        mock_ib.reqContractDetailsAsync = AsyncMock(side_effect=Exception("lookup error"))
        with patch.dict("sys.modules", {"ib_insync": mock_ib_insync}):
            result = await connected_broker.lookup_contract("AAPL")
        assert result is None
