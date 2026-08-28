"""Tests for Alpaca Trading Broker.

All tests use mocked Alpaca API responses — no real API calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from quant_nanggroe.exchange.alpaca_broker import (
    _ALPACA_STATUS_MAP,
    _ALPACA_TYPE_MAP,
    _SIDE_TO_ALPACA,
    AlpacaBroker,
    CircuitBreaker,
)
from quant_nanggroe.exchange.base import (
    ConnectionError,
    ExchangeConfig,
    ExchangeState,
    MarketDataError,
)
from quant_nanggroe.types.orders import OrderSide, OrderStatus, OrderType
from quant_nanggroe.types.positions import PositionSide

# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def alpaca_config():
    """Create an Alpaca exchange config for paper trading."""
    return ExchangeConfig(
        exchange_id="alpaca",
        api_key="<placeholder>",
        api_secret="<placeholder>",
        sandbox=True,
        rate_limit=10.0,
        retries=2,
    )


@pytest.fixture
def alpaca_broker(alpaca_config):
    """Create an AlpacaBroker instance."""
    return AlpacaBroker(alpaca_config)


# ======================================================================
# CircuitBreaker
# ======================================================================

class TestCircuitBreaker:
    """Tests for the CircuitBreaker utility."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(max_errors=3, cooldown_seconds=1.0)
        assert cb.is_open is False

    def test_opens_after_max_errors(self):
        cb = CircuitBreaker(max_errors=3, cooldown_seconds=60.0)
        cb.record_error()
        cb.record_error()
        assert cb.is_open is False
        cb.record_error()
        assert cb.is_open is True

    def test_success_resets_errors(self):
        cb = CircuitBreaker(max_errors=3, cooldown_seconds=60.0)
        cb.record_error()
        cb.record_error()
        cb.record_success()
        assert cb.is_open is False
        cb.record_error()
        assert cb.is_open is False  # Only 1 error after reset

    def test_reset_clears_state(self):
        cb = CircuitBreaker(max_errors=2, cooldown_seconds=60.0)
        cb.record_error()
        cb.record_error()
        assert cb.is_open is True
        cb.reset()
        assert cb.is_open is False

    def test_repr_like(self):
        cb = CircuitBreaker(max_errors=5)
        assert not cb.is_open


# ======================================================================
# Mapping Helpers
# ======================================================================

class TestMappingHelpers:
    """Tests for Alpaca mapping dictionaries."""

    def test_type_mapping(self):
        assert _ALPACA_TYPE_MAP[OrderType.MARKET] == "market"
        assert _ALPACA_TYPE_MAP[OrderType.LIMIT] == "limit"
        assert _ALPACA_TYPE_MAP[OrderType.STOP] == "stop"
        assert _ALPACA_TYPE_MAP[OrderType.STOP_LIMIT] == "stop_limit"
        assert _ALPACA_TYPE_MAP[OrderType.TRAILING_STOP] == "trailing_stop"

    def test_status_mapping(self):
        assert _ALPACA_STATUS_MAP["new"] == OrderStatus.SUBMITTED
        assert _ALPACA_STATUS_MAP["filled"] == OrderStatus.FILLED
        assert _ALPACA_STATUS_MAP["canceled"] == OrderStatus.CANCELED
        assert _ALPACA_STATUS_MAP["rejected"] == OrderStatus.REJECTED
        assert _ALPACA_STATUS_MAP["partially_filled"] == OrderStatus.PARTIALLY_FILLED

    def test_side_mapping(self):
        assert _SIDE_TO_ALPACA[OrderSide.BUY] == "buy"
        assert _SIDE_TO_ALPACA[OrderSide.SELL] == "sell"


# ======================================================================
# Connection Lifecycle
# ======================================================================

class TestAlpacaBrokerConnection:
    """Tests for connection lifecycle."""

    def test_initial_state(self, alpaca_broker):
        assert alpaca_broker.is_connected is False
        assert alpaca_broker.state == ExchangeState.DISCONNECTED
        assert alpaca_broker.name == "alpaca"

    @pytest.mark.asyncio
    async def test_connect_without_alpaca_raises(self, alpaca_broker):
        """Connect should raise ImportError if alpaca-py not installed."""
        with patch.dict("sys.modules", {"alpaca": None, "alpaca.trading": None, "alpaca.trading.client": None}):
            with pytest.raises((ImportError, Exception)):
                await alpaca_broker.connect()

    @pytest.mark.asyncio
    async def test_operations_require_connection(self, alpaca_broker):
        """Operations on disconnected broker should raise ConnectionError."""
        with pytest.raises(ConnectionError):
            await alpaca_broker.get_balance()
        with pytest.raises(ConnectionError):
            await alpaca_broker.place_order(
                symbol="AAPL",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10,
            )

    def test_repr(self, alpaca_broker):
        result = repr(alpaca_broker)
        assert "AlpacaBroker" in result
        assert "disconnected" in result


# ======================================================================
# Order Conversion
# ======================================================================

class TestAlpacaOrderConversion:
    """Tests for Alpaca order → Order model conversion."""

    def test_alpaca_order_to_order_market(self):
        """Test conversion of a market order."""
        mock_alpaca_order = MagicMock()
        mock_alpaca_order.id = "order-123"
        mock_alpaca_order.client_order_id = "client-001"
        mock_alpaca_order.symbol = "AAPL"
        mock_alpaca_order.side = "buy"
        mock_alpaca_order.order_type = "market"
        mock_alpaca_order.qty = "10"
        mock_alpaca_order.limit_price = None
        mock_alpaca_order.stop_price = None
        mock_alpaca_order.status = "filled"
        mock_alpaca_order.filled_qty = "10"
        mock_alpaca_order.filled_avg_price = "150.50"
        mock_alpaca_order.submitted_at = datetime.now(tz=timezone.utc)

        order = AlpacaBroker._alpaca_order_to_order(mock_alpaca_order)

        assert order.id == "order-123"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 10.0
        assert order.status == OrderStatus.FILLED
        assert order.filled_quantity == 10.0
        assert order.average_fill_price == 150.50
        assert order.broker_id == "alpaca"

    def test_alpaca_order_to_order_limit(self):
        """Test conversion of a limit order."""
        mock_alpaca_order = MagicMock()
        mock_alpaca_order.id = "order-456"
        mock_alpaca_order.client_order_id = None
        mock_alpaca_order.symbol = "GOOGL"
        mock_alpaca_order.side = "sell"
        mock_alpaca_order.order_type = "limit"
        mock_alpaca_order.qty = "5"
        mock_alpaca_order.limit_price = "2800.0"
        mock_alpaca_order.stop_price = None
        mock_alpaca_order.status = "new"
        mock_alpaca_order.filled_qty = "0"
        mock_alpaca_order.filled_avg_price = None
        mock_alpaca_order.submitted_at = datetime.now(tz=timezone.utc)

        order = AlpacaBroker._alpaca_order_to_order(mock_alpaca_order)

        assert order.side == OrderSide.SELL
        assert order.order_type == OrderType.LIMIT
        assert order.price == 2800.0
        assert order.status == OrderStatus.SUBMITTED
        assert order.filled_quantity == 0.0


# ======================================================================
# Position Conversion
# ======================================================================

class TestAlpacaPositionConversion:
    """Tests for Alpaca position → Position model conversion."""

    def test_alpaca_position_to_position_long(self):
        """Test conversion of a long position."""
        mock_pos = MagicMock()
        mock_pos.symbol = "AAPL"
        mock_pos.qty = "100"
        mock_pos.avg_entry_price = "150.0"
        mock_pos.current_price = "155.0"
        mock_pos.unrealized_pl = "500.0"
        mock_pos.cost_basis = "15000.0"
        mock_pos.market_value = "15500.0"

        position = AlpacaBroker._alpaca_position_to_position(mock_pos)

        assert position is not None
        assert position.symbol == "AAPL"
        assert position.side == PositionSide.LONG
        assert position.quantity == 100.0
        assert position.entry_price == 150.0
        assert position.current_price == 155.0
        assert position.unrealized_pnl == 500.0

    def test_alpaca_position_zero_qty_returns_none(self):
        """Zero-quantity position should return None."""
        mock_pos = MagicMock()
        mock_pos.qty = "0"
        mock_pos.avg_entry_price = "150.0"
        mock_pos.current_price = "155.0"
        mock_pos.unrealized_pl = "0.0"
        mock_pos.cost_basis = "0.0"
        mock_pos.market_value = "0.0"

        result = AlpacaBroker._alpaca_position_to_position(mock_pos)
        assert result is None


# ======================================================================
# Market Data (not supported)
# ======================================================================

class TestAlpacaBrokerMarketData:
    """Tests for market data methods."""

    @pytest.mark.asyncio
    async def test_get_orderbook_raises(self, alpaca_broker):
        """Order book should raise MarketDataError."""
        alpaca_broker._state = ExchangeState.CONNECTED
        with pytest.raises(MarketDataError):
            await alpaca_broker.get_orderbook("AAPL")


# ======================================================================
# Circuit Breaker Integration
# ======================================================================

class TestAlpacaBrokerCircuitBreaker:
    """Tests for circuit breaker integration in the broker."""

    def test_circuit_breaker_opens(self, alpaca_broker):
        """Circuit breaker should open after consecutive errors."""
        for _ in range(5):
            alpaca_broker._circuit_breaker.record_error()
        assert alpaca_broker._circuit_breaker.is_open

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_when_open(self, alpaca_broker):
        """Circuit breaker should block operations when open."""
        alpaca_broker._state = ExchangeState.CONNECTED
        alpaca_broker._trading_client = MagicMock()

        # Open the circuit breaker
        for _ in range(5):
            alpaca_broker._circuit_breaker.record_error()

        with pytest.raises(Exception):  # ExchangeError or similar
            await alpaca_broker.get_balance()

    def test_circuit_breaker_resets_on_success(self, alpaca_broker):
        """Circuit breaker should reset on success."""
        alpaca_broker._circuit_breaker.record_error()
        alpaca_broker._circuit_breaker.record_error()
        alpaca_broker._circuit_breaker.record_success()
        assert not alpaca_broker._circuit_breaker.is_open
