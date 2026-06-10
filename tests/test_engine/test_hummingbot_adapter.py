"""Tests for Hummingbot adapter."""

from __future__ import annotations

import pytest

from quant_nanggroe.engine.backtest.adapters.hummingbot_adapter import (
    HummingbotAdapter,
    HummingbotConfig,
    HummingbotStrategy,
    AvellanedaStoikovConfig,
    MarketMakingState,
)


class TestHummingbotConfig:
    """Tests for HummingbotConfig validation."""

    def test_default_config(self):
        config = HummingbotConfig()
        assert config.strategy == HummingbotStrategy.PURE_MARKET_MAKING
        assert config.exchange == "binance"
        assert config.trading_pair == "BTC-USDT"
        assert config.bid_spread == 0.001

    def test_custom_config(self):
        config = HummingbotConfig(
            exchange="okx",
            trading_pair="ETH-USDT",
            bid_spread=0.002,
            ask_spread=0.002,
            order_amount=1.0,
        )
        assert config.exchange == "okx"
        assert config.trading_pair == "ETH-USDT"

    def test_spread_range_validation(self):
        with pytest.raises(Exception):
            HummingbotConfig(bid_spread=0.5)  # > 0.1

    def test_order_levels_range(self):
        with pytest.raises(Exception):
            HummingbotConfig(order_levels=0)

    def test_order_amount_positive(self):
        with pytest.raises(Exception):
            HummingbotConfig(order_amount=-1)


class TestAvellanedaStoikovConfig:
    """Tests for A-S specific config."""

    def test_default_as_config(self):
        config = AvellanedaStoikovConfig()
        assert config.strategy == HummingbotStrategy.AVELLANEDA_STOIKOV
        assert config.gamma == 0.1
        assert config.sigma == 0.01
        assert config.kappa == 0.5

    def test_custom_as_config(self):
        config = AvellanedaStoikovConfig(
            gamma=0.5,
            sigma=0.02,
            kappa=1.0,
            trading_hours=8.0,
        )
        assert config.gamma == 0.5
        assert config.trading_hours == 8.0


class TestHummingbotAdapter:
    """Tests for HummingbotAdapter main functionality."""

    def test_start(self):
        adapter = HummingbotAdapter()
        result = adapter.start()
        assert result["status"] == "started"
        assert "config_yaml" in result
        assert "docker_command" in result

    def test_stop(self):
        adapter = HummingbotAdapter()
        adapter.start()
        result = adapter.stop()
        assert result["status"] == "stopped"

    def test_get_status(self):
        adapter = HummingbotAdapter()
        adapter.start()
        status = adapter.get_status()
        assert isinstance(status, MarketMakingState)
        assert status.is_running is True

    def test_update_parameters(self):
        adapter = HummingbotAdapter()
        result = adapter.update_parameters(bid_spread=0.002, ask_spread=0.003)
        assert result["status"] == "parameters_updated"
        assert result["updated"]["bid_spread"] == 0.002

    def test_calculate_optimal_spreads(self):
        adapter = HummingbotAdapter(config=AvellanedaStoikovConfig())
        spreads = adapter.calculate_optimal_spreads(
            volatility=0.02,
            inventory_ratio=0.5,
            order_flow_intensity=0.5,
        )
        assert "optimal_bid_spread" in spreads
        assert "optimal_ask_spread" in spreads
        assert spreads["model"] == "avellaneda_stoikov"

    def test_calculate_spreads_with_inventory_skew(self):
        adapter = HummingbotAdapter(config=AvellanedaStoikovConfig())
        # High inventory should widen bid spread, narrow ask spread
        spreads_high = adapter.calculate_optimal_spreads(
            volatility=0.02,
            inventory_ratio=0.8,  # Heavy base inventory
        )
        spreads_low = adapter.calculate_optimal_spreads(
            volatility=0.02,
            inventory_ratio=0.2,  # Light base inventory
        )
        # High inventory → wider bid, narrower ask
        assert spreads_high["optimal_bid_spread"] >= spreads_low["optimal_bid_spread"]
        assert spreads_high["optimal_ask_spread"] <= spreads_low["optimal_ask_spread"]

    def test_generate_config_yaml(self):
        adapter = HummingbotAdapter()
        yaml = adapter.generate_config_yaml()
        assert "binance" in yaml
        assert "BTC-USDT" in yaml
        assert "pure_market_making" in yaml

    def test_calculate_performance_metrics(self):
        adapter = HummingbotAdapter()
        # Not started yet
        metrics = adapter.calculate_performance_metrics()
        assert "error" in metrics

        adapter.start()
        metrics = adapter.calculate_performance_metrics()
        assert "uptime_seconds" in metrics
        assert "total_trades" in metrics

    def test_from_agent_decision(self):
        decision = {
            "symbol": "ETH/USDT",
            "quantity": 0.5,
            "bid_spread": 0.0015,
            "ask_spread": 0.0015,
        }
        adapter = HummingbotAdapter.from_agent_decision(decision, exchange="bybit")
        assert adapter.config.trading_pair == "ETH-USDT"
        assert adapter.config.exchange == "bybit"


class TestHummingbotStrategy:
    """Tests for strategy enum."""

    def test_all_values(self):
        assert HummingbotStrategy.PURE_MARKET_MAKING.value == "pure_market_making"
        assert HummingbotStrategy.AVELLANEDA_STOIKOV.value == "avellaneda_stoikov"
        assert HummingbotStrategy.GRID.value == "grid"

    def test_all_members(self):
        assert len(HummingbotStrategy) == 8


class TestMarketMakingState:
    """Tests for MarketMakingState dataclass."""

    def test_default_state(self):
        state = MarketMakingState()
        assert state.is_running is False
        assert state.total_trades == 0
        assert state.pnl == 0.0

    def test_custom_state(self):
        state = MarketMakingState(
            is_running=True,
            trading_pair="ETH-USDT",
            exchange="okx",
            total_trades=10,
            pnl=150.50,
        )
        assert state.is_running is True
        assert state.pnl == 150.50
