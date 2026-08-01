"""Regression tests for paper broker floating (unrealized) P&L simulation.

Guards FIX C1: on fill, ``Position.unrealized_pnl`` must be derived from real
price movement (entry vs. mark) instead of the hardcoded ``0.0`` default.
"""

from __future__ import annotations

import pytest

from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.types.orders import OrderSide, OrderType

pytestmark = pytest.mark.asyncio


@pytest.fixture
def broker() -> PaperExchangeBroker:
    """Frictionless broker — isolates P&L math from slippage/commission."""
    return PaperExchangeBroker(
        initial_capital=1_000_000.0, slippage_bps=0.0, min_commission=0.0
    )


async def _long(broker: PaperExchangeBroker, symbol: str, price: float, qty: float):
    await broker.connect()
    broker.set_price(symbol, price)
    await broker.place_order(symbol, OrderSide.BUY, OrderType.MARKET, qty)
    return broker._positions[symbol]


async def test_fill_marks_slippage_as_floating_loss() -> None:
    """A fresh long marks at market, so entry slippage shows as floating loss."""
    broker = PaperExchangeBroker(initial_capital=1_000_000.0, slippage_bps=5.0)
    pos = await _long(broker, "BTC/USDT", 40_000.0, 1.0)
    assert pos.entry_price == pytest.approx(40_020.0)
    assert pos.unrealized_pnl == pytest.approx(-20.0)


async def test_long_floating_pnl_tracks_price_up(broker: PaperExchangeBroker) -> None:
    await _long(broker, "BTC/USDT", 40_000.0, 1.0)
    broker.set_price("BTC/USDT", 44_000.0)
    pos = broker._positions["BTC/USDT"]
    assert pos.unrealized_pnl == pytest.approx(4_000.0)
    assert pos.unrealized_pnl_pct == pytest.approx(10.0)
    assert pos.market_value == pytest.approx(44_000.0)


async def test_short_floating_pnl_inverts(broker: PaperExchangeBroker) -> None:
    await broker.connect()
    broker.set_price("ETH/USDT", 2_000.0)
    await broker.place_order("ETH/USDT", OrderSide.SELL, OrderType.MARKET, 10.0)
    broker.set_price("ETH/USDT", 1_800.0)
    assert broker._positions["ETH/USDT"].unrealized_pnl == pytest.approx(2_000.0)


async def test_portfolio_aggregates_floating_pnl(broker: PaperExchangeBroker) -> None:
    await _long(broker, "BTC/USDT", 40_000.0, 1.0)
    broker.set_price("BTC/USDT", 44_000.0)
    portfolio = await broker.get_portfolio()
    assert portfolio.total_unrealized_pnl == pytest.approx(4_000.0)


async def test_pending_limit_fill_computes_floating_pnl(
    broker: PaperExchangeBroker,
) -> None:
    """Fills via check_pending_orders() must also mark to market."""
    await broker.connect()
    broker.set_price("SOL/USDT", 100.0)
    await broker.place_order(
        "SOL/USDT", OrderSide.BUY, OrderType.LIMIT, 5.0, price=90.0
    )
    assert broker.pending_order_count == 1

    broker.set_price("SOL/USDT", 88.0)
    assert broker.check_pending_orders() == 1

    pos = broker._positions["SOL/USDT"]
    assert pos.entry_price == pytest.approx(90.0)
    assert pos.unrealized_pnl == pytest.approx(-10.0)


async def test_scale_in_averages_entry_before_marking(
    broker: PaperExchangeBroker,
) -> None:
    await _long(broker, "X/USDT", 100.0, 1.0)
    broker.set_price("X/USDT", 200.0)
    await broker.place_order("X/USDT", OrderSide.BUY, OrderType.MARKET, 1.0)

    pos = broker._positions["X/USDT"]
    assert pos.entry_price == pytest.approx(150.0)
    assert pos.quantity == pytest.approx(2.0)
    assert pos.unrealized_pnl == pytest.approx(100.0)


async def test_full_close_books_realized_and_clears_floating(
    broker: PaperExchangeBroker,
) -> None:
    await _long(broker, "X/USDT", 100.0, 1.0)
    broker.set_price("X/USDT", 150.0)
    await broker.place_order("X/USDT", OrderSide.SELL, OrderType.MARKET, 1.0)

    assert "X/USDT" not in broker._positions
    assert broker.realized_pnl == pytest.approx(50.0)
    portfolio = await broker.get_portfolio()
    assert portfolio.total_unrealized_pnl == pytest.approx(0.0)
