"""Tests for QuantConnect adapter."""

from __future__ import annotations

import pytest

from quant_nanggroe.engine.backtest.adapters.quantconnect import (
    QuantConnectAdapter,
    QuantConnectConfig,
    LeanDataConverter,
    QuantConnectResolution,
    QuantConnectMarket,
)
from quant_nanggroe.agents.state import AssetClass, TradeAction


class TestLeanDataConverter:
    """Tests for LeanDataConverter bidirectional conversion."""

    def test_symbol_to_lean_equity(self):
        result = LeanDataConverter.symbol_to_lean("AAPL", "equity")
        assert result["symbol"] == "AAPL"
        assert result["security_type"] == "Equity"
        assert result["market"] == "usa"

    def test_symbol_to_lean_forex(self):
        result = LeanDataConverter.symbol_to_lean("EUR/USD", "forex")
        assert result["symbol"] == "EURUSD"
        assert result["security_type"] == "Forex"
        assert result["market"] == "oanda"

    def test_symbol_to_lean_crypto(self):
        result = LeanDataConverter.symbol_to_lean("BTC/USDT", "crypto")
        assert result["symbol"] == "BTCUSD"
        assert result["security_type"] == "Crypto"
        assert result["market"] == "binance"

    def test_lean_to_symbol_forex(self):
        result = LeanDataConverter.lean_to_symbol("EURUSD", "Forex")
        assert result == "EUR/USD"

    def test_lean_to_symbol_crypto(self):
        result = LeanDataConverter.lean_to_symbol("BTCUSD", "Crypto")
        assert result == "BTC/USDT"

    def test_lean_to_symbol_equity(self):
        result = LeanDataConverter.lean_to_symbol("AAPL", "Equity")
        assert result == "AAPL"

    def test_signal_to_lean_order_buy(self):
        signal = {
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 100,
            "asset_class": "equity",
            "source": "trader",
        }
        result = LeanDataConverter.signal_to_lean_order(signal)
        assert result["direction"] == 0  # Buy
        assert result["quantity"] == 100
        assert result["order_type"] == "MarketOrder"

    def test_signal_to_lean_order_with_stop(self):
        signal = {
            "symbol": "BTC/USDT",
            "action": "BUY",
            "quantity": 0.5,
            "stop_loss": 49000,
            "asset_class": "crypto",
        }
        result = LeanDataConverter.signal_to_lean_order(signal)
        assert result["order_type"] == "StopMarketOrder"

    def test_signal_to_lean_order_emergency_exit(self):
        signal = {"symbol": "AAPL", "action": "EMERGENCY_EXIT", "quantity": 50}
        result = LeanDataConverter.signal_to_lean_order(signal)
        assert result["order_type"] == "MarketOrder"
        assert result["direction"] == 3


class TestQuantConnectConfig:
    """Tests for QuantConnectConfig validation."""

    def test_default_config(self):
        config = QuantConnectConfig()
        assert config.resolution == QuantConnectResolution.DAILY
        assert config.starting_capital == 100_000.0
        assert config.benchmark == "SPY"

    def test_custom_config(self):
        config = QuantConnectConfig(
            user_id="12345",
            api_token="abc123",
            starting_capital=50_000,
            resolution=QuantConnectResolution.MINUTE,
        )
        assert config.user_id == "12345"
        assert config.starting_capital == 50_000
        assert config.resolution == QuantConnectResolution.MINUTE

    def test_starting_capital_must_be_positive(self):
        with pytest.raises(Exception):
            QuantConnectConfig(starting_capital=-100)

    def test_max_concurrent_backtests_range(self):
        with pytest.raises(Exception):
            QuantConnectConfig(max_concurrent_backtests=0)


class TestQuantConnectAdapter:
    """Tests for QuantConnectAdapter main functionality."""

    def test_create_project(self):
        adapter = QuantConnectAdapter()
        project = adapter.create_project("TestProject")
        assert project["name"] == "TestProject"
        assert project["status"] == "created"

    def test_generate_algorithm_code_equity(self):
        adapter = QuantConnectAdapter()
        code = adapter.generate_algorithm_code(
            symbols=["AAPL", "MSFT"],
            asset_class="equity",
        )
        assert "AddEquity" in code
        assert "AAPL" in code
        assert "MSFT" in code
        assert "QuantNanggroeAlgorithm" in code

    def test_generate_algorithm_code_crypto(self):
        adapter = QuantConnectAdapter()
        code = adapter.generate_algorithm_code(
            symbols=["BTC/USDT", "ETH/USDT"],
            asset_class="crypto",
        )
        assert "AddCrypto" in code
        assert "BTCUSD" in code

    def test_generate_algorithm_code_forex(self):
        adapter = QuantConnectAdapter()
        code = adapter.generate_algorithm_code(
            symbols=["EUR/USD"],
            asset_class="forex",
        )
        assert "AddForex" in code
        assert "EURUSD" in code

    def test_run_backtest(self):
        adapter = QuantConnectAdapter()
        result = adapter.run_backtest(
            symbols=["AAPL"],
            start_date="2023-01-01",
            end_date="2024-01-01",
        )
        assert "backtest_id" in result
        assert result["symbols_count"] == 1
        assert result["status"] == "ready_for_submission"

    def test_list_active_backtests(self):
        adapter = QuantConnectAdapter()
        adapter.run_backtest(symbols=["AAPL"])
        backtests = adapter.list_active_backtests()
        assert len(backtests) == 1

    def test_cancel_backtest(self):
        adapter = QuantConnectAdapter()
        result = adapter.run_backtest(symbols=["AAPL"])
        bid = result["backtest_id"]
        assert adapter.cancel_backtest(bid) is True
        assert adapter.cancel_backtest("nonexistent") is False

    def test_get_results_unknown_raises(self):
        adapter = QuantConnectAdapter()
        with pytest.raises(KeyError):
            adapter.get_results("nonexistent")


class TestQuantConnectResolution:
    """Tests for resolution enum."""

    def test_all_values(self):
        assert QuantConnectResolution.TICK.value == "Tick"
        assert QuantConnectResolution.MINUTE.value == "Minute"
        assert QuantConnectResolution.DAILY.value == "Daily"

    def test_all_members(self):
        assert len(QuantConnectResolution) == 5


class TestQuantConnectMarket:
    """Tests for market enum."""

    def test_all_values(self):
        assert QuantConnectMarket.USA.value == "usa"
        assert QuantConnectMarket.BINANCE.value == "binance"

    def test_all_members(self):
        assert len(QuantConnectMarket) == 10
