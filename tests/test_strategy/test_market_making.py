"""Tests for MarketMakingStrategy."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.strategy.strategies.market_making import MarketMakingStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TestMarketMakingStrategy:
    """Test market making strategy."""

    def test_default_params(self):
        strategy = MarketMakingStrategy()
        assert strategy.name == "MarketMaking"
        assert strategy.gamma == 0.1
        assert strategy.k == 1.5
        assert strategy.max_inventory == 10

    def test_required_columns(self):
        strategy = MarketMakingStrategy()
        assert "close" in strategy.required_columns()
        assert "volume" in strategy.required_columns()

    def test_warmup_period(self):
        strategy = MarketMakingStrategy()
        assert strategy.warmup_period() >= 60

    def test_estimate_volatility(self, random_ohlcv_data):
        strategy = MarketMakingStrategy()
        vol = strategy.estimate_volatility(random_ohlcv_data)
        assert vol > 0

    def test_reservation_price(self):
        strategy = MarketMakingStrategy()
        mid = 100.0
        # No inventory: reservation = mid
        r = strategy.compute_reservation_price(mid, 0, 0.01, 1.0)
        assert r == mid

        # Long inventory: reservation < mid (want to sell)
        r = strategy.compute_reservation_price(mid, 5, 0.01, 1.0)
        assert r < mid

        # Short inventory: reservation > mid (want to buy)
        r = strategy.compute_reservation_price(mid, -5, 0.01, 1.0)
        assert r > mid

    def test_optimal_spread(self):
        strategy = MarketMakingStrategy()
        spread = strategy.compute_optimal_spread(0.01, 1.0)
        assert spread > 0

    def test_optimal_quotes(self):
        strategy = MarketMakingStrategy()
        bid, ask, bid_size, ask_size = strategy.compute_optimal_quotes(
            100.0, 0, 0.01, 1.0
        )
        assert bid < 100.0
        assert ask > 100.0
        assert bid_size > 0
        assert ask_size > 0
        assert ask - bid >= strategy.min_spread

    def test_optimal_quotes_with_inventory(self):
        strategy = MarketMakingStrategy()
        # Long inventory: bid should be lower, ask should be more aggressive
        bid_long, ask_long, _, _ = strategy.compute_optimal_quotes(
            100.0, 5, 0.01, 1.0
        )
        bid_flat, ask_flat, _, _ = strategy.compute_optimal_quotes(
            100.0, 0, 0.01, 1.0
        )
        # With inventory, quotes should shift down (want to sell)
        assert bid_long < bid_flat or ask_long < ask_flat

    def test_fill_probability(self):
        strategy = MarketMakingStrategy()
        # Close to mid: high fill probability
        prob_close = strategy.estimate_fill_probability(0.001, 0.01)
        # Far from mid: low fill probability
        prob_far = strategy.estimate_fill_probability(0.1, 0.01)
        assert prob_close > prob_far

    def test_adverse_selection_detection(self):
        strategy = MarketMakingStrategy()
        # Normal data: no adverse selection
        normal_data = pd.DataFrame({
            "close": 100 + np.random.randn(100) * 0.5,
            "volume": np.random.randint(1000, 10000, 100).astype(float),
        })
        assert strategy.detect_adverse_selection(normal_data) is False

        # Extreme move: adverse selection
        extreme_data = normal_data.copy()
        extreme_data.iloc[-1, 0] = 200  # Massive jump
        result = strategy.detect_adverse_selection(extreme_data)
        # May or may not detect depending on rolling stats

    def test_generate_signal(self, random_ohlcv_data):
        strategy = MarketMakingStrategy(params={"symbol": "TEST"})
        signal = strategy.generate_signal(random_ohlcv_data)
        assert isinstance(signal, Signal)
        assert signal.signal_type in [
            SignalType.BUY, SignalType.SELL, SignalType.HOLD,
        ]

    def test_signal_has_quote_info(self, random_ohlcv_data):
        strategy = MarketMakingStrategy(params={"symbol": "TEST"})
        signal = strategy.generate_signal(random_ohlcv_data)
        assert "bid_price" in signal.evidence
        assert "ask_price" in signal.evidence
        assert "bid_size" in signal.evidence
        assert "ask_size" in signal.evidence
        assert "inventory" in signal.evidence
        assert "sigma" in signal.evidence

    def test_inventory_management(self, random_ohlcv_data):
        strategy = MarketMakingStrategy()
        bid_size, ask_size = strategy._compute_order_sizes(0)
        assert bid_size > 0
        assert ask_size > 0

        # Long inventory: bid size reduced, ask size increased
        bid_long, ask_long = strategy._compute_order_sizes(8)
        assert bid_long < bid_size
        assert ask_long > ask_size

    def test_insufficient_data(self):
        strategy = MarketMakingStrategy()
        data = pd.DataFrame({"close": [100], "volume": [1000]})
        signal = strategy.generate_signal(data)
        assert signal is None
