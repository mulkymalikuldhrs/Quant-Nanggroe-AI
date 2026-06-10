"""Comprehensive tests for the Exchange Factory.

Tests cover:
- Exchange creation for all supported exchanges
- Paper broker creation
- Market type routing and validation
- Configuration validation
- Exchange capability detection
- Error handling for unsupported exchanges
- Factory state tracking
- Custom options and overrides
"""

from __future__ import annotations

import pytest

from quant_nanggroe.exchange.factory import (
    ExchangeCapabilities,
    ExchangeFactory,
    ExchangeFactoryConfig,
    ExchangeFactoryError,
    MarketType,
    SUPPORTED_EXCHANGES,
    _CAPABILITY_REGISTRY,
)
from quant_nanggroe.exchange.base import ExchangeInterface
from quant_nanggroe.exchange.ccxt_broker import CCXTBroker
from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
from quant_nanggroe.exchange.alpaca_broker import AlpacaBroker
from quant_nanggroe.exchange.polymarket_broker import PolymarketBroker

# Exchanges that use CCXT as backend
_CCXT_EXCHANGES = {name for name, cap in _CAPABILITY_REGISTRY.items() if cap.ccxt_id}
# Non-CCXT exchanges with custom broker implementations
_NON_CCXT_EXCHANGES = {name for name, cap in _CAPABILITY_REGISTRY.items() if not cap.ccxt_id}


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture
def factory() -> ExchangeFactory:
    """Create a default factory."""
    return ExchangeFactory()


@pytest.fixture
def factory_with_sandbox() -> ExchangeFactory:
    """Create a factory with sandbox enabled."""
    config = ExchangeFactoryConfig(sandbox=True)
    return ExchangeFactory(config=config)


@pytest.fixture
def factory_with_futures_default() -> ExchangeFactory:
    """Create a factory with futures as default market type."""
    config = ExchangeFactoryConfig(default_market_type=MarketType.FUTURES)
    return ExchangeFactory(config=config)


# ======================================================================
# 1. Paper broker creation
# ======================================================================

class TestPaperBrokerCreation:

    def test_create_paper_broker(self, factory: ExchangeFactory):
        broker = factory.create("paper")
        assert isinstance(broker, PaperExchangeBroker)
        assert isinstance(broker, ExchangeInterface)

    def test_create_paper_broker_custom_capital(self, factory: ExchangeFactory):
        broker = factory.create("paper", initial_capital=50_000.0)
        assert isinstance(broker, PaperExchangeBroker)
        assert broker.cash == 50_000.0

    def test_create_paper_broker_case_insensitive(self, factory: ExchangeFactory):
        broker = factory.create("PAPER")
        assert isinstance(broker, PaperExchangeBroker)

    def test_create_paper_broker_with_whitespace(self, factory: ExchangeFactory):
        broker = factory.create("  paper  ")
        assert isinstance(broker, PaperExchangeBroker)


# ======================================================================
# 2. CCXT broker creation
# ======================================================================

class TestCCXTBrokerCreation:

    def test_create_binance(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)
        assert isinstance(broker, ExchangeInterface)
        assert broker.name == "binance"

    def test_create_okx(self, factory: ExchangeFactory):
        broker = factory.create("okx", api_key="test", api_secret="test", passphrase="pass")
        assert isinstance(broker, CCXTBroker)
        assert broker.name == "okx"

    def test_create_bybit(self, factory: ExchangeFactory):
        broker = factory.create("bybit", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)

    def test_create_bitget(self, factory: ExchangeFactory):
        broker = factory.create("bitget", api_key="test", api_secret="test", passphrase="pass")
        assert isinstance(broker, CCXTBroker)

    def test_create_kraken(self, factory: ExchangeFactory):
        broker = factory.create("kraken", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)

    def test_create_kucoin(self, factory: ExchangeFactory):
        broker = factory.create("kucoin", api_key="test", api_secret="test", passphrase="pass")
        assert isinstance(broker, CCXTBroker)

    def test_create_gate(self, factory: ExchangeFactory):
        broker = factory.create("gate", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)

    def test_create_coinbase(self, factory: ExchangeFactory):
        broker = factory.create("coinbase", api_key="test", api_secret="test", passphrase="pass")
        assert isinstance(broker, CCXTBroker)

    def test_create_case_insensitive(self, factory: ExchangeFactory):
        broker = factory.create("BINANCE", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)

    def test_create_with_whitespace(self, factory: ExchangeFactory):
        broker = factory.create("  binance  ", api_key="test", api_secret="test")
        assert isinstance(broker, CCXTBroker)

    def test_create_without_api_key(self, factory: ExchangeFactory):
        """Should create broker but warn about missing credentials."""
        broker = factory.create("binance")
        assert isinstance(broker, CCXTBroker)


# ======================================================================
# 3. Unsupported exchange errors
# ======================================================================

class TestUnsupportedExchange:

    def test_unsupported_exchange_raises(self, factory: ExchangeFactory):
        with pytest.raises(ExchangeFactoryError, match="Unsupported exchange"):
            factory.create("nonexistent_exchange")

    def test_error_includes_exchange_name(self, factory: ExchangeFactory):
        try:
            factory.create("fake_exchange")
        except ExchangeFactoryError as e:
            assert e.exchange == "fake_exchange"


# ======================================================================
# 4. Market type routing
# ======================================================================

class TestMarketTypeRouting:

    def test_default_market_type_is_spot(self, factory: ExchangeFactory):
        """Default market type should be spot."""
        assert factory.config.default_market_type == MarketType.SPOT

    def test_spot_market_type(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", market_type="spot")
        assert isinstance(broker, CCXTBroker)
        # Check CCXT options
        assert broker._config.options.get("defaultType") == "spot"

    def test_futures_market_type(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", market_type="futures")
        assert isinstance(broker, CCXTBroker)
        assert broker._config.options.get("defaultType") == "future"

    def test_perps_market_type(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", market_type="perps")
        assert isinstance(broker, CCXTBroker)
        assert broker._config.options.get("defaultType") == "swap"

    def test_invalid_market_type_raises(self, factory: ExchangeFactory):
        with pytest.raises(ExchangeFactoryError, match="Invalid market type"):
            factory.create("binance", api_key="test", api_secret="test", market_type="invalid")

    def test_futures_default_config(self, factory_with_futures_default: ExchangeFactory):
        broker = factory_with_futures_default.create(
            "binance", api_key="test", api_secret="test",
        )
        assert broker._config.options.get("defaultType") == "future"

    def test_unsupported_market_type_for_exchange(self, factory: ExchangeFactory):
        """Kraken doesn't support perps — should raise."""
        with pytest.raises(ExchangeFactoryError, match="does not support perpetual"):
            factory.create("kraken", api_key="test", api_secret="test", market_type="perps")

    def test_coinbase_no_perps(self, factory: ExchangeFactory):
        """Coinbase doesn't support perps."""
        with pytest.raises(ExchangeFactoryError, match="does not support perpetual"):
            factory.create("coinbase", api_key="test", api_secret="test", market_type="perps")


# ======================================================================
# 5. Configuration validation
# ======================================================================

class TestConfigurationValidation:

    def test_sandbox_config(self, factory_with_sandbox: ExchangeFactory):
        broker = factory_with_sandbox.create("binance", api_key="test", api_secret="test")
        assert broker._config.sandbox is True

    def test_sandbox_override(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", sandbox=True)
        assert broker._config.sandbox is True

    def test_rate_limit_override(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", rate_limit=10.0)
        assert broker._config.rate_limit == 10.0

    def test_timeout_override(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", timeout=60)
        assert broker._config.timeout == 60

    def test_retries_override(self, factory: ExchangeFactory):
        broker = factory.create("binance", api_key="test", api_secret="test", retries=5)
        assert broker._config.retries == 5

    def test_custom_options(self, factory: ExchangeFactory):
        config = ExchangeFactoryConfig(
            custom_options={"binance": {"testOption": True}},
        )
        f = ExchangeFactory(config=config)
        broker = f.create("binance", api_key="test", api_secret="test")
        assert broker._config.options.get("testOption") is True

    def test_extra_options(self, factory: ExchangeFactory):
        broker = factory.create(
            "binance",
            api_key="test",
            api_secret="test",
            extra_options={"customParam": "value"},
        )
        assert broker._config.options.get("customParam") == "value"


# ======================================================================
# 6. Exchange capability detection
# ======================================================================

class TestCapabilityDetection:

    def test_get_capabilities_binance(self, factory: ExchangeFactory):
        caps = factory.get_capabilities("binance")
        assert isinstance(caps, ExchangeCapabilities)
        assert caps.exchange_id == "binance"
        assert caps.supports_spot is True
        assert caps.supports_futures is True
        assert caps.supports_perps is True
        assert caps.requires_passphrase is False
        assert caps.max_leverage == 125.0

    def test_get_capabilities_okx(self, factory: ExchangeFactory):
        caps = factory.get_capabilities("okx")
        assert caps.requires_passphrase is True
        assert caps.supports_perps is True

    def test_get_capabilities_kraken(self, factory: ExchangeFactory):
        caps = factory.get_capabilities("kraken")
        assert caps.supports_perps is False
        assert caps.supports_futures is True

    def test_get_capabilities_coinbase(self, factory: ExchangeFactory):
        caps = factory.get_capabilities("coinbase")
        assert caps.supports_perps is False
        assert caps.supports_margin is False
        assert caps.max_leverage == 3.0

    def test_get_capabilities_unknown_raises(self, factory: ExchangeFactory):
        with pytest.raises(ExchangeFactoryError, match="Unknown exchange"):
            factory.get_capabilities("unknown_exchange")

    def test_capabilities_is_copy(self, factory: ExchangeFactory):
        """get_capabilities should return a copy, not the original."""
        caps1 = factory.get_capabilities("binance")
        caps2 = factory.get_capabilities("binance")
        assert caps1 == caps2
        caps1.max_leverage = 1.0  # Modify copy
        assert factory.get_capabilities("binance").max_leverage == 125.0


# ======================================================================
# 7. Listing and discovery
# ======================================================================

class TestListingAndDiscovery:

    def test_list_supported_exchanges(self):
        exchanges = ExchangeFactory.list_supported_exchanges()
        assert isinstance(exchanges, list)
        assert "binance" in exchanges
        assert "okx" in exchanges
        assert "kraken" in exchanges
        assert len(exchanges) == len(_CAPABILITY_REGISTRY)  # 10: 8 CCXT + alpaca + polymarket

    def test_list_by_capability_futures(self):
        exchanges = ExchangeFactory.list_exchanges_by_capability("supports_futures")
        assert "binance" in exchanges
        assert "kraken" in exchanges

    def test_list_by_capability_perps(self):
        exchanges = ExchangeFactory.list_exchanges_by_capability("supports_perps")
        assert "binance" in exchanges
        assert "okx" in exchanges
        assert "kraken" not in exchanges

    def test_list_by_capability_passphrase(self):
        exchanges = ExchangeFactory.list_exchanges_by_capability("requires_passphrase")
        assert "okx" in exchanges
        assert "kucoin" in exchanges
        assert "bitget" in exchanges
        assert "coinbase" in exchanges

    def test_supported_exchanges_frozenset(self):
        assert isinstance(SUPPORTED_EXCHANGES, frozenset)
        assert len(SUPPORTED_EXCHANGES) >= 10  # 8 CCXT + alpaca + polymarket


# ======================================================================
# 8. Factory state tracking
# ======================================================================

class TestFactoryState:

    def test_created_exchanges_empty_initially(self, factory: ExchangeFactory):
        assert factory.created_exchanges == {}

    def test_created_exchanges_tracks_creation(self, factory: ExchangeFactory):
        factory.create("paper")
        factory.create("binance", api_key="test", api_secret="test")
        created = factory.created_exchanges
        assert "paper" in created
        assert "binance" in created

    def test_created_exchanges_returns_copy(self, factory: ExchangeFactory):
        factory.create("paper")
        created = factory.created_exchanges
        created["extra"] = None  # Modify copy
        assert "extra" not in factory.created_exchanges

    def test_config_property(self, factory: ExchangeFactory):
        assert factory.config.default_market_type == MarketType.SPOT

    def test_custom_config(self):
        config = ExchangeFactoryConfig(sandbox=True, default_rate_limit=10.0)
        factory = ExchangeFactory(config=config)
        assert factory.config.sandbox is True
        assert factory.config.default_rate_limit == 10.0


# ======================================================================
# 9. Edge cases
# ======================================================================

class TestEdgeCases:

    def test_all_exchanges_creatable(self, factory: ExchangeFactory):
        """All supported exchanges should be creatable as correct broker types."""
        for name in SUPPORTED_EXCHANGES:
            broker = factory.create(name, api_key="test", api_secret="test")
            if name == "alpaca":
                assert isinstance(broker, AlpacaBroker), f"Alpaca should be AlpacaBroker"
            elif name == "polymarket":
                assert isinstance(broker, PolymarketBroker), f"Polymarket should be PolymarketBroker"
            else:
                assert isinstance(broker, CCXTBroker), f"Failed for {name}"

    def test_multiple_creations_same_exchange(self, factory: ExchangeFactory):
        """Creating the same exchange twice should work (overwrites in tracking)."""
        broker1 = factory.create("binance", api_key="test1", api_secret="test1")
        broker2 = factory.create("binance", api_key="test2", api_secret="test2")
        assert isinstance(broker1, CCXTBroker)
        assert isinstance(broker2, CCXTBroker)
        # The second creation overwrites in tracking
        assert factory.created_exchanges["binance"] is broker2

    def test_market_type_spot_for_ccxt_exchanges(self, factory: ExchangeFactory):
        """All CCXT exchanges should support spot."""
        for name in _CCXT_EXCHANGES:
            broker = factory.create(
                name, api_key="test", api_secret="test", market_type="spot",
            )
            assert isinstance(broker, CCXTBroker), f"Spot failed for {name}"

    def test_factory_config_validation(self):
        """Factory config should validate parameters."""
        config = ExchangeFactoryConfig(default_rate_limit=10.0)
        assert config.default_rate_limit == 10.0

    def test_capability_registry_completeness(self):
        """Capability registry should have entries for all supported exchanges."""
        for name in SUPPORTED_EXCHANGES:
            assert name in _CAPABILITY_REGISTRY, f"Missing capability for {name}"

    def test_market_type_enum_values(self):
        assert MarketType.SPOT.value == "spot"
        assert MarketType.FUTURES.value == "futures"
        assert MarketType.PERPS.value == "perps"
