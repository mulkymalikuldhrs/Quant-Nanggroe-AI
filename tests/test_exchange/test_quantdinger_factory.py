"""Comprehensive tests for the QuantDinger Multi-Exchange Factory.

All tests use mocked exchange/data source responses — no real API calls.

Tests cover:
- MarketType enum values
- BaseExchangeAdapter abstract interface
- _CCXTAdapter with mocked ccxt
- All 9 exchange adapter classes
- _YFinanceAdapter with mocked yfinance
- _AKShareAdapter with mocked akshare
- _FuturesAdapter and _ForexAdapter
- QuantDingerFactory initialization
- create_exchange_adapter for all 9 exchanges
- create_data_source for all market types
- get_kline convenience method
- Adapter caching
- close_all
- Error handling for unsupported exchanges
- get_supported_exchanges / get_supported_market_types
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quant_nanggroe.exchange.quantdinger_factory import (
    _DATA_SOURCE_ADAPTERS,
    _EXCHANGE_ADAPTERS,
    BaseExchangeAdapter,
    BinanceAdapter,
    BitfinexAdapter,
    BitgetAdapter,
    BybitAdapter,
    CoinbaseAdapter,
    GateAdapter,
    KrakenAdapter,
    KuCoinAdapter,
    MarketType,
    OKXAdapter,
    QuantDingerFactory,
    _adapter_cache,
    _AKShareAdapter,
    _CCXTAdapter,
    _ForexAdapter,
    _FuturesAdapter,
    _YFinanceAdapter,
)

# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the adapter cache before each test."""
    _adapter_cache.clear()
    yield
    _adapter_cache.clear()


@pytest.fixture
def factory():
    """Create a default QuantDingerFactory."""
    return QuantDingerFactory()


@pytest.fixture
def factory_with_config():
    """Create a QuantDingerFactory with default config."""
    return QuantDingerFactory(default_config={"api_key": "test", "api_secret": "test"})


# ======================================================================
# 1. MarketType Enum
# ======================================================================

class TestMarketType:
    """Tests for MarketType enum."""

    def test_all_values(self):
        expected = ["crypto", "us_stock", "cn_stock", "futures", "forex"]
        actual = [m.value for m in MarketType]
        for val in expected:
            assert val in actual

    def test_enum_is_string(self):
        assert isinstance(MarketType.CRYPTO, str)
        assert MarketType.CRYPTO == "crypto"

    def test_from_value(self):
        assert MarketType("crypto") == MarketType.CRYPTO
        assert MarketType("us_stock") == MarketType.US_STOCK

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            MarketType("invalid_type")

    def test_all_unique(self):
        values = [m.value for m in MarketType]
        assert len(values) == len(set(values))


# ======================================================================
# 2. BaseExchangeAdapter (Abstract)
# ======================================================================

class TestBaseExchangeAdapter:
    """Tests for the abstract BaseExchangeAdapter."""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseExchangeAdapter()

    def test_subclass_must_implement_methods(self):
        class IncompleteAdapter(BaseExchangeAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()

    def test_complete_subclass(self):
        class CompleteAdapter(BaseExchangeAdapter):
            async def get_kline(self, symbol, timeframe="1h", limit=100, before_time=None):
                return []
            async def get_ticker_price(self, symbol):
                return 0.0
            async def get_orderbook(self, symbol, limit=20):
                return {"bids": [], "asks": []}
            def get_exchange_name(self):
                return "test"
            def get_supported_symbols(self):
                return []

        adapter = CompleteAdapter()
        assert adapter.get_exchange_name() == "test"


# ======================================================================
# 3. Exchange Adapters
# ======================================================================

class TestExchangeAdapters:
    """Tests for individual exchange adapter classes."""

    def test_binance_adapter(self):
        adapter = BinanceAdapter()
        assert adapter.get_exchange_name() == "binance"
        assert "BTC/USDT" in adapter.get_supported_symbols()
        assert "BNB/USDT" in adapter.get_supported_symbols()

    def test_bybit_adapter(self):
        adapter = BybitAdapter()
        assert adapter.get_exchange_name() == "bybit"
        assert "BTC/USDT" in adapter.get_supported_symbols()

    def test_okx_adapter(self):
        adapter = OKXAdapter()
        assert adapter.get_exchange_name() == "okx"
        assert "OKB/USDT" in adapter.get_supported_symbols()

    def test_kucoin_adapter(self):
        adapter = KuCoinAdapter()
        assert adapter.get_exchange_name() == "kucoin"
        assert "KCS/USDT" in adapter.get_supported_symbols()

    def test_kraken_adapter(self):
        adapter = KrakenAdapter()
        assert adapter.get_exchange_name() == "kraken"
        assert "BTC/USD" in adapter.get_supported_symbols()

    def test_gate_adapter(self):
        adapter = GateAdapter()
        assert adapter.get_exchange_name() == "gate"
        assert "GT/USDT" in adapter.get_supported_symbols()

    def test_bitfinex_adapter(self):
        adapter = BitfinexAdapter()
        assert adapter.get_exchange_name() == "bitfinex"
        assert "LEO/USD" in adapter.get_supported_symbols()

    def test_bitget_adapter(self):
        adapter = BitgetAdapter()
        assert adapter.get_exchange_name() == "bitget"
        assert "BGB/USDT" in adapter.get_supported_symbols()

    def test_coinbase_adapter(self):
        adapter = CoinbaseAdapter()
        assert adapter.get_exchange_name() == "coinbase"
        assert "BTC/USD" in adapter.get_supported_symbols()

    def test_all_adapters_are_base_exchange(self):
        adapters = [
            BinanceAdapter(), BybitAdapter(), OKXAdapter(),
            KuCoinAdapter(), KrakenAdapter(), GateAdapter(),
            BitfinexAdapter(), BitgetAdapter(), CoinbaseAdapter(),
        ]
        for adapter in adapters:
            assert isinstance(adapter, BaseExchangeAdapter)

    def test_all_adapters_have_symbols(self):
        adapters = [
            BinanceAdapter(), BybitAdapter(), OKXAdapter(),
            KuCoinAdapter(), KrakenAdapter(), GateAdapter(),
            BitfinexAdapter(), BitgetAdapter(), CoinbaseAdapter(),
        ]
        for adapter in adapters:
            symbols = adapter.get_supported_symbols()
            assert len(symbols) > 0

    def test_ccxt_adapter_default_symbols(self):
        adapter = _CCXTAdapter("generic_exchange")
        symbols = adapter.get_supported_symbols()
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols


# ======================================================================
# 4. Data Source Adapters
# ======================================================================

class TestDataSourceAdapters:
    """Tests for non-crypto data source adapters."""

    def test_yfinance_adapter_name(self):
        adapter = _YFinanceAdapter()
        assert adapter.get_exchange_name() == "yfinance"
        assert "AAPL" in adapter.get_supported_symbols()
        assert "SPY" in adapter.get_supported_symbols()

    def test_yfinance_orderbook_unavailable(self):
        adapter = _YFinanceAdapter()
        import asyncio
        result = asyncio.run(
            adapter.get_orderbook("AAPL")
        )
        assert "note" in result
        assert "bids" in result
        assert "asks" in result

    def test_akshare_adapter_name(self):
        adapter = _AKShareAdapter()
        assert adapter.get_exchange_name() == "akshare"
        assert "000001" in adapter.get_supported_symbols()
        assert "600519" in adapter.get_supported_symbols()

    def test_futures_adapter_name(self):
        adapter = _FuturesAdapter()
        assert adapter.get_exchange_name() == "futures"
        assert "ES" in adapter.get_supported_symbols()
        assert "CL" in adapter.get_supported_symbols()

    def test_forex_adapter_name(self):
        adapter = _ForexAdapter()
        assert adapter.get_exchange_name() == "forex"
        assert "EURUSD" in adapter.get_supported_symbols()
        assert "GBPUSD" in adapter.get_supported_symbols()


# ======================================================================
# 5. _CCXTAdapter with mocked ccxt
# ======================================================================

class TestCCXTAdapterMocked:
    """Tests for _CCXTAdapter with mocked ccxt exchange."""

    @pytest.mark.asyncio
    async def test_get_kline(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1700000000000, 42000, 42500, 41800, 42200, 1000],
            [1700003600000, 42200, 42800, 42000, 42600, 1200],
        ]

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        klines = await adapter.get_kline("BTC/USDT", "1h", 100)
        assert len(klines) == 2
        assert klines[0]["open"] == 42000
        assert klines[0]["close"] == 42200
        assert klines[1]["volume"] == 1200

    @pytest.mark.asyncio
    async def test_get_kline_sorted(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1700003600000, 42200, 42800, 42000, 42600, 1200],
            [1700000000000, 42000, 42500, 41800, 42200, 1000],
        ]

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        klines = await adapter.get_kline("BTC/USDT", "1h", 100)
        assert klines[0]["time"] < klines[1]["time"]

    @pytest.mark.asyncio
    async def test_get_kline_error_returns_empty(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.side_effect = Exception("API error")

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        klines = await adapter.get_kline("BTC/USDT", "1h", 100)
        assert klines == []

    @pytest.mark.asyncio
    async def test_get_ticker_price(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ticker.return_value = {"last": 42000.50}

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        price = await adapter.get_ticker_price("BTC/USDT")
        assert price == 42000.50

    @pytest.mark.asyncio
    async def test_get_ticker_price_error(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ticker.side_effect = Exception("error")

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        price = await adapter.get_ticker_price("BTC/USDT")
        assert price == 0.0

    @pytest.mark.asyncio
    async def test_get_orderbook(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book.return_value = {
            "bids": [[42000, 1.5], [41900, 2.0]],
            "asks": [[42100, 1.0], [42200, 0.5]],
        }

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        book = await adapter.get_orderbook("BTC/USDT")
        assert len(book["bids"]) == 2
        assert len(book["asks"]) == 2

    @pytest.mark.asyncio
    async def test_get_orderbook_error(self):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book.side_effect = Exception("error")

        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        book = await adapter.get_orderbook("BTC/USDT")
        assert book == {"bids": [], "asks": []}

    @pytest.mark.asyncio
    async def test_close(self):
        mock_exchange = AsyncMock()
        adapter = _CCXTAdapter("binance")
        adapter._exchange = mock_exchange

        await adapter.close()
        mock_exchange.close.assert_called_once()
        assert adapter._exchange is None

    @pytest.mark.asyncio
    async def test_close_no_exchange(self):
        adapter = _CCXTAdapter("binance")
        await adapter.close()  # Should not raise
        assert adapter._exchange is None


# ======================================================================
# 6. QuantDingerFactory Initialization
# ======================================================================

class TestQuantDingerFactoryInit:
    """Tests for QuantDingerFactory initialization."""

    def test_default_initialization(self):
        f = QuantDingerFactory()
        assert f._default_config == {}

    def test_initialization_with_config(self):
        config = {"api_key": "test", "sandbox": True}
        f = QuantDingerFactory(default_config=config)
        assert f._default_config == config


# ======================================================================
# 7. create_exchange_adapter
# ======================================================================

class TestCreateExchangeAdapter:
    """Tests for creating exchange adapters."""

    def test_create_binance(self, factory):
        adapter = factory.create_exchange_adapter("binance")
        assert isinstance(adapter, BinanceAdapter)
        assert isinstance(adapter, BaseExchangeAdapter)

    def test_create_bybit(self, factory):
        adapter = factory.create_exchange_adapter("bybit")
        assert isinstance(adapter, BybitAdapter)

    def test_create_okx(self, factory):
        adapter = factory.create_exchange_adapter("okx")
        assert isinstance(adapter, OKXAdapter)

    def test_create_kucoin(self, factory):
        adapter = factory.create_exchange_adapter("kucoin")
        assert isinstance(adapter, KuCoinAdapter)

    def test_create_kraken(self, factory):
        adapter = factory.create_exchange_adapter("kraken")
        assert isinstance(adapter, KrakenAdapter)

    def test_create_gate(self, factory):
        adapter = factory.create_exchange_adapter("gate")
        assert isinstance(adapter, GateAdapter)

    def test_create_bitfinex(self, factory):
        adapter = factory.create_exchange_adapter("bitfinex")
        assert isinstance(adapter, BitfinexAdapter)

    def test_create_bitget(self, factory):
        adapter = factory.create_exchange_adapter("bitget")
        assert isinstance(adapter, BitgetAdapter)

    def test_create_coinbase(self, factory):
        adapter = factory.create_exchange_adapter("coinbase")
        assert isinstance(adapter, CoinbaseAdapter)

    def test_create_case_insensitive(self, factory):
        adapter = factory.create_exchange_adapter("BINANCE")
        assert isinstance(adapter, BinanceAdapter)

    def test_create_with_whitespace(self, factory):
        adapter = factory.create_exchange_adapter("  binance  ")
        assert isinstance(adapter, BinanceAdapter)

    def test_create_unknown_falls_back_to_ccxt(self, factory):
        adapter = factory.create_exchange_adapter("mexc")
        assert isinstance(adapter, _CCXTAdapter)
        assert adapter.get_exchange_name() == "mexc"

    def test_create_with_config(self, factory):
        adapter = factory.create_exchange_adapter("binance", config={"api_key": "test"})
        assert isinstance(adapter, BinanceAdapter)

    def test_config_merged_with_default(self, factory_with_config):
        adapter = factory_with_config.create_exchange_adapter(
            "binance", config={"extra": "value"},
        )
        assert isinstance(adapter, BinanceAdapter)


# ======================================================================
# 8. create_data_source
# ======================================================================

class TestCreateDataSource:
    """Tests for creating data source adapters."""

    def test_create_crypto(self, factory):
        adapter = factory.create_data_source("crypto")
        assert isinstance(adapter, _CCXTAdapter)
        assert isinstance(adapter, BaseExchangeAdapter)

    def test_create_us_stock(self, factory):
        adapter = factory.create_data_source("us_stock")
        assert isinstance(adapter, _YFinanceAdapter)

    def test_create_cn_stock(self, factory):
        adapter = factory.create_data_source("cn_stock")
        assert isinstance(adapter, _AKShareAdapter)

    def test_create_futures(self, factory):
        adapter = factory.create_data_source("futures")
        assert isinstance(adapter, _FuturesAdapter)

    def test_create_forex(self, factory):
        adapter = factory.create_data_source("forex")
        assert isinstance(adapter, _ForexAdapter)

    def test_create_case_insensitive(self, factory):
        adapter = factory.create_data_source("CRYPTO")
        assert isinstance(adapter, _CCXTAdapter)

    def test_create_with_whitespace(self, factory):
        adapter = factory.create_data_source("  us_stock  ")
        assert isinstance(adapter, _YFinanceAdapter)

    def test_alias_binance_to_crypto(self, factory):
        adapter = factory.create_data_source("binance")
        assert isinstance(adapter, _CCXTAdapter)

    def test_alias_usstock(self, factory):
        adapter = factory.create_data_source("usstock")
        assert isinstance(adapter, _YFinanceAdapter)

    def test_alias_us(self, factory):
        adapter = factory.create_data_source("us")
        assert isinstance(adapter, _YFinanceAdapter)

    def test_alias_ashare(self, factory):
        adapter = factory.create_data_source("ashare")
        assert isinstance(adapter, _AKShareAdapter)

    def test_alias_cn(self, factory):
        adapter = factory.create_data_source("cn")
        assert isinstance(adapter, _AKShareAdapter)

    def test_unknown_defaults_to_crypto(self, factory):
        adapter = factory.create_data_source("unknown_market")
        assert isinstance(adapter, _CCXTAdapter)


# ======================================================================
# 9. Adapter Caching
# ======================================================================

class TestAdapterCaching:
    """Tests for adapter instance caching."""

    def test_exchange_adapter_cached(self, factory):
        adapter1 = factory.create_exchange_adapter("binance")
        adapter2 = factory.create_exchange_adapter("binance")
        assert adapter1 is adapter2

    def test_data_source_cached(self, factory):
        adapter1 = factory.create_data_source("crypto")
        adapter2 = factory.create_data_source("crypto")
        assert adapter1 is adapter2

    def test_different_exchanges_not_cached_together(self, factory):
        binance = factory.create_exchange_adapter("binance")
        bybit = factory.create_exchange_adapter("bybit")
        assert binance is not bybit

    def test_different_data_sources_not_cached_together(self, factory):
        crypto = factory.create_data_source("crypto")
        stocks = factory.create_data_source("us_stock")
        assert crypto is not stocks


# ======================================================================
# 10. get_kline Convenience Method
# ======================================================================

class TestGetKlineConvenience:
    """Tests for the get_kline convenience method."""

    @pytest.mark.asyncio
    async def test_get_kline_by_exchange(self, factory):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1700000000000, 42000, 42500, 41800, 42200, 1000],
        ]

        adapter = factory.create_exchange_adapter("binance")
        adapter._exchange = mock_exchange

        klines = await factory.get_kline("binance", "BTC/USDT", "1h", 100)
        assert len(klines) == 1
        assert klines[0]["close"] == 42200

    @pytest.mark.asyncio
    async def test_get_kline_by_market_type(self, factory):
        # Mock the data source adapter
        mock_adapter = AsyncMock(spec=BaseExchangeAdapter)
        mock_adapter.get_kline.return_value = [
            {"time": 1700000000, "open": 150, "high": 155, "low": 148, "close": 153, "volume": 1000},
        ]

        with patch.object(factory, "create_data_source", return_value=mock_adapter):
            klines = await factory.get_kline("us_stock", "AAPL", "1d", 100)
            assert len(klines) == 1

    @pytest.mark.asyncio
    async def test_get_kline_error_returns_empty(self, factory):
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv.side_effect = Exception("API error")

        adapter = factory.create_exchange_adapter("binance")
        adapter._exchange = mock_exchange

        klines = await factory.get_kline("binance", "BTC/USDT", "1h", 100)
        assert klines == []


# ======================================================================
# 11. Static Methods
# ======================================================================

class TestStaticMethods:
    """Tests for static/utility methods."""

    def test_get_supported_exchanges(self):
        exchanges = QuantDingerFactory.get_supported_exchanges()
        assert isinstance(exchanges, list)
        assert len(exchanges) == 9
        assert "binance" in exchanges
        assert "bybit" in exchanges
        assert "okx" in exchanges
        assert "kucoin" in exchanges
        assert "kraken" in exchanges
        assert "gate" in exchanges
        assert "bitfinex" in exchanges
        assert "bitget" in exchanges
        assert "coinbase" in exchanges

    def test_get_supported_market_types(self):
        market_types = QuantDingerFactory.get_supported_market_types()
        assert isinstance(market_types, list)
        assert "crypto" in market_types
        assert "us_stock" in market_types
        assert "cn_stock" in market_types
        assert "futures" in market_types
        assert "forex" in market_types


# ======================================================================
# 12. close_all
# ======================================================================

class TestCloseAll:
    """Tests for closing all cached adapters."""

    @pytest.mark.asyncio
    async def test_close_all(self, factory):
        adapter = factory.create_exchange_adapter("binance")
        adapter._exchange = AsyncMock()

        await factory.close_all()
        assert len(_adapter_cache) == 0

    @pytest.mark.asyncio
    async def test_close_all_empty(self, factory):
        await factory.close_all()  # Should not raise
        assert len(_adapter_cache) == 0

    @pytest.mark.asyncio
    async def test_close_all_handles_error(self, factory):
        mock_adapter = MagicMock()
        mock_adapter.close = AsyncMock(side_effect=Exception("close error"))
        _adapter_cache["test"] = mock_adapter

        await factory.close_all()  # Should not raise
        assert len(_adapter_cache) == 0


# ======================================================================
# 13. Registry Completeness
# ======================================================================

class TestRegistryCompleteness:
    """Tests for adapter registry completeness."""

    def test_exchange_registry_has_9_entries(self):
        assert len(_EXCHANGE_ADAPTERS) == 9

    def test_all_exchange_adapters_are_base_exchange(self):
        for name, cls in _EXCHANGE_ADAPTERS.items():
            assert issubclass(cls, BaseExchangeAdapter), f"{name} is not a BaseExchangeAdapter"

    def test_data_source_registry_has_5_entries(self):
        assert len(_DATA_SOURCE_ADAPTERS) == 5

    def test_all_data_source_adapters_are_base_exchange(self):
        for market_type, cls in _DATA_SOURCE_ADAPTERS.items():
            assert issubclass(cls, BaseExchangeAdapter), f"{market_type} is not a BaseExchangeAdapter"

    def test_exchange_names_match_keys(self):
        for name, cls in _EXCHANGE_ADAPTERS.items():
            adapter = cls()
            assert adapter.get_exchange_name() == name


# ======================================================================
# 14. YFinance / AKShare Adapter Mocked
# ======================================================================

class TestYFinanceAdapterMocked:
    """Tests for _YFinanceAdapter with mocked yfinance."""

    @pytest.mark.asyncio
    async def test_get_kline_no_yfinance(self):
        adapter = _YFinanceAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            klines = await adapter.get_kline("AAPL", "1d", 100)
            assert klines == []

    @pytest.mark.asyncio
    async def test_get_ticker_price_no_yfinance(self):
        adapter = _YFinanceAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            price = await adapter.get_ticker_price("AAPL")
            assert price == 0.0


class TestAKShareAdapterMocked:
    """Tests for _AKShareAdapter with mocked akshare."""

    @pytest.mark.asyncio
    async def test_get_kline_no_akshare(self):
        adapter = _AKShareAdapter()
        with patch.dict("sys.modules", {"akshare": None}):
            klines = await adapter.get_kline("000001", "1d", 100)
            assert klines == []

    @pytest.mark.asyncio
    async def test_get_ticker_price_no_akshare(self):
        adapter = _AKShareAdapter()
        with patch.dict("sys.modules", {"akshare": None}):
            price = await adapter.get_ticker_price("000001")
            assert price == 0.0


class TestFuturesAdapterMocked:
    """Tests for _FuturesAdapter with mocked yfinance."""

    @pytest.mark.asyncio
    async def test_get_kline_no_yfinance(self):
        adapter = _FuturesAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            klines = await adapter.get_kline("ES", "1d", 100)
            assert klines == []

    @pytest.mark.asyncio
    async def test_get_ticker_price_no_yfinance(self):
        adapter = _FuturesAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            price = await adapter.get_ticker_price("ES")
            assert price == 0.0

    @pytest.mark.asyncio
    async def test_orderbook_returns_empty(self):
        adapter = _FuturesAdapter()
        book = await adapter.get_orderbook("ES")
        assert book == {"bids": [], "asks": []}


class TestForexAdapterMocked:
    """Tests for _ForexAdapter with mocked yfinance."""

    @pytest.mark.asyncio
    async def test_get_kline_no_yfinance(self):
        adapter = _ForexAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            klines = await adapter.get_kline("EURUSD", "1d", 100)
            assert klines == []

    @pytest.mark.asyncio
    async def test_get_ticker_price_no_yfinance(self):
        adapter = _ForexAdapter()
        with patch.dict("sys.modules", {"yfinance": None}):
            price = await adapter.get_ticker_price("EURUSD")
            assert price == 0.0

    @pytest.mark.asyncio
    async def test_orderbook_returns_empty(self):
        adapter = _ForexAdapter()
        book = await adapter.get_orderbook("EURUSD")
        assert book == {"bids": [], "asks": []}
