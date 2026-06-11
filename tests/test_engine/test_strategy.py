"""Tests for Engine Strategy module — loader, parser, schema."""

import os
import tempfile

import pytest

from quant_nanggroe_ai.engine.strategy.schema import (
    StrategyConfig,
    EntryRule,
    ExitRule,
    IndicatorType,
    OperatorType,
    RiskRules,
    TimeFrameType,
    UniverseDefinition,
)


# ─── Strategy Schema ──────────────────────────────────────────────────────────


class TestIndicatorType:
    """Tests for IndicatorType enum."""

    def test_all_types(self):
        assert IndicatorType.SMA is not None
        assert IndicatorType.EMA is not None
        assert IndicatorType.RSI is not None


class TestOperatorType:
    """Tests for OperatorType enum."""

    def test_all_types(self):
        assert OperatorType.GT is not None
        assert OperatorType.LT is not None
        assert OperatorType.EQ is not None


class TestTimeFrameType:
    """Tests for TimeFrameType enum."""

    def test_all_types(self):
        assert TimeFrameType.M1 is not None
        assert TimeFrameType.H1 is not None
        assert TimeFrameType.D1 is not None


class TestEntryRule:
    """Tests for EntryRule model."""

    def test_creation(self):
        rule = EntryRule(
            indicator=IndicatorType.RSI,
            operator=OperatorType.LT,
            value=30.0,
        )
        assert rule.indicator == IndicatorType.RSI
        assert rule.operator == OperatorType.LT
        assert rule.value == 30.0


class TestExitRule:
    """Tests for ExitRule model."""

    def test_creation(self):
        rule = ExitRule(
            indicator=IndicatorType.RSI,
            operator=OperatorType.GT,
            value=70.0,
        )
        assert rule.indicator == IndicatorType.RSI
        assert rule.value == 70.0


class TestStrategyConfig:
    """Tests for StrategyConfig model."""

    def test_creation(self):
        entry = EntryRule(
            indicator=IndicatorType.RSI,
            operator=OperatorType.LT,
            value=30.0,
        )
        exit_r = ExitRule(
            indicator=IndicatorType.RSI,
            operator=OperatorType.GT,
            value=70.0,
        )
        config = StrategyConfig(
            name="test_strategy",
            timeframe=TimeFrameType.H1,
            universe=UniverseDefinition(symbols=["BTC/USDT"]),
            entry_rules=[entry],
            exit_rules=[exit_r],
            risk_rules=RiskRules(),
        )
        assert config.name == "test_strategy"
        assert config.timeframe == TimeFrameType.H1
        assert len(config.entry_rules) == 1


# ─── Strategy Loader ──────────────────────────────────────────────────────────


class TestStrategyLoader:
    """Tests for StrategyLoader."""

    def test_loader_import(self):
        from quant_nanggroe_ai.engine.strategy.loader import StrategyLoader
        assert StrategyLoader is not None

    def test_loader_creation(self):
        from quant_nanggroe_ai.engine.strategy.loader import StrategyLoader
        loader = StrategyLoader()
        assert loader is not None


# ─── Strategy Parser ──────────────────────────────────────────────────────────


class TestStrategyParser:
    """Tests for strategy parser module."""

    def test_parser_import(self):
        from quant_nanggroe_ai.engine.strategy import parser
        assert parser is not None

    def test_parser_has_strategy_config(self):
        from quant_nanggroe_ai.engine.strategy.parser import StrategyConfig
        assert StrategyConfig is not None


# ─── Engine Risk Constants ────────────────────────────────────────────────────


class TestConstitutionalRules:
    """Tests for Constitutional Risk Constants."""

    def test_constants_import(self):
        from quant_nanggroe_ai.engine.risk.constants import (
            MAX_RISK_PER_TRADE,
            MAX_DAILY_LOSS,
            MAX_WEEKLY_LOSS,
            MIN_RISK_REWARD,
            MAX_CORRELATED_POSITIONS,
            MAX_POSITION_SIZE_PCT,
            MAX_LEVERAGE,
            MAX_DRAWDOWN_PCT,
            MAX_DAILY_TRADES,
            CONFIDENCE_THRESHOLD,
            KILL_SWITCH_DAILY_PNL,
            KILL_SWITCH_WEEKLY_PNL,
        )
        assert MAX_RISK_PER_TRADE == 0.005
        assert MAX_DAILY_LOSS == 0.01
        assert MAX_WEEKLY_LOSS == 0.03
        assert MIN_RISK_REWARD == 2.0
        assert MAX_CORRELATED_POSITIONS == 3
        assert MAX_POSITION_SIZE_PCT == 0.10
        assert MAX_LEVERAGE == 3.0
        assert MAX_DRAWDOWN_PCT == 0.15
        assert MAX_DAILY_TRADES == 5
        assert CONFIDENCE_THRESHOLD == 0.65
        assert KILL_SWITCH_DAILY_PNL == -0.02
        assert KILL_SWITCH_WEEKLY_PNL == -0.05

    def test_max_leverage_within_bounds(self):
        from quant_nanggroe_ai.engine.risk.constants import MAX_LEVERAGE
        assert 0 < MAX_LEVERAGE <= 5.0  # Reasonable upper bound

    def test_daily_loss_less_than_weekly(self):
        from quant_nanggroe_ai.engine.risk.constants import MAX_DAILY_LOSS, MAX_WEEKLY_LOSS
        assert MAX_DAILY_LOSS < MAX_WEEKLY_LOSS

    def test_kill_switch_daily_greater_than_weekly(self):
        """Kill switch daily PnL is less negative than weekly (less tolerance daily)."""
        from quant_nanggroe_ai.engine.risk.constants import KILL_SWITCH_DAILY_PNL, KILL_SWITCH_WEEKLY_PNL
        assert KILL_SWITCH_DAILY_PNL > KILL_SWITCH_WEEKLY_PNL


# ─── Engine Risk Emotional Lockout ────────────────────────────────────────────


class TestEmotionalLockout:
    """Tests for Emotional Lockout risk module."""

    def test_import(self):
        from quant_nanggroe_ai.engine.risk.emotional_lockout import EmotionalLockoutService
        assert EmotionalLockoutService is not None

    def test_creation(self):
        from quant_nanggroe_ai.engine.risk.emotional_lockout import EmotionalLockoutService
        service = EmotionalLockoutService()
        assert service is not None

    def test_lockout_reasons(self):
        from quant_nanggroe_ai.engine.risk.emotional_lockout import LockoutReason
        assert LockoutReason is not None

    def test_lockout_states(self):
        from quant_nanggroe_ai.engine.risk.emotional_lockout import LockoutState
        assert LockoutState is not None


# ─── Engine Risk Kelly Criterion ───────────────────────────────────────────────


class TestKellyCriterion:
    """Tests for Kelly Criterion module."""

    def test_import(self):
        from quant_nanggroe_ai.engine.risk.kelly import KellyCriterion
        assert KellyCriterion is not None

    def test_creation(self):
        from quant_nanggroe_ai.engine.risk.kelly import KellyCriterion
        kelly = KellyCriterion()
        assert kelly is not None


# ─── Engine Risk Manager ──────────────────────────────────────────────────────


class TestRiskManager:
    """Tests for Risk Manager module."""

    def test_import(self):
        from quant_nanggroe_ai.engine.risk.manager import RiskManager
        assert RiskManager is not None
