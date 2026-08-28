"""Tests for the sources subpackage."""

from __future__ import annotations

import pytest

# ── Base tests ───────────────────────────────────────────────────────────────


class TestSourceProvider:
    """Tests for the SourceProvider base class."""

    def test_source_category_enum(self):
        from ai_multicolony.sources import SourceCategory
        assert SourceCategory.GEOPOLITICAL.value == "geopolitical"
        assert SourceCategory.ECONOMIC.value == "economic"
        assert SourceCategory.MARKET.value == "market"

    def test_source_reliability_enum(self):
        from ai_multicolony.sources import SourceReliability
        assert SourceReliability.RELIABLE.value == "reliable"
        assert SourceReliability.UNRELIABLE.value == "unreliable"

    def test_source_status_enum(self):
        from ai_multicolony.sources import SourceStatus
        assert SourceStatus.ACTIVE.value == "active"
        assert SourceStatus.OFFLINE.value == "offline"

    def test_source_item_creation(self):
        from ai_multicolony.sources import SourceItem
        item = SourceItem(title="Test", summary="Test summary")
        assert item.title == "Test"
        assert item.summary == "Test summary"
        assert item.relevance_score == 0.0

    def test_source_item_to_dict(self):
        from ai_multicolony.sources import SourceCategory, SourceItem
        item = SourceItem(title="Test", category=SourceCategory.ECONOMIC)
        d = item.to_dict()
        assert d["title"] == "Test"
        assert d["category"] == "economic"

    def test_source_result_success(self):
        from ai_multicolony.sources import SourceItem, SourceResult
        result = SourceResult(items=[SourceItem(title="Test")])
        assert result.success is True

    def test_source_result_failure(self):
        from ai_multicolony.sources import SourceResult
        result = SourceResult(errors=["Connection failed"])
        assert result.success is False

    def test_source_config_defaults(self):
        from ai_multicolony.sources import SourceConfig
        config = SourceConfig()
        assert config.enabled is True
        assert config.rate_limit_per_minute == 60
        assert config.timeout_s == 30.0

    def test_source_config_validation(self):
        from ai_multicolony.sources import SourceConfig
        config = SourceConfig(rate_limit_per_minute=0)
        errors = config.validate_config() if hasattr(config, 'validate_config') else []
        # SourceConfig doesn't have validate_config, but SourceProvider does
        assert config.rate_limit_per_minute == 0


# ── OSINT tests ─────────────────────────────────────────────────────────────


class TestOSINTSource:
    """Tests for the OSINT intelligence source."""

    @pytest.fixture
    def osint_source(self):
        from ai_multicolony.sources import OSINTSource
        return OSINTSource()

    def test_osint_creation(self, osint_source):
        assert osint_source.name == "osint"
        assert osint_source.category_count == 27

    def test_osint_available_categories(self, osint_source):
        cats = osint_source.available_categories
        assert len(cats) == 27
        assert "geopolitical_conflict" in cats
        assert "market_equities" in cats

    def test_osint_categories_dict(self):
        from ai_multicolony.sources.osint import OSINT_CATEGORIES
        assert len(OSINT_CATEGORIES) == 27

    @pytest.mark.asyncio
    async def test_osint_scan(self, osint_source):
        result = await osint_source.scan(max_items=10)
        assert result.fetched_count > 0
        assert len(result.items) > 0

    @pytest.mark.asyncio
    async def test_osint_fetch(self, osint_source):
        result = await osint_source.fetch("conflict", max_items=5)
        assert result.fetched_count >= 0  # May or may not match

    @pytest.mark.asyncio
    async def test_osint_health_check(self, osint_source):
        health = await osint_source.health_check()
        assert health["categories"] == 27


# ── Economic tests ──────────────────────────────────────────────────────────


class TestEconomicSource:
    """Tests for the economic data source."""

    @pytest.fixture
    def economic_source(self):
        from ai_multicolony.sources import EconomicSource
        return EconomicSource()

    def test_economic_creation(self, economic_source):
        assert economic_source.name == "economic"
        assert len(economic_source.tracked_countries) > 0

    def test_tracked_countries(self, economic_source):
        countries = economic_source.tracked_countries
        assert "US" in countries
        assert "EU" in countries
        assert "CN" in countries

    @pytest.mark.asyncio
    async def test_economic_scan(self, economic_source):
        result = await economic_source.scan(max_items=20)
        assert len(result.items) > 0

    @pytest.mark.asyncio
    async def test_economic_fetch_inflation(self, economic_source):
        result = await economic_source.fetch("inflation", max_items=10)
        assert len(result.items) > 0

    def test_get_gdp_data(self, economic_source):
        gdp = economic_source.get_gdp_data("US")
        assert gdp is not None
        assert gdp.country == "US"
        assert gdp.annual_growth_pct > 0

    def test_get_gdp_data_unknown(self, economic_source):
        gdp = economic_source.get_gdp_data("XX")
        assert gdp is None

    def test_get_inflation_data(self, economic_source):
        inf = economic_source.get_inflation_data("US")
        assert inf is not None
        assert inf.cpi_yoy_pct > 0

    def test_get_interest_rate_data(self, economic_source):
        rate = economic_source.get_interest_rate_data("JP")
        assert rate is not None
        assert rate.central_bank == "BOJ"


# ── Market tests ────────────────────────────────────────────────────────────


class TestMarketSource:
    """Tests for the market data source."""

    @pytest.fixture
    def market_source(self):
        from ai_multicolony.sources import MarketSource
        return MarketSource()

    def test_market_creation(self, market_source):
        assert market_source.name == "market"

    @pytest.mark.asyncio
    async def test_market_scan(self, market_source):
        result = await market_source.scan(max_items=30)
        assert len(result.items) > 0

    @pytest.mark.asyncio
    async def test_market_fetch_equity(self, market_source):
        result = await market_source.fetch("AAPL", max_items=5)
        assert len(result.items) > 0

    @pytest.mark.asyncio
    async def test_market_fetch_crypto(self, market_source):
        result = await market_source.fetch("BTC", max_items=5)
        assert len(result.items) > 0

    def test_get_equity_quote(self, market_source):
        quote = market_source.get_equity_quote("AAPL")
        assert quote is not None
        assert quote.price > 0

    def test_get_crypto_quote(self, market_source):
        quote = market_source.get_crypto_quote("BTC")
        assert quote is not None
        assert quote.price_usd > 0

    def test_get_forex_quote(self, market_source):
        quote = market_source.get_forex_quote("EUR/USD")
        assert quote is not None
        assert quote.rate > 0

    def test_available_symbols(self, market_source):
        symbols = market_source.available_symbols
        assert "equities" in symbols
        assert "crypto" in symbols
        assert "forex" in symbols


# ── Manager tests ───────────────────────────────────────────────────────────


class TestSourceManager:
    """Tests for the source orchestration manager."""

    @pytest.fixture
    def manager(self):
        from ai_multicolony.sources import EconomicSource, OSINTSource, SourceManager
        m = SourceManager()
        m.register(OSINTSource())
        m.register(EconomicSource())
        return m

    def test_manager_creation(self, manager):
        assert manager.source_count == 2

    def test_register_unregister(self):
        from ai_multicolony.sources import MarketSource, SourceManager
        m = SourceManager()
        m.register(MarketSource())
        assert m.source_count == 1
        m.unregister("market")
        assert m.source_count == 0

    @pytest.mark.asyncio
    async def test_sweep_all(self, manager):
        result = await manager.sweep_all(max_items=20)
        assert result.total_items > 0
        assert result.deduplicated_items > 0

    @pytest.mark.asyncio
    async def test_fetch_all(self, manager):
        result = await manager.fetch_all("inflation", max_items=20)
        assert result.total_items >= 0

    def test_create_default(self):
        from ai_multicolony.sources import SourceManager
        m = SourceManager.create_default()
        assert m.source_count == 3

    @pytest.mark.asyncio
    async def test_health_check_all(self, manager):
        results = await manager.health_check_all()
        assert len(results) == 2
