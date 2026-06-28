"""Tests for PaperExchangeBroker."""
import unittest
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.types.orders import OrderSide, OrderType
from quant_nanggroe.types.market import OHLCV
from datetime import datetime, timezone


class TestPaperExchangeBroker(unittest.TestCase):
    def setUp(self):
        self.broker = PaperExchangeBroker(initial_capital=10000.0)

    def test_initial_capital(self):
        self.assertEqual(self.broker.cash, 10000.0)

    def test_get_price_default(self):
        self.assertGreater(self.broker.get_price("BTC/USDT"), 0)

    def test_add_ohlcv(self):
        now = datetime.now(timezone.utc)
        ohlcv = OHLCV(symbol="BTC/USDT", timestamp=now, open=100.0, high=101.0, low=99.0, close=100.5, volume=1000.0)
        self.broker.add_ohlcv("BTC/USDT", ohlcv)
        self.assertGreater(self.broker.get_price("BTC/USDT"), 0)

    async def test_place_order(self):
        self.broker = PaperExchangeBroker(initial_capital=10000.0)
        ohlcv = OHLCV(symbol="BTC/USDT", timestamp=datetime.now(timezone.utc), open=67000.0, high=68000.0, low=66000.0, close=67000.0, volume=1000.0)
        self.broker.add_ohlcv("BTC/USDT", ohlcv)
        order = await self.broker.place_order(symbol="BTC/USDT", side=OrderSide.BUY, order_type=OrderType.MARKET, quantity=0.5)
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "BTC/USDT")

    def test_get_portfolio_no_trades(self):
        import asyncio
        p = asyncio.run(self.broker.get_portfolio())
        self.assertEqual(p.total_value, 10000.0)

    def test_str(self):
        s = str(self.broker)
        self.assertIn("PaperExchangeBroker", s)


if __name__ == "__main__":
    unittest.main()
