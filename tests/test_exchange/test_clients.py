"""Tests for Exchange REST Clients."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quant_nanggroe.exchange.clients.base_rest_client import (
    BaseRestClient,
    BalanceInfo,
    ExchangeCapability,
    KlineBar,
    OrderbookData,
    OrderbookEntry,
    OrderRequest,
    OrderResult,
    PositionInfo,
    RestClientConfig,
)
from quant_nanggroe.exchange.clients.binance_client import BinanceClient
from quant_nanggroe.exchange.clients.bybit_client import BybitClient
from quant_nanggroe.exchange.clients.okx_client import OKXClient


# ======================================================================
# Base Classes
# ======================================================================

class TestRestClientConfig:
    def test_defaults(self):
        config = RestClientConfig(exchange_id="test")
        assert config.rate_limit == 10
        assert config.timeout == 30
        assert config.testnet is False

    def test_custom(self):
        config = RestClientConfig(
            exchange_id="binance",
            api_key="test_key",
            api_secret="test_secret",
            base_url="https://api.binance.com",
            rate_limit=20,
        )
        assert config.api_key == "test_key"
        assert config.rate_limit == 20


class TestOrderRequest:
    def test_defaults(self):
        order = OrderRequest(symbol="BTCUSDT", side="buy", quantity=0.1)
        assert order.order_type == "limit"
        assert order.time_in_force == "GTC"

    def test_market_order(self):
        order = OrderRequest(symbol="BTCUSDT", side="sell", order_type="market", quantity=0.5)
        assert order.order_type == "market"


class TestOrderResult:
    def test_defaults(self):
        result = OrderResult()
        assert result.order_id == ""
        assert result.status == ""


class TestBalanceInfo:
    def test_defaults(self):
        info = BalanceInfo(asset="USDT")
        assert info.free == 0.0
        assert info.total == 0.0


class TestExchangeCapability:
    def test_spot_flag(self):
        cap = ExchangeCapability.SPOT
        assert bool(cap & ExchangeCapability.SPOT) is True

    def test_combined(self):
        cap = ExchangeCapability.SPOT | ExchangeCapability.FUTURES
        assert bool(cap & ExchangeCapability.SPOT) is True
        assert bool(cap & ExchangeCapability.FUTURES) is True
        assert bool(cap & ExchangeCapability.WEBSOCKET) is False


# ======================================================================
# Binance Client
# ======================================================================

class TestBinanceClient:
    def test_construction(self):
        config = RestClientConfig(exchange_id="binance", api_key="<placeholder>", api_secret="<placeholder>")
        client = BinanceClient(config)
        assert client.exchange_id == "binance"
        assert client.has_spot is True
        assert client.has_futures is True
        assert client.has_perpetuals is True

    def test_testnet_urls(self):
        config = RestClientConfig(exchange_id="binance", testnet=True)
        client = BinanceClient(config)
        assert "testnet" in client._spot_url


# ======================================================================
# Bybit Client
# ======================================================================

class TestBybitClient:
    def test_construction(self):
        config = RestClientConfig(exchange_id="bybit", api_key="<placeholder>", api_secret="<placeholder>")
        client = BybitClient(config)
        assert client.exchange_id == "bybit"
        assert client.has_spot is True
        assert client.has_futures is True

    def test_sign_v5(self):
        config = RestClientConfig(exchange_id="bybit", api_key="<placeholder>", api_secret="<placeholder>")
        client = BybitClient(config)
        headers = client._sign_v5({}, 1700000000000)
        assert "X-BAPI-API-KEY" in headers
        assert "X-BAPI-SIGN" in headers


# ======================================================================
# OKX Client
# ======================================================================

class TestOKXClient:
    def test_construction(self):
        config = RestClientConfig(
            exchange_id="okx",
            api_key="<placeholder>",
            api_secret="<placeholder>",
            passphrase="<placeholder>",
        )
        client = OKXClient(config)
        assert client.exchange_id == "okx"
        assert client.has_spot is True
        assert client.has_futures is True
        assert client.has_perpetuals is True
        assert client.has_websocket is True

    def test_sign(self):
        config = RestClientConfig(
            exchange_id="okx",
            api_key="<placeholder>",
            api_secret="<placeholder>",
            passphrase="<placeholder>",
        )
        client = OKXClient(config)
        sign = client._sign_okx("2024-01-01T00:00:00.000Z", "GET", "/api/v5/account/balance")
        assert isinstance(sign, str)
        assert len(sign) > 0
