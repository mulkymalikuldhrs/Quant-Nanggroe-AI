"""Integration test for SL/TP handling in MT5Broker.place_order (BLOCKER 2h).

The exchange-layer MT5Broker previously built the ``order_send`` request dict
WITHOUT stop-loss / take-profit, so protective levels never reached MT5. This
test mocks ``mt5.order_send`` and asserts that ``sl`` and ``tp`` are present in
the request dict when ``stop_loss`` / ``take_profit`` are passed to
``place_order``.

All tests use a mocked MetaTrader5 module — no real MT5 calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from quant_nanggroe.exchange.base import ExchangeConfig, ExchangeState
from quant_nanggroe.exchange.mt5_broker import MT5Broker
from quant_nanggroe.types.market import TimeFrame
from quant_nanggroe.types.orders import OrderSide, OrderType
from quant_nanggroe.types.positions import PositionSide


# ======================================================================
# Fixtures / mocks
# ======================================================================

@pytest.fixture
def mt5_config():
    return ExchangeConfig(
        exchange_id="mt5",
        api_key="<placeholder>",
        api_secret="<placeholder>",
        options={"server": "MetaQuotes-Demo"},
    )


@pytest.fixture
def mt5_broker(mt5_config):
    return MT5Broker(mt5_config)


def _make_mock_mt5():
    """Create a comprehensive mock MetaTrader5 module."""
    mt5 = MagicMock()
    mt5.initialize.return_value = True
    mt5.login.return_value = True
    mt5.last_error.return_value = (0, "No error")
    mt5.shutdown.return_value = None

    # Constants
    mt5.TRADE_ACTION_DEAL = 1
    mt5.TRADE_ACTION_PENDING = 5
    mt5.TRADE_ACTION_SLTP = 6
    mt5.ORDER_TYPE_BUY = 0
    mt5.ORDER_TYPE_SELL = 1
    mt5.ORDER_TYPE_BUY_LIMIT = 2
    mt5.ORDER_TYPE_SELL_LIMIT = 3
    mt5.ORDER_TYPE_BUY_STOP = 4
    mt5.ORDER_TYPE_SELL_STOP = 5
    mt5.POSITION_TYPE_BUY = 0
    mt5.POSITION_TYPE_SELL = 1
    mt5.TRADE_RETCODE_DONE = 10009
    mt5.ORDER_FILLING_IOC = 2
    mt5.ORDER_TIME_GTC = 0

    return mt5


@pytest.fixture
def mock_mt5():
    return _make_mock_mt5()


@pytest.fixture
def connected_broker(mt5_broker, mock_mt5):
    """Connected MT5Broker with mocked MT5 module."""
    mt5_broker._mt5 = mock_mt5
    mt5_broker._state = ExchangeState.CONNECTED
    return mt5_broker


def _setup_order_send(mock_mt5, order_ticket=12345):
    """Wire up symbol tick + a successful order_send result."""
    tick = MagicMock()
    tick.ask = 1.0850
    tick.bid = 1.0848
    mock_mt5.symbol_info_tick.return_value = tick

    result = MagicMock()
    result.order = order_ticket
    result.retcode = mock_mt5.TRADE_RETCODE_DONE
    result.volume = 0.1
    result.price = 1.0850
    result.comment = "Done"
    mock_mt5.order_send.return_value = result
    return result


# ======================================================================
# Integration tests: SL/TP must appear in the order_send request dict
# ======================================================================

class TestMT5SLTPIntegration:
    """Assert SL/TP are forwarded to order_send request dict (BLOCKER 2h)."""

    @pytest.mark.asyncio
    async def test_market_buy_with_sl_tp_sends_sl_tp_in_request(
        self, connected_broker, mock_mt5
    ):
        _setup_order_send(mock_mt5)

        await connected_broker.place_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            stop_loss=1.0800,
            take_profit=1.0900,
        )

        # order_send must have been called exactly once
        assert mock_mt5.order_send.call_count == 1
        request = mock_mt5.order_send.call_args.args[0]

        # BLOCKER 2h: sl / tp must be present and correct in the request dict
        assert "sl" in request, "request dict missing 'sl' key"
        assert "tp" in request, "request dict missing 'tp' key"
        assert request["sl"] == 1.0800
        assert request["tp"] == 1.0900
        # sanity: other core fields still present
        assert request["symbol"] == "EURUSD"
        assert request["volume"] == 0.1
        assert request["type"] == mock_mt5.ORDER_TYPE_BUY

    @pytest.mark.asyncio
    async def test_market_sell_with_sl_tp_sends_sl_tp_in_request(
        self, connected_broker, mock_mt5
    ):
        _setup_order_send(mock_mt5)

        await connected_broker.place_order(
            symbol="EURUSD",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.2,
            stop_loss=1.0900,
            take_profit=1.0800,
        )

        assert mock_mt5.order_send.call_count == 1
        request = mock_mt5.order_send.call_args.args[0]
        assert request["sl"] == 1.0900
        assert request["tp"] == 1.0800
        assert request["type"] == mock_mt5.ORDER_TYPE_SELL

    @pytest.mark.asyncio
    async def test_sl_tp_only_sl_sends_only_sl(
        self, connected_broker, mock_mt5
    ):
        _setup_order_send(mock_mt5)

        await connected_broker.place_order(
            symbol="GBPUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.05,
            stop_loss=1.2700,
        )

        request = mock_mt5.order_send.call_args.args[0]
        assert request["sl"] == 1.2700
        assert "tp" not in request, "tp should be omitted when not provided"

    @pytest.mark.asyncio
    async def test_no_sl_tp_request_has_no_sl_tp_keys(
        self, connected_broker, mock_mt5
    ):
        _setup_order_send(mock_mt5)

        await connected_broker.place_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )

        request = mock_mt5.order_send.call_args.args[0]
        assert "sl" not in request
        assert "tp" not in request

    @pytest.mark.asyncio
    async def test_returned_order_carries_sl_tp(
        self, connected_broker, mock_mt5
    ):
        _setup_order_send(mock_mt5)

        order = await connected_broker.place_order(
            symbol="EURUSD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            stop_loss=1.0800,
            take_profit=1.0900,
        )

        assert order.stop_loss == 1.0800
        assert order.take_profit == 1.0900
        # and the request to MT5 must reflect them as well
        request = mock_mt5.order_send.call_args.args[0]
        assert request["sl"] == 1.0800
        assert request["tp"] == 1.0900
