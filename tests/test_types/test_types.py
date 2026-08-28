"""Comprehensive tests for all type modules.

Tests cover:
- RiskLevel enum values
- RiskAssessment model: create with valid data, reject invalid
- VaRResult model: round-trip serialization
- DrawdownResult model
- OrderType, OrderSide, OrderStatus enums
- Order, MarketOrder, LimitOrder models
- OHLCV, Ticker, OrderBook models
- Position, PositionSide, Portfolio models
- Signal types
- Decision types

Each test verifies:
- Pydantic model validation works (valid data accepted)
- Invalid data rejected (missing fields, wrong types)
- JSON serialization round-trip
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from quant_nanggroe.types.decisions import (
    ConfluenceScore,
    Decision,
    DecisionTable,
    DecisionType,
)
from quant_nanggroe.types.market import (
    OHLCV,
    MarketData,
    OrderBook,
    OrderBookLevel,
    Ticker,
    TimeFrame,
)
from quant_nanggroe.types.orders import (
    LimitOrder,
    MarketOrder,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    StopLimitOrder,
    StopOrder,
)
from quant_nanggroe.types.positions import (
    Portfolio,
    Position,
    PositionSide,
)
from quant_nanggroe.types.risk import (
    DrawdownResult,
    PositionSizingResult,
    RiskAssessment,
    RiskLevel,
    VaRResult,
)
from quant_nanggroe.types.signals import (
    Signal,
    SignalStrength,
    SignalType,
)

# ═══════════════════════════════════════════════════════════════════════
# 1. Risk Types
# ═══════════════════════════════════════════════════════════════════════


class TestRiskLevel:

    def test_all_values(self):
        expected = ["low", "moderate", "high", "critical", "breach"]
        actual = [r.value for r in RiskLevel]
        assert set(actual) == set(expected)

    def test_from_string(self):
        assert RiskLevel("low") == RiskLevel.LOW
        assert RiskLevel("breach") == RiskLevel.BREACH

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            RiskLevel("extreme")

    def test_is_string_enum(self):
        assert isinstance(RiskLevel.LOW, str)


class TestRiskAssessment:

    def test_create_valid(self):
        ra = RiskAssessment(symbol="AAPL")
        assert ra.symbol == "AAPL"
        assert ra.risk_level == RiskLevel.LOW
        assert ra.approved is True
        assert ra.veto is False
        assert ra.confidence == 0.0
        assert ra.per_trade_risk_pct == 0.0
        assert ra.daily_loss_pct == 0.0
        assert ra.position_concentration_pct == 0.0

    def test_create_with_all_fields(self):
        ra = RiskAssessment(
            symbol="BTC/USDT",
            risk_level=RiskLevel.HIGH,
            approved=False,
            veto=True,
            veto_reason="Daily loss exceeded",
            confidence=0.3,
            check_per_trade_risk=True,
            check_daily_loss=False,
            check_weekly_loss=True,
            check_max_drawdown=True,
            check_correlation=True,
            check_concentration=True,
            check_liquidity=True,
            check_volatility=False,
            check_market_hours=True,
            per_trade_risk_pct=0.008,
            daily_loss_pct=0.015,
            weekly_loss_pct=0.04,
            current_drawdown_pct=0.08,
            portfolio_var=-5000.0,
            portfolio_cvar=-8000.0,
            position_concentration_pct=0.15,
            avg_correlation=0.6,
            suggested_position_size=100.0,
            suggested_stop_loss=48000.0,
            suggested_take_profit=55000.0,
        )
        assert ra.risk_level == RiskLevel.HIGH
        assert ra.veto is True
        assert ra.veto_reason == "Daily loss exceeded"
        assert ra.check_daily_loss is False
        assert ra.portfolio_var == -5000.0

    def test_reject_missing_symbol(self):
        with pytest.raises(ValidationError):
            RiskAssessment()

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            RiskAssessment(symbol="AAPL", confidence=1.5)

    def test_confidence_negative(self):
        with pytest.raises(ValidationError):
            RiskAssessment(symbol="AAPL", confidence=-0.1)

    def test_confidence_boundary_zero(self):
        ra = RiskAssessment(symbol="AAPL", confidence=0.0)
        assert ra.confidence == 0.0

    def test_confidence_boundary_one(self):
        ra = RiskAssessment(symbol="AAPL", confidence=1.0)
        assert ra.confidence == 1.0

    def test_serialization_round_trip(self):
        ra = RiskAssessment(
            symbol="AAPL",
            risk_level=RiskLevel.MODERATE,
            approved=True,
            confidence=0.7,
            portfolio_var=-2000.0,
        )
        data = ra.model_dump()
        ra2 = RiskAssessment(**data)
        assert ra2.symbol == ra.symbol
        assert ra2.risk_level == ra.risk_level
        assert ra2.confidence == ra.confidence
        assert ra2.portfolio_var == ra.portfolio_var

    def test_json_round_trip(self):
        ra = RiskAssessment(
            symbol="AAPL",
            risk_level=RiskLevel.HIGH,
            confidence=0.5,
        )
        json_str = ra.model_dump_json()
        ra2 = RiskAssessment.model_validate_json(json_str)
        assert ra2.symbol == ra.symbol
        assert ra2.risk_level == ra.risk_level

    def test_veto_state(self):
        ra = RiskAssessment(
            symbol="BTC",
            veto=True,
            approved=False,
            veto_reason="Max drawdown exceeded",
        )
        assert ra.veto is True
        assert ra.approved is False

    def test_default_checks_all_pass(self):
        ra = RiskAssessment(symbol="AAPL")
        assert ra.check_per_trade_risk is True
        assert ra.check_daily_loss is True
        assert ra.check_weekly_loss is True
        assert ra.check_max_drawdown is True
        assert ra.check_correlation is True
        assert ra.check_concentration is True
        assert ra.check_liquidity is True
        assert ra.check_volatility is True
        assert ra.check_market_hours is True


class TestVaRResult:

    def test_create_valid(self):
        result = VaRResult(
            var_value=-5000.0,
            cvar_value=-8000.0,
            confidence_level=0.95,
            time_horizon=1,
            method="parametric",
            portfolio_value=1_000_000,
            var_pct=0.005,
            cvar_pct=0.008,
        )
        assert result.var_value == -5000.0
        assert result.cvar_value == -8000.0
        assert result.confidence_level == 0.95
        assert result.method == "parametric"

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            VaRResult()

    def test_confidence_level_range(self):
        with pytest.raises(ValidationError):
            VaRResult(
                var_value=-5000,
                cvar_value=-8000,
                confidence_level=0.5,  # Below 0.9
                time_horizon=1,
                method="parametric",
                portfolio_value=1_000_000,
                var_pct=0.005,
                cvar_pct=0.008,
            )

    def test_confidence_level_upper_range(self):
        with pytest.raises(ValidationError):
            VaRResult(
                var_value=-5000,
                cvar_value=-8000,
                confidence_level=1.0,  # Above 0.99
                time_horizon=1,
                method="parametric",
                portfolio_value=1_000_000,
                var_pct=0.005,
                cvar_pct=0.008,
            )

    def test_portfolio_value_must_be_positive(self):
        with pytest.raises(ValidationError):
            VaRResult(
                var_value=-5000,
                cvar_value=-8000,
                confidence_level=0.95,
                time_horizon=1,
                method="parametric",
                portfolio_value=0,  # Must be > 0
                var_pct=0.005,
                cvar_pct=0.008,
            )

    def test_time_horizon_positive(self):
        with pytest.raises(ValidationError):
            VaRResult(
                var_value=-5000,
                cvar_value=-8000,
                confidence_level=0.95,
                time_horizon=0,  # Must be >= 1
                method="parametric",
                portfolio_value=1_000_000,
                var_pct=0.005,
                cvar_pct=0.008,
            )

    def test_serialization_round_trip(self):
        result = VaRResult(
            var_value=-5000.0,
            cvar_value=-8000.0,
            confidence_level=0.95,
            time_horizon=1,
            method="parametric",
            portfolio_value=1_000_000,
            var_pct=0.005,
            cvar_pct=0.008,
        )
        data = result.model_dump()
        result2 = VaRResult(**data)
        assert result2.var_value == result.var_value
        assert result2.confidence_level == result.confidence_level
        assert result2.method == result.method

    def test_json_round_trip(self):
        result = VaRResult(
            var_value=-5000.0,
            cvar_value=-8000.0,
            confidence_level=0.95,
            time_horizon=1,
            method="historical",
            portfolio_value=1_000_000,
            var_pct=0.005,
            cvar_pct=0.008,
        )
        json_str = result.model_dump_json()
        result2 = VaRResult.model_validate_json(json_str)
        assert result2.method == "historical"

    def test_simulation_count_optional(self):
        result = VaRResult(
            var_value=-5000,
            cvar_value=-8000,
            confidence_level=0.95,
            time_horizon=1,
            method="monte_carlo",
            portfolio_value=1_000_000,
            var_pct=0.005,
            cvar_pct=0.008,
            simulation_count=10000,
        )
        assert result.simulation_count == 10000


class TestDrawdownResult:

    def test_create_valid(self):
        result = DrawdownResult(
            current_drawdown=5.0,
            max_drawdown=15.0,
            peak_value=1_100_000,
            current_value=1_045_000,
        )
        assert result.current_drawdown == 5.0
        assert result.max_drawdown == 15.0
        assert result.peak_value == 1_100_000

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            DrawdownResult()

    def test_drawdown_non_negative(self):
        with pytest.raises(ValidationError):
            DrawdownResult(
                current_drawdown=-1.0,
                max_drawdown=5.0,
                peak_value=1000,
                current_value=950,
            )

    def test_peak_value_must_be_positive(self):
        with pytest.raises(ValidationError):
            DrawdownResult(
                current_drawdown=5.0,
                max_drawdown=15.0,
                peak_value=0,  # Must be > 0
                current_value=950,
            )

    def test_current_value_must_be_positive(self):
        with pytest.raises(ValidationError):
            DrawdownResult(
                current_drawdown=5.0,
                max_drawdown=15.0,
                peak_value=1000,
                current_value=0,  # Must be > 0
            )

    def test_serialization_round_trip(self):
        result = DrawdownResult(
            current_drawdown=5.0,
            max_drawdown=15.0,
            peak_value=1_100_000,
            current_value=1_045_000,
        )
        data = result.model_dump()
        result2 = DrawdownResult(**data)
        assert result2.current_drawdown == result.current_drawdown

    def test_optional_fields(self):
        result = DrawdownResult(
            current_drawdown=5.0,
            max_drawdown=15.0,
            peak_value=1_100_000,
            current_value=1_045_000,
            trough_value=935_000,
            recovery_time_days=30,
            underwater_duration_days=45,
        )
        assert result.trough_value == 935_000
        assert result.recovery_time_days == 30


class TestPositionSizingResult:

    def test_create_valid(self):
        result = PositionSizingResult(
            symbol="AAPL",
            position_size=100,
            position_value=15000,
            risk_amount=750,
            risk_pct=0.5,
            method="kelly",
        )
        assert result.symbol == "AAPL"
        assert result.method == "kelly"

    def test_risk_pct_max(self):
        with pytest.raises(ValidationError):
            PositionSizingResult(
                symbol="AAPL",
                position_size=100,
                position_value=15000,
                risk_amount=750,
                risk_pct=10.0,  # Max is 5.0
                method="kelly",
            )


# ═══════════════════════════════════════════════════════════════════════
# 2. Order Types
# ═══════════════════════════════════════════════════════════════════════


class TestOrderType:

    def test_all_values(self):
        expected = ["market", "limit", "stop", "stop_limit", "trailing_stop", "take_profit", "take_profit_limit"]
        actual = [o.value for o in OrderType]
        assert set(actual) == set(expected)

    def test_from_string(self):
        assert OrderType("market") == OrderType.MARKET
        assert OrderType("limit") == OrderType.LIMIT


class TestOrderSide:

    def test_all_values(self):
        assert [s.value for s in OrderSide] == ["buy", "sell"]

    def test_is_string_enum(self):
        assert isinstance(OrderSide.BUY, str)


class TestOrderStatus:

    def test_all_values(self):
        expected = ["pending", "submitted", "partially_filled", "filled", "canceled", "rejected", "expired", "error"]
        actual = [s.value for s in OrderStatus]
        assert set(actual) == set(expected)


class TestOrderModel:

    def test_create_valid_market_order(self):
        order = Order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert order.symbol == "BTC/USDT"
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 0.1
        assert order.status == OrderStatus.PENDING

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Order(symbol="BTC/USDT")

    def test_reject_zero_quantity(self):
        with pytest.raises(ValidationError):
            Order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0,
            )

    def test_reject_negative_quantity(self):
        with pytest.raises(ValidationError):
            Order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=-1,
            )

    def test_reject_empty_symbol(self):
        with pytest.raises(ValidationError):
            Order(
                symbol="",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.1,
            )

    def test_serialization_round_trip(self):
        order = Order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        data = order.model_dump()
        order2 = Order(**data)
        assert order2.symbol == order.symbol
        assert order2.quantity == order.quantity

    def test_json_round_trip(self):
        order = Order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1.5,
        )
        json_str = order.model_dump_json()
        order2 = Order.model_validate_json(json_str)
        assert order2.side == OrderSide.SELL

    def test_optional_fields(self):
        order = Order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            strategy_name="momentum",
            agent_name="trader",
            notes="Test order",
        )
        assert order.strategy_name == "momentum"
        assert order.agent_name == "trader"

    def test_default_filled_quantity(self):
        order = Order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
        )
        assert order.filled_quantity == 0.0
        assert order.commission == 0.0
        assert order.slippage == 0.0


class TestMarketOrderModel:

    def test_create(self):
        order = MarketOrder(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=0.1,
        )
        assert order.order_type == OrderType.MARKET

    def test_serialization(self):
        order = MarketOrder(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=0.1,
        )
        data = order.model_dump()
        assert data["order_type"] == "market"


class TestLimitOrderModel:

    def test_create(self):
        order = LimitOrder(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
        )
        assert order.order_type == OrderType.LIMIT
        assert order.price == 50000.0

    def test_price_required(self):
        with pytest.raises(ValidationError):
            LimitOrder(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                quantity=0.1,
            )

    def test_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            LimitOrder(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                quantity=0.1,
                price=0,
            )


class TestStopOrderModel:

    def test_create(self):
        order = StopOrder(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            quantity=0.1,
            stop_price=48000.0,
        )
        assert order.order_type == OrderType.STOP
        assert order.stop_price == 48000.0

    def test_stop_price_required(self):
        with pytest.raises(ValidationError):
            StopOrder(
                symbol="BTC/USDT",
                side=OrderSide.SELL,
                quantity=0.1,
            )


class TestStopLimitOrderModel:

    def test_create(self):
        order = StopLimitOrder(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            quantity=0.1,
            price=50000.0,
            stop_price=51000.0,
        )
        assert order.order_type == OrderType.STOP_LIMIT
        assert order.price == 50000.0
        assert order.stop_price == 51000.0

    def test_both_prices_required(self):
        with pytest.raises(ValidationError):
            StopLimitOrder(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                quantity=0.1,
                price=50000.0,
                # Missing stop_price
            )


# ═══════════════════════════════════════════════════════════════════════
# 3. Market Data Types
# ═══════════════════════════════════════════════════════════════════════


class TestTimeFrame:

    def test_all_values(self):
        expected = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        actual = [t.value for t in TimeFrame]
        assert set(actual) == set(expected)

    def test_from_string(self):
        assert TimeFrame("1d") == TimeFrame.D1


class TestOHLCVModel:

    def test_create_valid(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        assert candle.symbol == "BTC/USDT"
        assert candle.open == 50000.0
        assert candle.high == 51000.0
        assert candle.volume == 1000.0

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            OHLCV(symbol="BTC/USDT")

    def test_prices_must_be_positive(self):
        with pytest.raises(ValidationError):
            OHLCV(
                symbol="BTC/USDT",
                timestamp=datetime.now(),
                open=0,  # Must be > 0
                high=51000,
                low=49500,
                close=50500,
                volume=1000,
            )

    def test_volume_can_be_zero(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            open=50000,
            high=51000,
            low=49500,
            close=50500,
            volume=0,
        )
        assert candle.volume == 0

    def test_serialization_round_trip(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        data = candle.model_dump()
        candle2 = OHLCV(**data)
        assert candle2.symbol == candle.symbol
        assert candle2.open == candle.open

    def test_json_round_trip(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0,
        )
        json_str = candle.model_dump_json()
        candle2 = OHLCV.model_validate_json(json_str)
        assert candle2.symbol == "BTC/USDT"


class TestTickerModel:

    def test_create_valid(self):
        ticker = Ticker(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            last_price=50000.0,
        )
        assert ticker.symbol == "BTC/USDT"
        assert ticker.last_price == 50000.0

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Ticker(symbol="BTC/USDT")

    def test_last_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            Ticker(
                symbol="BTC/USDT",
                timestamp=datetime.now(),
                last_price=0,
            )

    def test_optional_fields(self):
        ticker = Ticker(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            last_price=50000.0,
            bid=49999.0,
            ask=50001.0,
            volume_24h=1000000.0,
            change_pct_24h=2.5,
            vwap=50050.0,
        )
        assert ticker.bid == 49999.0
        assert ticker.change_pct_24h == 2.5

    def test_serialization_round_trip(self):
        ticker = Ticker(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            last_price=50000.0,
        )
        data = ticker.model_dump()
        ticker2 = Ticker(**data)
        assert ticker2.last_price == ticker.last_price


class TestOrderBookLevel:

    def test_create(self):
        level = OrderBookLevel(price=50000.0, quantity=1.5)
        assert level.price == 50000.0
        assert level.quantity == 1.5

    def test_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            OrderBookLevel(price=0, quantity=1.5)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            OrderBookLevel(price=50000.0, quantity=0)


class TestOrderBookModel:

    def test_create_valid(self):
        book = OrderBook(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            bids=[OrderBookLevel(price=49999.0, quantity=1.0)],
            asks=[OrderBookLevel(price=50001.0, quantity=0.5)],
        )
        assert book.symbol == "BTC/USDT"
        assert len(book.bids) == 1
        assert len(book.asks) == 1

    def test_empty_orderbook(self):
        book = OrderBook(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
        )
        assert book.bids == []
        assert book.asks == []

    def test_spread_optional(self):
        book = OrderBook(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            spread=2.0,
            mid_price=50000.0,
        )
        assert book.spread == 2.0


class TestMarketDataModel:

    def test_create_valid(self):
        md = MarketData(symbol="BTC/USDT")
        assert md.symbol == "BTC/USDT"
        assert md.timeframe == TimeFrame.D1
        assert md.ohlcv == []
        assert md.ticker is None
        assert md.orderbook is None

    def test_with_ohlcv(self):
        candle = OHLCV(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            open=50000, high=51000, low=49500, close=50500, volume=1000,
        )
        md = MarketData(symbol="BTC/USDT", ohlcv=[candle])
        assert len(md.ohlcv) == 1

    def test_with_ticker(self):
        ticker = Ticker(
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            last_price=50000.0,
        )
        md = MarketData(symbol="BTC/USDT", ticker=ticker)
        assert md.ticker is not None
        assert md.ticker.last_price == 50000.0

    def test_serialization_round_trip(self):
        md = MarketData(symbol="BTC/USDT", provider="binance")
        data = md.model_dump()
        md2 = MarketData(**data)
        assert md2.provider == "binance"


# ═══════════════════════════════════════════════════════════════════════
# 4. Position Types
# ═══════════════════════════════════════════════════════════════════════


class TestPositionSide:

    def test_all_values(self):
        expected = ["long", "short", "flat"]
        actual = [p.value for p in PositionSide]
        assert set(actual) == set(expected)


class TestPositionModel:

    def test_create_valid(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
        )
        assert pos.symbol == "BTC/USDT"
        assert pos.side == PositionSide.LONG
        assert pos.quantity == 0.1

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Position(symbol="BTC/USDT")

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValidationError):
            Position(
                symbol="BTC/USDT",
                side=PositionSide.LONG,
                quantity=0,
                entry_price=50000,
                current_price=50500,
                cost_basis=5000,
            )

    def test_entry_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            Position(
                symbol="BTC/USDT",
                side=PositionSide.LONG,
                quantity=0.1,
                entry_price=0,
                current_price=50500,
                cost_basis=5000,
            )

    def test_current_price_must_be_positive(self):
        with pytest.raises(ValidationError):
            Position(
                symbol="BTC/USDT",
                side=PositionSide.LONG,
                quantity=0.1,
                entry_price=50000,
                current_price=0,
                cost_basis=5000,
            )

    def test_update_price_long(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50000.0,
            cost_basis=5000.0,
        )
        pos.update_price(51000.0)
        assert pos.current_price == 51000.0
        assert pos.unrealized_pnl == pytest.approx(100.0)  # (51000 - 50000) * 0.1

    def test_update_price_short(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50000.0,
            cost_basis=5000.0,
        )
        pos.update_price(49000.0)
        assert pos.unrealized_pnl == pytest.approx(100.0)  # (50000 - 49000) * 0.1

    def test_serialization_round_trip(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
            stop_loss=48000.0,
            take_profit=55000.0,
        )
        data = pos.model_dump()
        pos2 = Position(**data)
        assert pos2.symbol == pos.symbol
        assert pos2.stop_loss == pos.stop_loss

    def test_json_round_trip(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.SHORT,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
            min_price=49000.0,  # Avoid float("inf") JSON serialization issue
        )
        json_str = pos.model_dump_json()
        pos2 = Position.model_validate_json(json_str)
        assert pos2.side == PositionSide.SHORT


class TestPortfolioModel:

    def test_create_valid(self):
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=800_000,
        )
        assert portfolio.initial_capital == 1_000_000
        assert portfolio.cash == 800_000
        assert portfolio.positions == {}
        assert portfolio.name == "default"
        assert portfolio.currency == "USD"

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Portfolio()

    def test_initial_capital_must_be_positive(self):
        with pytest.raises(ValidationError):
            Portfolio(initial_capital=0, cash=0)

    def test_cash_non_negative(self):
        with pytest.raises(ValidationError):
            Portfolio(initial_capital=1_000_000, cash=-1)

    def test_with_position(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
        )
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=995_000,
            positions={"BTC/USDT": pos},
        )
        assert "BTC/USDT" in portfolio.positions
        assert portfolio.is_invested is True

    def test_position_value_property(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
            market_value=5050.0,
        )
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=995_000,
            positions={"BTC/USDT": pos},
        )
        assert portfolio.position_value == 5050.0

    def test_is_not_invested_when_empty(self):
        portfolio = Portfolio(initial_capital=1_000_000, cash=1_000_000)
        assert portfolio.is_invested is False

    def test_recalculate(self):
        pos = Position(
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=0.1,
            entry_price=50000.0,
            current_price=50500.0,
            cost_basis=5000.0,
            unrealized_pnl=50.0,
            market_value=5050.0,
        )
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=995_000,
            positions={"BTC/USDT": pos},
        )
        portfolio.recalculate()
        assert portfolio.total_unrealized_pnl == 50.0
        assert portfolio.total_value == 995_000 + 5050.0

    def test_serialization_round_trip(self):
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=800_000,
            daily_pnl=500,
            weekly_pnl=2000,
        )
        data = portfolio.model_dump()
        portfolio2 = Portfolio(**data)
        assert portfolio2.initial_capital == portfolio.initial_capital
        assert portfolio2.daily_pnl == portfolio.daily_pnl

    def test_json_round_trip(self):
        portfolio = Portfolio(
            initial_capital=1_000_000,
            cash=800_000,
        )
        json_str = portfolio.model_dump_json()
        portfolio2 = Portfolio.model_validate_json(json_str)
        assert portfolio2.initial_capital == 1_000_000


# ═══════════════════════════════════════════════════════════════════════
# 5. Signal Types
# ═══════════════════════════════════════════════════════════════════════


class TestSignalType:

    def test_all_values(self):
        expected = ["buy", "sell", "hold", "close_long", "close_short", "exit_all"]
        actual = [s.value for s in SignalType]
        assert set(actual) == set(expected)


class TestSignalStrength:

    def test_all_values(self):
        expected = ["weak", "moderate", "strong", "very_strong"]
        actual = [s.value for s in SignalStrength]
        assert set(actual) == set(expected)


class TestSignalModel:

    def test_create_valid(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.8,
            source_agent="strategist",
        )
        assert signal.symbol == "BTC/USDT"
        assert signal.signal_type == SignalType.BUY
        assert signal.confidence == 0.8
        assert signal.source_agent == "strategist"

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Signal(symbol="BTC/USDT")

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Signal(
                symbol="BTC/USDT",
                signal_type=SignalType.BUY,
                confidence=1.5,
                source_agent="test",
            )

    def test_compute_strength_weak(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.2,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.WEAK

    def test_compute_strength_moderate(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.4,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.MODERATE

    def test_compute_strength_strong(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.7,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.STRONG

    def test_compute_strength_very_strong(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.9,
            source_agent="test",
        )
        assert signal.compute_strength() == SignalStrength.VERY_STRONG

    def test_serialization_round_trip(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.SELL,
            confidence=0.6,
            source_agent="researcher",
            price=50000.0,
            target_price=48000.0,
            stop_loss=51000.0,
            take_profit=46000.0,
        )
        data = signal.model_dump()
        signal2 = Signal(**data)
        assert signal2.signal_type == SignalType.SELL
        assert signal2.target_price == 48000.0

    def test_json_round_trip(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.8,
            source_agent="test",
        )
        json_str = signal.model_dump_json()
        signal2 = Signal.model_validate_json(json_str)
        assert signal2.symbol == "BTC/USDT"

    def test_optional_fields(self):
        signal = Signal(
            symbol="BTC/USDT",
            signal_type=SignalType.BUY,
            confidence=0.8,
            source_agent="test",
            timeframe="4h",
            source_strategy="momentum",
            reasoning="Strong uptrend",
            evidence={"rsi": 70, "macd": "bullish"},
            factors=["momentum", "trend"],
        )
        assert signal.timeframe == "4h"
        assert signal.source_strategy == "momentum"
        assert "rsi" in signal.evidence


# ═══════════════════════════════════════════════════════════════════════
# 6. Decision Types
# ═══════════════════════════════════════════════════════════════════════


class TestDecisionType:

    def test_all_values(self):
        expected = [
            "execute_buy", "execute_sell", "hold_position",
            "close_position", "veto", "defer", "emergency_exit",
        ]
        actual = [d.value for d in DecisionType]
        assert set(actual) == set(expected)


class TestConfluenceScore:

    def test_create_valid(self):
        score = ConfluenceScore(
            total_agents=3,
            bullish_agents=2,
            bearish_agents=1,
            neutral_agents=0,
            avg_confidence=0.7,
            weighted_score=0.5,
        )
        assert score.total_agents == 3
        assert score.bullish_agents == 2

    def test_compute_consensus_bullish(self):
        score = ConfluenceScore(total_agents=5, bullish_agents=3, bearish_agents=1, neutral_agents=1)
        assert score.compute_consensus() == "bullish"

    def test_compute_consensus_bearish(self):
        score = ConfluenceScore(total_agents=5, bullish_agents=1, bearish_agents=3, neutral_agents=1)
        assert score.compute_consensus() == "bearish"

    def test_compute_consensus_conflicted(self):
        score = ConfluenceScore(total_agents=5, bullish_agents=2, bearish_agents=2, neutral_agents=1)
        assert score.compute_consensus() == "conflicted"

    def test_compute_consensus_neutral(self):
        score = ConfluenceScore(total_agents=5, bullish_agents=1, bearish_agents=1, neutral_agents=3)
        assert score.compute_consensus() == "neutral"

    def test_compute_consensus_no_data(self):
        score = ConfluenceScore(total_agents=0)
        assert score.compute_consensus() == "no_data"

    def test_default_values(self):
        score = ConfluenceScore()
        assert score.total_agents == 0
        assert score.avg_confidence == 0.0
        assert score.weighted_score == 0.0

    def test_weighted_score_range(self):
        with pytest.raises(ValidationError):
            ConfluenceScore(weighted_score=2.0)  # Max is 1.0

    def test_serialization_round_trip(self):
        score = ConfluenceScore(
            total_agents=3,
            bullish_agents=2,
            avg_confidence=0.8,
            consensus="bullish",
        )
        data = score.model_dump()
        score2 = ConfluenceScore(**data)
        assert score2.total_agents == 3
        assert score2.consensus == "bullish"


class TestDecisionTable:

    def test_create_valid(self):
        table = DecisionTable(
            name="momentum_buy",
            conditions={"trend": "up", "rsi": "below_70"},
            action=DecisionType.EXECUTE_BUY,
        )
        assert table.name == "momentum_buy"
        assert table.action == DecisionType.EXECUTE_BUY

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            DecisionTable(conditions={}, action=DecisionType.HOLD_POSITION)

    def test_priority_non_negative(self):
        with pytest.raises(ValidationError):
            DecisionTable(
                name="test",
                conditions={},
                action=DecisionType.HOLD_POSITION,
                priority=-1,
            )


class TestDecisionModel:

    def test_create_valid(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
        )
        assert decision.symbol == "BTC/USDT"
        assert decision.decision_type == DecisionType.EXECUTE_BUY
        assert decision.confidence == 0.0

    def test_reject_missing_required(self):
        with pytest.raises(ValidationError):
            Decision(decision_type=DecisionType.HOLD_POSITION)

    def test_with_confluence(self):
        confluence = ConfluenceScore(
            total_agents=5,
            bullish_agents=3,
            avg_confidence=0.8,
        )
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            confluence=confluence,
            confidence=0.8,
        )
        assert decision.confluence.total_agents == 5

    def test_confidence_range(self):
        with pytest.raises(ValidationError):
            Decision(
                symbol="BTC/USDT",
                decision_type=DecisionType.EXECUTE_BUY,
                confidence=2.0,
            )

    def test_serialization_round_trip(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_SELL,
            confidence=0.6,
            reasoning="Bearish divergence",
            agent_votes={"researcher": "bearish", "trader": "bearish"},
        )
        data = decision.model_dump()
        decision2 = Decision(**data)
        assert decision2.decision_type == DecisionType.EXECUTE_SELL
        assert decision2.agent_votes["researcher"] == "bearish"

    def test_json_round_trip(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.VETO,
            reasoning="Risk limit exceeded",
        )
        json_str = decision.model_dump_json()
        decision2 = Decision.model_validate_json(json_str)
        assert decision2.decision_type == DecisionType.VETO

    def test_all_decision_types(self):
        for dt in DecisionType:
            decision = Decision(symbol="TEST", decision_type=dt)
            assert decision.decision_type == dt

    def test_order_params_optional(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            order_params={"quantity": 0.1, "price": 50000},
        )
        assert decision.order_params["quantity"] == 0.1

    def test_signals_list(self):
        decision = Decision(
            symbol="BTC/USDT",
            decision_type=DecisionType.EXECUTE_BUY,
            signals=[{"type": "momentum", "strength": "strong"}],
        )
        assert len(decision.signals) == 1
