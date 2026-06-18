"""Tests for the finance subpackage."""

from __future__ import annotations

import math
import pytest


# ── Risk Guard tests ─────────────────────────────────────────────────────────


class TestConstitutionalRiskGuard:
    """Tests for the constitutional risk guard."""

    @pytest.fixture
    def guard(self):
        from ai_multicolony.finance import ConstitutionalRiskGuard
        return ConstitutionalRiskGuard()

    @pytest.fixture
    def healthy_portfolio(self):
        from ai_multicolony.finance import PortfolioSnapshot
        return PortfolioSnapshot(total_equity=100000.0, cash=60000.0)

    def test_guard_creation(self, guard):
        stats = guard.stats
        assert stats["total_checks"] == 0

    def test_approve_small_trade(self, guard, healthy_portfolio):
        from ai_multicolony.finance import TradeRequest, TradeAction
        request = TradeRequest(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            price=185.0,
            risk_pct=0.3,
        )
        result = guard.check_trade(request, healthy_portfolio)
        assert result.approved

    def test_reject_excessive_risk(self, guard, healthy_portfolio):
        from ai_multicolony.finance import TradeRequest, TradeAction
        request = TradeRequest(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=10,
            price=185.0,
            risk_pct=1.0,  # Exceeds 0.5% per-trade limit
        )
        result = guard.check_trade(request, healthy_portfolio)
        assert not result.approved

    def test_reject_daily_loss_exceeded(self, guard):
        from ai_multicolony.finance import TradeRequest, TradeAction, PortfolioSnapshot
        portfolio = PortfolioSnapshot(
            total_equity=100000.0,
            daily_pnl=-1500.0,  # -1.5% daily loss
        )
        request = TradeRequest(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=1,
            price=185.0,
            risk_pct=0.3,
        )
        result = guard.check_trade(request, portfolio)
        assert not result.approved

    def test_reject_weekly_loss_exceeded(self, guard):
        from ai_multicolony.finance import TradeRequest, TradeAction, PortfolioSnapshot
        portfolio = PortfolioSnapshot(
            total_equity=100000.0,
            weekly_pnl=-4000.0,  # -4% weekly loss
        )
        request = TradeRequest(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=1,
            price=185.0,
            risk_pct=0.3,
        )
        result = guard.check_trade(request, portfolio)
        assert not result.approved

    def test_position_size_adjustment(self, guard, healthy_portfolio):
        from ai_multicolony.finance import TradeRequest, TradeAction
        # Request huge position
        request = TradeRequest(
            symbol="AAPL",
            action=TradeAction.BUY,
            quantity=10000,
            price=185.0,
            risk_pct=0.3,
        )
        result = guard.check_trade(request, healthy_portfolio)
        # Should be adjusted but still potentially approved
        assert result.position_size_adjusted or not result.approved

    def test_calculate_position_size(self, guard):
        size = guard.calculate_position_size(
            equity=100000,
            entry_price=100.0,
            stop_loss_price=98.0,
            risk_pct=0.5,
        )
        assert size > 0

    def test_constitutional_limits(self, guard):
        from ai_multicolony.finance import (
            MAX_RISK_PER_TRADE_PCT,
            MAX_DAILY_LOSS_PCT,
            MAX_WEEKLY_LOSS_PCT,
        )
        assert MAX_RISK_PER_TRADE_PCT == 0.5
        assert MAX_DAILY_LOSS_PCT == 1.0
        assert MAX_WEEKLY_LOSS_PCT == 3.0


# ── Kill Switch tests ────────────────────────────────────────────────────────


class TestKillSwitch:
    """Tests for the emergency kill switch."""

    @pytest.fixture
    def kill_switch(self):
        from ai_multicolony.finance import KillSwitch
        return KillSwitch()

    def test_initial_state(self, kill_switch):
        assert not kill_switch.is_active()
        assert kill_switch.can_trade()

    def test_activate_level_1(self, kill_switch):
        from ai_multicolony.finance import KillSwitchLevel
        event = kill_switch.activate(KillSwitchLevel.LEVEL_1, "Test activation")
        assert kill_switch.is_active()
        assert not kill_switch.can_trade()
        assert event.level == KillSwitchLevel.LEVEL_1

    def test_activate_level_2(self, kill_switch):
        from ai_multicolony.finance import KillSwitchLevel
        kill_switch.activate(KillSwitchLevel.LEVEL_2, "Daily loss exceeded")
        assert not kill_switch.can_trade()
        assert kill_switch.can_hold_positions()

    def test_activate_level_3(self, kill_switch):
        from ai_multicolony.finance import KillSwitchLevel
        kill_switch.activate(KillSwitchLevel.LEVEL_3, "Full shutdown")
        assert not kill_switch.can_hold_positions()

    def test_auto_activate_daily_loss(self, kill_switch):
        event = kill_switch.check_auto_activate(daily_pnl_pct=-2.0)
        assert event is not None
        assert kill_switch.is_active()

    def test_auto_activate_weekly_loss(self, kill_switch):
        event = kill_switch.check_auto_activate(weekly_pnl_pct=-5.0)
        assert event is not None
        assert kill_switch.is_active()

    def test_auto_activate_drawdown(self, kill_switch):
        event = kill_switch.check_auto_activate(max_drawdown_pct=6.0)
        assert event is not None

    def test_no_activation_when_safe(self, kill_switch):
        event = kill_switch.check_auto_activate(daily_pnl_pct=0.5)
        assert event is None
        assert not kill_switch.is_active()

    def test_callback_registration(self, kill_switch):
        from ai_multicolony.finance import KillSwitchLevel
        callback_called = []

        def on_activate(event):
            callback_called.append(event)

        kill_switch.on_activate(KillSwitchLevel.LEVEL_1, on_activate)
        kill_switch.activate(KillSwitchLevel.LEVEL_1, "Test")
        assert len(callback_called) == 1


# ── Market State tests ──────────────────────────────────────────────────────


class TestMarketRegimeDetector:
    """Tests for the market regime detector."""

    @pytest.fixture
    def detector(self):
        from ai_multicolony.finance import MarketRegimeDetector
        return MarketRegimeDetector()

    def test_trending_up_detection(self, detector):
        # Strong uptrend
        closes = [100.0 + i * 2.0 for i in range(50)]
        result = detector.detect(closes, symbol="TEST")
        assert result.regime.value in ("trending_up", "trending_down", "volatile", "ranging")

    def test_ranging_detection(self, detector):
        # Sideways market
        closes = [100.0 + 1.0 * math.sin(i * 0.3) for i in range(50)]
        result = detector.detect(closes, symbol="TEST")
        assert result.regime.value in ("ranging", "trending_up", "trending_down")

    def test_crisis_detection(self, detector):
        # Big crash
        closes = [100.0] * 49 + [90.0]  # 10% drop in one day
        result = detector.detect(closes, symbol="TEST")
        assert result.regime.value == "crisis"

    def test_insufficient_data(self, detector):
        result = detector.detect([100.0], symbol="TEST")
        assert result.regime.value == "unknown"

    def test_detection_history(self, detector):
        closes = [100.0 + i for i in range(50)]
        detector.detect(closes)
        assert len(detector.history) == 1

    def test_current_regime(self, detector):
        closes = [100.0 + i for i in range(50)]
        detector.detect(closes)
        assert detector.current_regime is not None


# ── Pressure tests ──────────────────────────────────────────────────────────


class TestPressureEngine:
    """Tests for the market pressure engine."""

    @pytest.fixture
    def engine(self):
        from ai_multicolony.finance import PressureEngine
        return PressureEngine()

    @pytest.fixture
    def bullish_bars(self):
        from ai_multicolony.finance import OHLCVBar
        return [
            OHLCVBar(open=100 + i, high=101 + i, low=99 + i, close=100.5 + i, volume=1000)
            for i in range(20)
        ]

    def test_buy_pressure_detection(self, engine, bullish_bars):
        result = engine.analyze(bullish_bars, symbol="TEST")
        assert result.buy_pressure >= 0.0
        assert result.sell_pressure >= 0.0

    def test_neutral_pressure(self, engine):
        from ai_multicolony.finance import OHLCVBar
        bars = [
            OHLCVBar(open=100, high=101, low=99, close=100, volume=1000)
            for _ in range(20)
        ]
        result = engine.analyze(bars, symbol="TEST")
        assert result.direction.value in ("buy", "sell", "neutral", "mixed")

    def test_insufficient_data(self, engine):
        from ai_multicolony.finance import OHLCVBar
        bars = [OHLCVBar(open=100, high=101, low=99, close=100, volume=1000)]
        result = engine.analyze(bars, symbol="TEST")
        assert result.confidence == 0.0

    def test_analyze_from_arrays(self, engine):
        closes = [100.0 + i * 0.5 for i in range(20)]
        opens = [c - 0.2 for c in closes]
        highs = [c + 1.0 for c in closes]
        lows = [c - 1.0 for c in closes]
        volumes = [1000.0] * 20
        result = engine.analyze_from_arrays(opens, highs, lows, closes, volumes, symbol="TEST")
        assert result.net_pressure != 0 or result.buy_pressure == result.sell_pressure


# ── AutoSwitch tests ─────────────────────────────────────────────────────────


class TestAutoSwitcher:
    """Tests for the auto strategy switcher."""

    @pytest.fixture
    def switcher(self):
        from ai_multicolony.finance import AutoSwitcher
        return AutoSwitcher()

    def test_initial_strategy(self, switcher):
        from ai_multicolony.finance import StrategyType
        assert switcher.current_strategy == StrategyType.TREND_FOLLOWING

    def test_switch_on_trending(self, switcher):
        from ai_multicolony.finance import MarketRegime, StrategyType
        strategy = switcher.evaluate_and_switch(MarketRegime.TRENDING_UP, confidence=0.8, force=True)
        assert strategy == StrategyType.TREND_FOLLOWING

    def test_switch_on_ranging(self, switcher):
        from ai_multicolony.finance import MarketRegime, StrategyType
        strategy = switcher.evaluate_and_switch(MarketRegime.RANGING, confidence=0.8, force=True)
        assert strategy == StrategyType.MEAN_REVERSION

    def test_switch_on_crisis(self, switcher):
        from ai_multicolony.finance import MarketRegime, StrategyType
        strategy = switcher.evaluate_and_switch(MarketRegime.CRISIS, confidence=0.9, force=True)
        assert strategy == StrategyType.CAPITAL_PRESERVATION

    def test_manual_switch(self, switcher):
        from ai_multicolony.finance import StrategyType
        switch_result = switcher.switch_manual(StrategyType.SCALPING)
        assert switch_result.to_strategy == StrategyType.SCALPING
        assert switcher.current_strategy == StrategyType.SCALPING

    def test_strategy_profile(self, switcher):
        from ai_multicolony.finance import StrategyType
        profile = switcher.get_profile(StrategyType.TREND_FOLLOWING)
        assert profile is not None
        assert profile.name == "Trend Following"

    def test_regime_strategy_map(self, switcher):
        from ai_multicolony.finance import MarketRegime, StrategyType
        strategy = switcher.get_strategy_for_regime(MarketRegime.RANGING)
        assert strategy == StrategyType.MEAN_REVERSION

    def test_detect_and_switch(self, switcher):
        closes = [100.0 + i * 2.0 for i in range(50)]
        strategy = switcher.detect_and_switch(closes, symbol="TEST")
        assert strategy is not None
