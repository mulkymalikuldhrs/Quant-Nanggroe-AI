"""Comprehensive tests for PaperExchangeBroker - matches actual implementation."""

import unittest
import asyncio
import numpy as np
import pandas as pd

from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.types.orders import Order, OrderSide, OrderType, OrderStatus
from quant_nanggroe.types.positions import Position, PositionSide
from quant_nanggroe.types.market import OHLCV, Ticker, TimeFrame


class TestPaperExchangeBrokerInit(unittest.TestCase):
    """Tests for PaperExchangeBroker initialization."""

    def test_default_initialization(self):
        broker = PaperExchangeBroker()
        self.assertAlmostEqual(broker.cash, 1_000_000.0)
        self.assertEqual(broker._commission_rate, 0.001)
        self.assertEqual(broker._slippage_bps, 5.0)
        self.assertEqual(broker._min_commission, 1.0)
        self.assertEqual(broker._default_price, 100.0)

    def test_custom_initialization(self):
        broker = PaperExchangeBroker(
            initial_capital=100_000.0,
            commission_rate=0.002,
            slippage_bps=10.0,
            min_commission=0.5,
            default_price=50.0,
        )
        self.assertEqual(broker.cash, 100_000.0)
        self.assertEqual(broker._commission_rate, 0.002)
        self.assertEqual(broker._slippage_bps, 10.0)
        self.assertEqual(broker._min_commission, 0.5)
        self.assertEqual(broker._default_price, 50.0)

    def test_state_initialized(self):
        broker = PaperExchangeBroker()
        self.assertFalse(broker.is_connected)
        self.assertEqual(len(broker._orders), 0)
        self.assertEqual(len(broker._positions), 0)


class TestPaperExchangeBrokerConnection(unittest.TestCase):
    """Tests for connection lifecycle."""

    def test_connect(self):
        broker = PaperExchangeBroker()
        connected = asyncio.run(broker.connect())
        self.assertTrue(connected)
        self.assertTrue(broker.is_connected)

    def test_disconnect(self):
        broker = PaperExchangeBroker()
        asyncio.run(broker.connect())
        asyncio.run(broker.disconnect())
        self.assertFalse(broker.is_connected)

    def test_connect_idempotent(self):
        broker = PaperExchangeBroker()
        asyncio.run(broker.connect())
        asyncio.run(broker.connect())
        self.assertTrue(broker.is_connected)


class TestPaperExchangeBrokerPriceSimulation(unittest.TestCase):
    """Tests for price simulation helpers."""

    def test_set_price(self):
        broker = PaperExchangeBroker()
        broker.set_price("BTC/USDT", 42000.0)
        self.assertEqual(broker.get_price("BTC/USDT"), 42000.0)

    def test_set_price_invalid(self):
        broker = PaperExchangeBroker()
        with self.assertRaises(ValueError):
            broker.set_price("BTC/USDT", -100.0)
        with self.assertRaises(ValueError):
            broker.set_price("BTC/USDT", 0.0)

    def test_get_price_default(self):
        broker = PaperExchangeBroker(default_price=50.0)
        self.assertEqual(broker.get_price("UNKNOWN"), 50.0)

    def test_set_price_updates_ticker(self):
        broker = PaperExchangeBroker()
        broker.set_price("BTC/USDT", 42000.0)
        ticker = asyncio.run(broker.get_ticker("BTC/USDT"))
        self.assertEqual(ticker.last_price, 42000.0)
        self.assertEqual(ticker.symbol, "BTC/USDT")


class TestPaperExchangeBrokerMarketOrders(unittest.TestCase):
    """Tests for market order execution."""

    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(self.broker.connect())
        self.broker.set_price("BTC/USDT", 40000.0)

    def test_place_market_buy_order(self):
        order = asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(order.filled_quantity, 1.0)
        self.assertIsNotNone(order.average_fill_price)

    def test_place_market_sell_order(self):
        # First buy some BTC
        self.broker.set_price("BTC/USDT", 40000.0)
        asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        # Then sell
        self.broker.set_price("BTC/USDT", 41000.0)
        order = asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)

    def test_market_order_insufficient_funds(self):
        broker = PaperExchangeBroker(initial_capital=100.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        with self.assertRaises(Exception):  # OrderError or InsufficientFundsError
            asyncio.run(broker.place_order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=10.0,
            ))

    def test_market_order_not_connected(self):
        broker = PaperExchangeBroker()
        broker.set_price("BTC/USDT", 40000.0)
        # Not connected - order should fail
        import uuid
        order = Order(
            id=str(uuid.uuid4()),
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
            status=OrderStatus.PENDING,
        )
        broker._orders[order.id] = order
        # place_order checks connection
        with self.assertRaises(Exception):
            asyncio.run(broker.place_order(
                symbol="BTC/USDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
            ))


class TestPaperExchangeBrokerLimitOrders(unittest.TestCase):
    """Tests for limit order execution."""

    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(self.broker.connect())

    def test_place_limit_order_buy_immediate_fill(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        # Limit buy at price above current - should fill
        order = asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=41000.0,  # Above current price
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)

    def test_place_limit_order_buy_pending(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        # Limit buy at price below current - should be pending
        order = asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=39000.0,  # Below current price
        ))
        self.assertEqual(order.status, OrderStatus.SUBMITTED)

    def test_place_limit_order_sell_immediate_fill(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        # First buy
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        # Limit sell at price below current - should fill
        order = asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=39000.0,
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)


class TestPaperExchangeBrokerStopOrders(unittest.TestCase):
    """Tests for stop order execution."""

    def test_place_stop_order_buy_triggered(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 41000.0)  # Above stop
        order = asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.STOP,
            quantity=1.0,
            stop_price=40000.0,
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)

    def test_place_stop_order_sell_triggered(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 39000.0)  # Below stop
        order = asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.STOP,
            quantity=1.0,
            stop_price=40000.0,
        ))
        self.assertEqual(order.status, OrderStatus.FILLED)


class TestPaperExchangeBrokerPositions(unittest.TestCase):
    """Tests for position management."""

    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(self.broker.connect())
        self.broker.set_price("BTC/USDT", 40000.0)

    def test_get_positions_empty(self):
        positions = asyncio.run(self.broker.get_positions())
        self.assertEqual(len(positions), 0)

    def test_get_positions_after_buy(self):
        asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        positions = asyncio.run(self.broker.get_positions())
        self.assertEqual(len(positions), 1)
        pos = positions[0]
        self.assertEqual(pos.symbol, "BTC/USDT")
        self.assertEqual(pos.side, PositionSide.LONG)

    def test_get_portfolio(self):
        asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        portfolio = asyncio.run(self.broker.get_portfolio())
        self.assertEqual(portfolio.name, "paper")
        self.assertEqual(portfolio.initial_capital, 100_000.0)


class TestPaperExchangeBrokerPnL(unittest.TestCase):
    """Tests for P&L tracking."""

    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(self.broker.connect())

    def test_realized_pnl_initial(self):
        self.assertEqual(self.broker.realized_pnl, 0.0)

    def test_commission_tracking(self):
        self.assertEqual(self.broker.total_commission, 0.0)
        self.assertEqual(self.broker.total_slippage, 0.0)

    def test_positive_pnl_sell_high(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        # Buy
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        # Sell higher
        broker.set_price("BTC/USDT", 42000.0)
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        # Should have positive PnL
        self.assertGreater(broker.realized_pnl, 0)


class TestPaperExchangeBrokerBalance(unittest.TestCase):
    """Tests for balance queries."""

    def test_get_balance_no_positions(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        balance = asyncio.run(broker.get_balance())
        self.assertEqual(balance.get("USDT"), 100_000.0)

    def test_get_balance_with_positions(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        balance = asyncio.run(broker.get_balance())
        self.assertIn("USDT", balance)


class TestPaperExchangeBrokerOrderManagement(unittest.TestCase):
    """Tests for order management."""

    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(self.broker.connect())

    def test_cancel_order(self):
        self.broker.set_price("BTC/USDT", 40000.0)
        order = asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=39000.0,  # Will be pending
        ))
        canceled = asyncio.run(self.broker.cancel_order(order.id))
        self.assertEqual(canceled.status, OrderStatus.CANCELED)

    def test_get_order(self):
        self.broker.set_price("BTC/USDT", 40000.0)
        order = asyncio.run(self.broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        retrieved = asyncio.run(self.broker.get_order(order.id))
        self.assertEqual(retrieved.id, order.id)

    def test_get_order_not_found(self):
        with self.assertRaises(Exception):
            asyncio.run(self.broker.get_order("nonexistent"))


class TestPaperExchangeBrokerOrderBook(unittest.TestCase):
    """Tests for order book generation."""

    def test_get_orderbook(self):
        broker = PaperExchangeBroker()
        broker.set_price("BTC/USDT", 40000.0)
        ob = asyncio.run(broker.get_orderbook("BTC/USDT", limit=10))
        self.assertEqual(ob.symbol, "BTC/USDT")
        self.assertEqual(len(ob.bids), 10)
        self.assertEqual(len(ob.asks), 10)
        self.assertIsNotNone(ob.spread)
        self.assertIsNotNone(ob.mid_price)

    def test_get_orderbook_default_price(self):
        broker = PaperExchangeBroker(default_price=100.0)
        ob = asyncio.run(broker.get_orderbook("UNKNOWN", limit=5))
        self.assertEqual(ob.mid_price, 100.0)


class TestPaperExchangeBrokerOHLCV(unittest.TestCase):
    """Tests for OHLCV handling."""

    def test_add_ohlcv(self):
        broker = PaperExchangeBroker()
        candle = OHLCV(
            timestamp=pd.Timestamp.now(),
            open=40000.0,
            high=40100.0,
            low=39900.0,
            close=40050.0,
            volume=1000.0,
        )
        broker.add_ohlcv("BTC/USDT", candle)
        self.assertEqual(len(broker._ohlcv_history["BTC/USDT"]), 1)

    def test_get_ohlcv_empty(self):
        broker = PaperExchangeBroker()
        result = asyncio.run(broker.get_ohlcv("UNKNOWN"))
        self.assertEqual(len(result), 0)


class TestPaperExchangeBrokerTradeHistory(unittest.TestCase):
    """Tests for trade history tracking."""

    def test_trade_history_recorded(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        trades = asyncio.run(broker.get_trades("BTC/USDT"))
        self.assertEqual(len(trades), 1)

    def test_trade_history_filter_by_symbol(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        broker.set_price("ETH/USDT", 2000.0)
        # Buy BTC
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        # Buy ETH
        asyncio.run(broker.place_order(
            symbol="ETH/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10.0,
        ))
        btc_trades = asyncio.run(broker.get_trades("BTC/USDT"))
        eth_trades = asyncio.run(broker.get_trades("ETH/USDT"))
        self.assertEqual(len(btc_trades), 1)
        self.assertEqual(len(eth_trades), 1)


class TestPaperExchangeBrokerSlippage(unittest.TestCase):
    """Tests for slippage application."""

    def test_slippage_buy(self):
        broker = PaperExchangeBroker(slippage_bps=10.0)
        # Buying pushes price up
        price = broker._apply_slippage(100.0, OrderSide.BUY)
        self.assertGreater(price, 100.0)

    def test_slippage_sell(self):
        broker = PaperExchangeBroker(slippage_bps=10.0)
        # Selling pushes price down
        price = broker._apply_slippage(100.0, OrderSide.SELL)
        self.assertLess(price, 100.0)

    def test_slippage_amount_tracking(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0, slippage_bps=10.0)
        asyncio.run(broker.connect())
        broker.set_price("BTC/USDT", 40000.0)
        asyncio.run(broker.place_order(
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        ))
        self.assertGreater(broker.total_slippage, 0)


class TestPaperExchangeBrokerCheckPendingOrders(unittest.TestCase):
    """Tests for pending order checking."""

    def test_check_pending_orders_fills_limit(self):
        broker = PaperExchangeBroker(initial_capital=100_000.0)
        asyncio.run(broker.connect())
        # Place pending limit order
        import uuid
        from datetime import datetime, timezone
        order = Order(
            id=str(uuid.uuid4()),
            symbol="BTC/USDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=41000.0,  # Will fill if price >= this
            status=OrderStatus.SUBMITTED,
            created_at=datetime.now(tz=timezone.utc),
        )
        broker._pending_orders[order.id] = order
        broker.set_price("BTC/USDT", 42000.0)  # Price crosses limit
        filled = broker.check_pending_orders()
        self.assertGreater(filled, 0)


class TestPaperExchangeBrokerProperties(unittest.TestCase):
    """Tests for broker properties."""

    def test_order_count(self):
        broker = PaperExchangeBroker()
        self.assertEqual(broker.order_count, 0)

    def test_pending_order_count(self):
        broker = PaperExchangeBroker()
        self.assertEqual(broker.pending_order_count, 0)

    def test_total_commission(self):
        broker = PaperExchangeBroker()
        self.assertEqual(broker.total_commission, 0.0)

    def test_total_slippage(self):
        broker = PaperExchangeBroker()
        self.assertEqual(broker.total_slippage, 0.0)


if __name__ == "__main__":
    unittest.main()