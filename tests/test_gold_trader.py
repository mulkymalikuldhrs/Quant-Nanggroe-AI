"""Tests for the AI-XAUUSD-Trading inspired gold trader agent."""
from __future__ import annotations

from quant_nanggroe.agents.gold_trader import GoldSignal, GoldTrader


class TestGoldSignal:
    def test_default_reasons(self):
        from datetime import datetime
        gs = GoldSignal(timestamp=datetime.now(), direction="long", confidence=0.8)
        assert gs.reasons == []

    def test_with_reasons(self):
        from datetime import datetime
        gs = GoldSignal(
            timestamp=datetime.now(),
            direction="short",
            confidence=0.6,
            reasons=["SMA cross", "RSI overbought"],
        )
        assert len(gs.reasons) == 2
        assert "SMA cross" in gs.reasons


class TestGoldTrader:
    def test_initial_state(self):
        gt = GoldTrader()
        assert gt.prices == []
        assert gt.signals == []
        assert gt.lookback_days == 30

    def test_custom_lookback(self):
        gt = GoldTrader(lookback_days=60)
        assert gt.lookback_days == 60

    def test_update_prices_appends(self):
        gt = GoldTrader()
        gt.update_prices([100.0, 101.0, 102.0])
        assert gt.prices == [100.0, 101.0, 102.0]

    def test_update_prices_respects_lookback(self):
        gt = GoldTrader(lookback_days=5)
        gt.update_prices(list(range(20)))
        assert len(gt.prices) == 5
        assert gt.prices == list(range(15, 20))

    def test_analyze_insufficient_data(self):
        gt = GoldTrader()
        gt.update_prices([100.0, 101.0])
        signal = gt.analyze()
        assert signal.direction == "neutral"
        assert signal.confidence == 0.0
        assert "insufficient data" in signal.reasons

    def test_analyze_edge_20_prices(self):
        gt = GoldTrader()
        gt.update_prices([100.0 + i for i in range(20)])
        signal = gt.analyze()
        assert signal.direction != "neutral" or signal.confidence == 0.0
        # Should not give insufficient data
        assert "insufficient data" not in signal.reasons

    def test_analyze_bullish_signal(self):
        """Uptrend should produce long signal (small pullbacks keep RSI < 70)."""
        gt = GoldTrader()
        prices = [100.0]
        for i in range(1, 30):
            prices.append(prices[-1] - 1.2 if i % 3 == 0 else prices[-1] + 1.0)
        gt.update_prices(prices)
        assert gt._calc_rsi() < 70
        signal = gt.analyze()
        assert signal.direction == "long"
        assert signal.confidence > 0.5
        assert any("SMA5" in r for r in signal.reasons)

    def test_analyze_bearish_signal(self):
        """Downtrend should produce short signal (small bounces keep RSI > 30)."""
        gt = GoldTrader()
        prices = [100.0]
        for i in range(1, 30):
            prices.append(prices[-1] + 1.2 if i % 3 == 0 else prices[-1] - 1.0)
        gt.update_prices(prices)
        assert gt._calc_rsi() > 30
        signal = gt.analyze()
        assert signal.direction == "short"
        assert signal.confidence > 0.5

    def test_analyze_neutral_ranging(self):
        """Ranging market should produce RSI in neutral range."""
        gt = GoldTrader()
        prices = [100.0 + (i % 6 - 3) * 2.0 for i in range(30)]
        gt.update_prices(prices)
        signal = gt.analyze()
        rsi = gt._calc_rsi()
        if signal.direction != "neutral":
            assert 30 <= rsi <= 70

    def test_analyze_overbought_no_long(self):
        """RSI > 70 should prevent long signal even if SMA5 > SMA20."""
        gt = GoldTrader()
        # Strong uptrend that pushes RSI above 70
        prices = [100.0 + i * 3.0 for i in range(30)]
        gt.update_prices(prices)
        signal = gt.analyze()
        # RSI should be above 70, so no long signal despite uptrend
        if gt._calc_rsi() >= 70:
            assert signal.direction != "long"

    def test_analyze_oversold_no_short(self):
        """RSI < 30 should prevent short signal even if SMA5 < SMA20."""
        gt = GoldTrader()
        prices = [100.0 - i * 3.0 for i in range(30)]
        gt.update_prices(prices)
        signal = gt.analyze()
        if gt._calc_rsi() <= 30:
            assert signal.direction != "short"

    def test_signals_accumulate(self):
        gt = GoldTrader()
        prices = [100.0 + i * 0.5 for i in range(30)]
        gt.update_prices(prices)
        gt.analyze()
        gt.analyze()
        assert len(gt.signals) == 2

    def test_rsi_calculation(self):
        gt = GoldTrader()
        prices = [100.0 + i * 0.5 for i in range(30)]
        gt.update_prices(prices)
        rsi = gt._calc_rsi()
        assert 0 <= rsi <= 100

    def test_rsi_insufficient_data(self):
        gt = GoldTrader()
        gt.update_prices([100.0] * 5)
        rsi = gt._calc_rsi(period=14)
        assert rsi == 50.0  # default when insufficient data

    def test_rsi_all_gains(self):
        """When all moves are gains, RSI should be 100."""
        gt = GoldTrader()
        prices = [100.0 + i for i in range(20)]
        gt.update_prices(prices)
        rsi = gt._calc_rsi(period=14)
        assert rsi == 100.0

    def test_confidence_never_exceeds_08(self):
        gt = GoldTrader()
        prices = [100.0 + i * 10.0 for i in range(30)]
        gt.update_prices(prices)
        signal = gt.analyze()
        assert signal.confidence <= 0.8

    def test_confidence_never_below_05(self):
        gt = GoldTrader()
        prices = [100.0]
        for i in range(1, 30):
            prices.append(prices[-1] - 1.2 if i % 3 == 0 else prices[-1] + 1.0)
        gt.update_prices(prices)
        signal = gt.analyze()
        assert signal.confidence >= 0.5
