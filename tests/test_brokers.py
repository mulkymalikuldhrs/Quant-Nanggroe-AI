"""Tests for the quantdinger-inspired multi-broker abstraction layer."""
from __future__ import annotations

import pytest

from quant_nanggroe.connectors.broker_base import (
    BrokerConnector,
    BrokerType,
    Order,
    Position,
)


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


