"""Auto strategy switching for the AI-MultiColony finance module.

Automatically switches between trading strategies based on detected
market conditions.  Different strategies are optimal for different
regimes:

* Trending markets → Trend-following strategies
* Ranging markets → Mean-reversion strategies
* Volatile markets → Breakout / hedging strategies
* Crisis → Capital preservation / hedging

The auto-switcher integrates with the regime detector and risk
guard to ensure safe strategy transitions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .market_state import MarketRegimeDetector, MarketRegime, RegimeResult

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class StrategyType(str, Enum):
    """Available trading strategy types."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    HEDGING = "hedging"
    CAPITAL_PRESERVATION = "capital_preservation"
    SCALPING = "scalping"
    PAUSED = "paused"


class SwitchReason(str, Enum):
    """Reason for a strategy switch."""
    REGIME_CHANGE = "regime_change"
    RISK_LIMIT = "risk_limit"
    PERFORMANCE = "performance"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    KILL_SWITCH = "kill_switch"


# ── Models ───────────────────────────────────────────────────────────────────


class StrategyProfile(BaseModel):
    """Profile for a trading strategy."""
    model_config = ConfigDict(frozen=False)

    strategy_type: StrategyType = StrategyType.TREND_FOLLOWING
    name: str = ""
    description: str = ""
    optimal_regimes: List[MarketRegime] = Field(default_factory=list)
    risk_appetite: float = 0.5  # 0 (conservative) to 1 (aggressive)
    expected_return_pct: float = 0.0
    max_drawdown_pct: float = 5.0
    win_rate: float = 0.5
    avg_holding_period: str = "1d"
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategySwitch(BaseModel):
    """Record of a strategy switch."""
    model_config = ConfigDict(frozen=False)

    switch_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_strategy: StrategyType = StrategyType.PAUSED
    to_strategy: StrategyType = StrategyType.PAUSED
    reason: SwitchReason = SwitchReason.REGIME_CHANGE
    regime: MarketRegime = MarketRegime.UNKNOWN
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved: bool = True


class AutoSwitchConfig(BaseModel):
    """Configuration for auto strategy switching."""
    model_config = ConfigDict(frozen=False)

    enable_auto_switch: bool = True
    min_regime_confidence: float = 0.6
    cooldown_periods: int = 3      # Minimum bars between switches
    require_confirmation: bool = True  # Require regime confirmation
    max_switches_per_day: int = 4
    pause_on_crisis: bool = True
    default_strategy: StrategyType = StrategyType.TREND_FOLLOWING


# ── Default strategy mappings ───────────────────────────────────────────────

REGIME_STRATEGY_MAP: Dict[MarketRegime, StrategyType] = {
    MarketRegime.TRENDING_UP: StrategyType.TREND_FOLLOWING,
    MarketRegime.TRENDING_DOWN: StrategyType.HEDGING,
    MarketRegime.RANGING: StrategyType.MEAN_REVERSION,
    MarketRegime.VOLATILE: StrategyType.BREAKOUT,
    MarketRegime.CRISIS: StrategyType.CAPITAL_PRESERVATION,
    MarketRegime.RECOVERY: StrategyType.MOMENTUM,
    MarketRegime.UNKNOWN: StrategyType.PAUSED,
}

STRATEGY_PROFILES: Dict[StrategyType, StrategyProfile] = {
    StrategyType.TREND_FOLLOWING: StrategyProfile(
        strategy_type=StrategyType.TREND_FOLLOWING,
        name="Trend Following",
        description="Follows established price trends using moving averages and breakout signals",
        optimal_regimes=[MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN],
        risk_appetite=0.6,
        expected_return_pct=15.0,
        max_drawdown_pct=8.0,
        win_rate=0.45,
        avg_holding_period="5d",
    ),
    StrategyType.MEAN_REVERSION: StrategyProfile(
        strategy_type=StrategyType.MEAN_REVERSION,
        name="Mean Reversion",
        description="Trades against extremes, expecting return to mean",
        optimal_regimes=[MarketRegime.RANGING],
        risk_appetite=0.4,
        expected_return_pct=10.0,
        max_drawdown_pct=5.0,
        win_rate=0.55,
        avg_holding_period="1d",
    ),
    StrategyType.BREAKOUT: StrategyProfile(
        strategy_type=StrategyType.BREAKOUT,
        name="Breakout",
        description="Trades breakouts from consolidation patterns",
        optimal_regimes=[MarketRegime.VOLATILE],
        risk_appetite=0.7,
        expected_return_pct=20.0,
        max_drawdown_pct=10.0,
        win_rate=0.35,
        avg_holding_period="2d",
    ),
    StrategyType.MOMENTUM: StrategyProfile(
        strategy_type=StrategyType.MOMENTUM,
        name="Momentum",
        description="Rides short-term momentum waves",
        optimal_regimes=[MarketRegime.RECOVERY, MarketRegime.TRENDING_UP],
        risk_appetite=0.5,
        expected_return_pct=12.0,
        max_drawdown_pct=6.0,
        win_rate=0.50,
        avg_holding_period="3d",
    ),
    StrategyType.HEDGING: StrategyProfile(
        strategy_type=StrategyType.HEDGING,
        name="Hedging",
        description="Hedges existing positions against adverse moves",
        optimal_regimes=[MarketRegime.TRENDING_DOWN, MarketRegime.VOLATILE],
        risk_appetite=0.2,
        expected_return_pct=3.0,
        max_drawdown_pct=2.0,
        win_rate=0.70,
        avg_holding_period="7d",
    ),
    StrategyType.CAPITAL_PRESERVATION: StrategyProfile(
        strategy_type=StrategyType.CAPITAL_PRESERVATION,
        name="Capital Preservation",
        description="Protects capital during crisis; minimal exposure",
        optimal_regimes=[MarketRegime.CRISIS],
        risk_appetite=0.1,
        expected_return_pct=1.0,
        max_drawdown_pct=1.0,
        win_rate=0.80,
        avg_holding_period="1d",
    ),
    StrategyType.SCALPING: StrategyProfile(
        strategy_type=StrategyType.SCALPING,
        name="Scalping",
        description="High-frequency small-profit trades",
        optimal_regimes=[MarketRegime.RANGING],
        risk_appetite=0.6,
        expected_return_pct=8.0,
        max_drawdown_pct=3.0,
        win_rate=0.60,
        avg_holding_period="1h",
    ),
}


# ── Auto Switcher ────────────────────────────────────────────────────────────


class AutoSwitcher:
    """Automatically switches strategies based on market conditions.

    Integrates with the regime detector to select optimal strategies
    for the current market environment.

    Usage::

        switcher = AutoSwitcher()
        # Detect regime and switch
        strategy = switcher.evaluate_and_switch(
            regime=MarketRegime.TRENDING_UP,
            confidence=0.8,
        )
    """

    def __init__(
        self,
        config: Optional[AutoSwitchConfig] = None,
        regime_detector: Optional[MarketRegimeDetector] = None,
    ):
        self._config = config or AutoSwitchConfig()
        self._regime_detector = regime_detector or MarketRegimeDetector()
        self._current_strategy: StrategyType = self._config.default_strategy
        self._switches: List[StrategySwitch] = []
        self._cooldown_remaining: int = 0
        self._switches_today: int = 0

    def evaluate_and_switch(
        self,
        regime: MarketRegime,
        confidence: float = 0.0,
        force: bool = False,
    ) -> StrategyType:
        """Evaluate market regime and switch strategy if appropriate.

        Parameters
        ----------
        regime:
            Detected market regime.
        confidence:
            Confidence of regime detection.
        force:
            Force switch regardless of cooldown.

        Returns
        -------
        StrategyType
            The current (possibly switched) strategy.
        """
        if not self._config.enable_auto_switch and not force:
            return self._current_strategy

        # Check confidence threshold
        if confidence < self._config.min_regime_confidence and not force:
            logger.debug(
                "Regime confidence %.2f below threshold %.2f",
                confidence, self._config.min_regime_confidence,
            )
            return self._current_strategy

        # Check cooldown
        if self._cooldown_remaining > 0 and not force:
            self._cooldown_remaining -= 1
            return self._current_strategy

        # Check daily switch limit
        if self._switches_today >= self._config.max_switches_per_day and not force:
            logger.debug("Daily switch limit reached (%d)", self._config.max_switches_per_day)
            return self._current_strategy

        # Determine optimal strategy
        target_strategy = REGIME_STRATEGY_MAP.get(regime, self._config.default_strategy)

        # Crisis override
        if regime == MarketRegime.CRISIS and self._config.pause_on_crisis:
            target_strategy = StrategyType.CAPITAL_PRESERVATION

        # Already on the right strategy
        if target_strategy == self._current_strategy:
            return self._current_strategy

        # Execute switch
        switch = StrategySwitch(
            from_strategy=self._current_strategy,
            to_strategy=target_strategy,
            reason=SwitchReason.REGIME_CHANGE,
            regime=regime,
            confidence=confidence,
        )
        self._switches.append(switch)
        self._current_strategy = target_strategy
        self._cooldown_remaining = self._config.cooldown_periods
        self._switches_today += 1

        logger.info(
            "Strategy switched: %s → %s (regime: %s, confidence: %.2f)",
            switch.from_strategy.value,
            switch.to_strategy.value,
            regime.value,
            confidence,
        )

        return self._current_strategy

    def switch_manual(
        self,
        target: StrategyType,
        reason: str = "Manual switch",
    ) -> StrategySwitch:
        """Manually switch to a specific strategy.

        Parameters
        ----------
        target:
            Target strategy type.
        reason:
            Reason for the switch.

        Returns
        -------
        StrategySwitch
            Record of the switch.
        """
        switch = StrategySwitch(
            from_strategy=self._current_strategy,
            to_strategy=target,
            reason=SwitchReason.MANUAL,
        )
        self._switches.append(switch)
        self._current_strategy = target

        logger.info("Manual strategy switch: %s → %s (%s)",
                     switch.from_strategy.value, target.value, reason)
        return switch

    def detect_and_switch(
        self,
        closes: List[float],
        volumes: Optional[List[float]] = None,
        symbol: str = "",
    ) -> StrategyType:
        """Detect market regime from price data and switch strategy.

        Parameters
        ----------
        closes:
            List of closing prices.
        volumes:
            Optional volume data.
        symbol:
            Symbol being analyzed.

        Returns
        -------
        StrategyType
            The current strategy after potential switch.
        """
        result = self._regime_detector.detect(closes, volumes, symbol)
        return self.evaluate_and_switch(result.regime, result.confidence)

    # ── Properties ──────────────────────────────────────────────────────

    @property
    def current_strategy(self) -> StrategyType:
        return self._current_strategy

    @property
    def current_profile(self) -> Optional[StrategyProfile]:
        return STRATEGY_PROFILES.get(self._current_strategy)

    @property
    def switches(self) -> List[StrategySwitch]:
        return list(self._switches)

    @property
    def config(self) -> AutoSwitchConfig:
        return self._config

    def get_strategy_for_regime(self, regime: MarketRegime) -> StrategyType:
        """Get the optimal strategy for a given regime."""
        return REGIME_STRATEGY_MAP.get(regime, self._config.default_strategy)

    def get_profile(self, strategy: StrategyType) -> Optional[StrategyProfile]:
        """Get the profile for a specific strategy."""
        return STRATEGY_PROFILES.get(strategy)

    @property
    def stats(self) -> Dict[str, Any]:
        """Switcher statistics."""
        return {
            "current_strategy": self._current_strategy.value,
            "total_switches": len(self._switches),
            "switches_today": self._switches_today,
            "cooldown_remaining": self._cooldown_remaining,
            "available_strategies": [s.value for s in StrategyType],
        }


# ── Backward-compatible alias ───────────────────────────────────────
AutoSwitchEngine = AutoSwitcher
