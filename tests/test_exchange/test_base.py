"""Tests for Exchange module — base interface, config, errors, and types."""

import pytest

from quant_nanggroe_ai.exchange.base import (
    AuthenticationError,
    ConnectionError,
    ExchangeConfig,
    ExchangeError,
    ExchangeInterface,
    ExchangeState,
    InsufficientFundsError,
    MarketDataError,
    OrderError,
    RateLimitError,
)


# ─── Error Hierarchy ──────────────────────────────────────────────────────────


class TestExchangeErrors:
    """Tests for exchange error hierarchy."""

    def test_base_error(self):
        err = ExchangeError("Something went wrong", exchange="binance")
        assert str(err) == "Something went wrong"
        assert err.exchange == "binance"
        assert err.original is None

    def test_base_error_with_original(self):
        original = ValueError("original cause")
        err = ExchangeError("Wrapped", exchange="okx", original=original)
        assert err.original is original

    def test_connection_error_inherits(self):
        err = ConnectionError("Connection lost", exchange="binance")
        assert isinstance(err, ExchangeError)

    def test_order_error(self):
        err = OrderError("Order rejected", order_id="12345", exchange="binance")
        assert isinstance(err, ExchangeError)
        assert err.order_id == "12345"

    def test_rate_limit_error(self):
        err = RateLimitError(exchange="binance")
        assert isinstance(err, ExchangeError)
        assert err.retry_after == 60.0

    def test_rate_limit_error_custom_retry(self):
        err = RateLimitError(retry_after=30.0, exchange="okx")
        assert err.retry_after == 30.0

    def test_authentication_error(self):
        err = AuthenticationError("Invalid API key", exchange="binance")
        assert isinstance(err, ExchangeError)

    def test_insufficient_funds_error(self):
        err = InsufficientFundsError("Not enough USDT", exchange="binance")
        assert isinstance(err, ExchangeError)

    def test_market_data_error(self):
        err = MarketDataError("No data", exchange="binance")
        assert isinstance(err, ExchangeError)


# ─── ExchangeConfig ────────────────────────────────────────────────────────────


class TestExchangeConfig:
    """Tests for ExchangeConfig model."""

    def test_minimal_creation(self):
        config = ExchangeConfig(exchange_id="binance")
        assert config.exchange_id == "binance"
        assert config.api_key is None
        assert config.api_secret is None
        assert config.sandbox is False

    def test_full_creation(self):
        config = ExchangeConfig(
            exchange_id="okx",
            api_key="key123",
            api_secret="secret456",
            passphrase="pass789",
            sandbox=True,
            rate_limit=10.0,
            timeout=60,
            retries=5,
            retry_delay=2.0,
            options={"defaultType": "spot"},
        )
        assert config.exchange_id == "okx"
        assert config.api_key == "key123"
        assert config.passphrase == "pass789"
        assert config.sandbox is True
        assert config.rate_limit == 10.0
        assert config.timeout == 60
        assert config.retries == 5
        assert config.retry_delay == 2.0
        assert config.options["defaultType"] == "spot"

    def test_exchange_id_required(self):
        with pytest.raises(Exception):
            ExchangeConfig()

    def test_exchange_id_min_length(self):
        with pytest.raises(Exception):
            ExchangeConfig(exchange_id="")

    def test_rate_limit_must_be_positive(self):
        with pytest.raises(Exception):
            ExchangeConfig(exchange_id="binance", rate_limit=0)

    def test_timeout_must_be_positive(self):
        with pytest.raises(Exception):
            ExchangeConfig(exchange_id="binance", timeout=0)

    def test_retries_non_negative(self):
        with pytest.raises(Exception):
            ExchangeConfig(exchange_id="binance", retries=-1)

    def test_retry_delay_non_negative(self):
        with pytest.raises(Exception):
            ExchangeConfig(exchange_id="binance", retry_delay=-1.0)

    def test_serialization(self):
        config = ExchangeConfig(exchange_id="binance", sandbox=True)
        data = config.model_dump()
        restored = ExchangeConfig(**data)
        assert restored.exchange_id == "binance"
        assert restored.sandbox is True


# ─── ExchangeState ─────────────────────────────────────────────────────────────


class TestExchangeState:
    """Tests for ExchangeState enum."""

    def test_all_states(self):
        assert ExchangeState.DISCONNECTED == "disconnected"
        assert ExchangeState.CONNECTING == "connecting"
        assert ExchangeState.CONNECTED == "connected"
        assert ExchangeState.RECONNECTING == "reconnecting"
        assert ExchangeState.ERROR == "error"
        assert ExchangeState.RATE_LIMITED == "rate_limited"

    def test_state_count(self):
        assert len(ExchangeState) == 6


# ─── ExchangeInterface (Abstract) ─────────────────────────────────────────────


class TestExchangeInterface:
    """Tests for ExchangeInterface abstract base class."""

    def test_cannot_instantiate_directly(self):
        """ExchangeInterface is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            ExchangeInterface()

    def test_concrete_subclass(self):
        """A concrete subclass must implement all abstract methods."""

        class MockExchange(ExchangeInterface):
            def __init__(self):
                self._connected = False
                self._state = ExchangeState.DISCONNECTED

            async def connect(self):
                self._connected = True
                self._state = ExchangeState.CONNECTED
                return True

            async def disconnect(self):
                self._connected = False
                self._state = ExchangeState.DISCONNECTED

            @property
            def is_connected(self):
                return self._connected

            @property
            def state(self):
                return self._state

            @property
            def name(self):
                return "mock-exchange"

            async def get_balance(self):
                return {"USDT": 10000.0}

            async def get_positions(self):
                return []

            async def get_portfolio(self):
                from quant_nanggroe_ai.types.positions import Portfolio
                return Portfolio(cash=10000.0, positions=[], total_value=10000.0)

            async def place_order(self, symbol, side, order_type, quantity, **kwargs):
                from quant_nanggroe_ai.types.orders import Order, OrderStatus
                return Order(
                    order_id="mock-123",
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    status=OrderStatus.NEW,
                )

            async def cancel_order(self, order_id, **kwargs):
                from quant_nanggroe_ai.types.orders import Order, OrderStatus
                return Order(
                    order_id=order_id,
                    symbol="BTC/USDT",
                    status=OrderStatus.CANCELLED,
                )

            async def get_order(self, order_id, **kwargs):
                from quant_nanggroe_ai.types.orders import Order, OrderStatus
                return Order(
                    order_id=order_id,
                    symbol="BTC/USDT",
                    status=OrderStatus.FILLED,
                )

            async def get_ohlcv(self, symbol, **kwargs):
                return []

            async def get_ticker(self, symbol):
                from quant_nanggroe_ai.types.market import Ticker
                return Ticker(symbol=symbol, last=50000.0, bid=49999.0, ask=50001.0)

            async def get_orderbook(self, symbol, **kwargs):
                from quant_nanggroe_ai.types.market import OrderBook
                return OrderBook(symbol=symbol, bids=[], asks=[])

            async def get_trades(self, symbol, **kwargs):
                return []

            async def subscribe_ticker(self, symbol, callback):
                pass

            async def subscribe_orderbook(self, symbol, callback):
                pass

            async def subscribe_trades(self, symbol, callback):
                pass

            async def unsubscribe(self, symbol, channel):
                pass

            async def get_markets(self):
                return ["BTC/USDT"]

            async def health_check(self):
                return True

        exchange = MockExchange()
        assert exchange.name == "mock-exchange"
        assert not exchange.is_connected
        assert exchange.state == ExchangeState.DISCONNECTED


# ─── Exchange Guards ───────────────────────────────────────────────────────────


class TestExchangeGuards:
    """Tests for exchange guard pipeline."""

    def test_guards_import(self):
        from quant_nanggroe_ai.exchange.guards import GuardPipeline
        assert GuardPipeline is not None

    def test_guard_pipeline_creation(self):
        from quant_nanggroe_ai.exchange.guards import GuardPipeline
        pipeline = GuardPipeline()
        assert pipeline is not None


# ─── Order Types ───────────────────────────────────────────────────────────────


class TestOrderTypes:
    """Tests for exchange order types."""

    def test_order_types_import(self):
        from quant_nanggroe_ai.exchange.order_types import TrailingStopOrder, BracketOrder
        assert TrailingStopOrder is not None
        assert BracketOrder is not None


# ─── Factory ───────────────────────────────────────────────────────────────────


class TestExchangeFactory:
    """Tests for ExchangeFactory."""

    def test_factory_import(self):
        from quant_nanggroe_ai.exchange.factory import ExchangeFactory
        assert ExchangeFactory is not None
