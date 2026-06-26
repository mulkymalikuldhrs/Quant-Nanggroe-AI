"""Tests for the quantdinger-inspired multi-broker abstraction layer."""
from __future__ import annotations

import pytest

from quant_nanggroe.connectors.broker_base import (
    BrokerConnector,
    BrokerType,
    MultiBrokerManager,
    Order,
    Position,
)
from quant_nanggroe.connectors.simulated import SimulatedBroker


class TestBrokerType:
    def test_values(self):
        assert BrokerType.CRYPTO.value == "crypto"
        assert BrokerType.IBKR.value == "ibkr"
        assert BrokerType.MT5.value == "mt5"
        assert BrokerType.SIMULATED.value == "simulated"

    def test_all_values_unique(self):
        values = [t.value for t in BrokerType]
        assert len(values) == len(set(values))


class TestOrder:
    def test_default_broker(self):
        o = Order(symbol="BTC/USDT", side="buy", quantity=1.0, order_type="market")
        assert o.broker == "simulated"

    def test_with_price(self):
        o = Order(symbol="XAUUSD", side="sell", quantity=0.5, order_type="limit", price=1950.0)
        assert o.price == 1950.0

    def test_required_fields(self):
        o = Order(symbol="ETH/USDT", side="buy", quantity=2.0, order_type="market")
        assert o.symbol == "ETH/USDT"
        assert o.side == "buy"
        assert o.quantity == 2.0


class TestPosition:
    def test_default_pnl(self):
        p = Position(symbol="BTC/USDT", quantity=1.0, entry_price=50000.0, current_price=51000.0)
        assert p.pnl == 0.0

    def test_default_broker(self):
        p = Position(symbol="XAUUSD", quantity=10.0, entry_price=1900.0, current_price=1910.0)
        assert p.broker == "simulated"


class TestSimulatedBroker:
    def test_connect(self):
        broker = SimulatedBroker()
        assert broker.connect() is True
        assert broker.connected is True

    def test_disconnect(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.disconnect()
        assert broker.connected is False
        assert broker.get_positions() == []

    def test_initial_balance(self):
        broker = SimulatedBroker(initial_balance=50000.0)
        assert broker.get_balance() == 50000.0

    def test_default_balance(self):
        broker = SimulatedBroker()
        assert broker.get_balance() == 100_000.0

    def test_place_buy_order(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("BTC/USDT", 50000.0)
        order_id = broker.place_order(Order("BTC/USDT", "buy", 1.0, "market"))
        assert order_id is not None
        assert len(order_id) > 0

    def test_buy_order_reduces_balance(self):
        broker = SimulatedBroker(initial_balance=100000.0)
        broker.connect()
        broker.update_price("AAPL", 150.0)
        broker.place_order(Order("AAPL", "buy", 10.0, "market"))
        assert broker.get_balance() == 100000.0 - 150.0 * 10.0

    def test_sell_order_increases_balance(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("AAPL", 150.0)
        broker.place_order(Order("AAPL", "buy", 10.0, "market"))
        balance_after_buy = broker.get_balance()
        broker.place_order(Order("AAPL", "sell", 5.0, "market"))
        assert broker.get_balance() == balance_after_buy + 150.0 * 5.0

    def test_sell_insufficient_position_raises(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("AAPL", 150.0)
        with pytest.raises(ValueError, match="Insufficient position quantity"):
            broker.place_order(Order("AAPL", "sell", 1.0, "market"))

    def test_buy_insufficient_funds_raises(self):
        broker = SimulatedBroker(initial_balance=100.0)
        broker.connect()
        broker.update_price("BTC/USDT", 50000.0)
        with pytest.raises(ValueError, match="Insufficient funds"):
            broker.place_order(Order("BTC/USDT", "buy", 10.0, "market"))

    def test_get_positions_after_buy(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("AAPL", 150.0)
        broker.place_order(Order("AAPL", "buy", 10.0, "market"))
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].quantity == 10.0

    def test_get_positions_empty(self):
        broker = SimulatedBroker()
        broker.connect()
        assert broker.get_positions() == []

    def test_update_price_updates_pnl(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("AAPL", 150.0)
        broker.place_order(Order("AAPL", "buy", 10.0, "market"))
        broker.update_price("AAPL", 160.0)
        positions = broker.get_positions()
        assert positions[0].pnl == 10.0 * 10.0

    def test_limit_order_price(self):
        broker = SimulatedBroker()
        broker.connect()
        broker.update_price("AAPL", 150.0)
        broker.place_order(Order("AAPL", "buy", 5.0, "limit", price=148.0))
        assert broker.get_balance() == 100000.0 - 148.0 * 5.0


class TestMultiBrokerManager:
    def test_register_broker(self):
        manager = MultiBrokerManager()
        broker = SimulatedBroker()
        manager.register("sim", broker)
        assert "sim" in manager.brokers

    def test_register_multiple(self):
        manager = MultiBrokerManager()
        manager.register("a", SimulatedBroker())
        manager.register("b", SimulatedBroker(initial_balance=50000.0))
        assert len(manager.brokers) == 2

    def test_place_order_across_brokers(self):
        manager = MultiBrokerManager()
        b1 = SimulatedBroker(initial_balance=100000.0)
        b2 = SimulatedBroker(initial_balance=50000.0)
        b1.connect()
        b2.connect()
        b1.update_price("BTC/USDT", 50000.0)
        b2.update_price("BTC/USDT", 50000.0)
        manager.register("broker1", b1)
        manager.register("broker2", b2)

        results = manager.place_order(Order("BTC/USDT", "buy", 0.5, "market"))
        assert "broker1" in results
        assert "broker2" in results
        assert "error" not in results["broker1"].lower()
        assert "error" not in results["broker2"].lower()

    def test_place_order_error_isolation(self):
        manager = MultiBrokerManager()
        working = SimulatedBroker()
        working.connect()
        working.update_price("AAPL", 150.0)

        class FailingBroker(BrokerConnector):
            def connect(self) -> bool:
                return True
            def place_order(self, order: Order) -> str:
                raise RuntimeError("Connection failed")
            def get_positions(self):
                return []
            def get_balance(self) -> float:
                return 0.0
            def disconnect(self): ...

        failing = FailingBroker()
        manager.register("working", working)
        manager.register("failing", failing)

        results = manager.place_order(Order("AAPL", "buy", 1.0, "market"))
        assert "working" in results
        assert "failing" in results
        assert "error" not in results["working"]
        assert "error" in results["failing"]

    def test_aggregate_positions_empty(self):
        manager = MultiBrokerManager()
        assert manager.aggregate_positions() == {}

    def test_aggregate_positions(self):
        manager = MultiBrokerManager()
        b1 = SimulatedBroker()
        b2 = SimulatedBroker()
        b1.connect()
        b2.connect()
        b1.update_price("AAPL", 150.0)
        b2.update_price("GOOGL", 2800.0)
        b1.place_order(Order("AAPL", "buy", 10.0, "market"))
        b2.place_order(Order("GOOGL", "buy", 5.0, "market"))
        manager.register("b1", b1)
        manager.register("b2", b2)

        agg = manager.aggregate_positions()
        assert len(agg["b1"]) == 1
        assert len(agg["b2"]) == 1
        assert agg["b1"][0].symbol == "AAPL"
        assert agg["b2"][0].symbol == "GOOGL"
