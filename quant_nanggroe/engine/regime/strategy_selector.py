"""
Regime-Based Strategy Selector
Maps detected market regimes to optimal strategy configurations.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Configuration for a trading strategy"""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    Kelly: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegimeStrategyMap:
    """Maps regimes to strategy configurations"""
    regime: str
    primary_strategy: StrategyConfig
    secondary_strategies: List[StrategyConfig] = field(default_factory=list)
    risk_multiplier: float = 1.0


class RegimeStrategySelector:
    """
    Selects optimal strategy based on current market regime.

    Uses the ensemble regime detection output to pick the best
    strategy configuration for current market conditions.
    """

    _REGIME_LABEL_MAP = {
        "BULL": "bull_trend",
        "BEAR": "bear_trend",
        "HIGH_VOL": "high_volatility",
        "LOW_VOL": "low_volatility",
        "SIDEWAYS": "sideways",
        "CRISIS": "crisis",
    }

    _DEFAULT_MAP = {
        "bull_trend": StrategyConfig(
            name="momentum",
            params={"mode": "dual_momentum", "lookbacks": [21, 63, 126]},
            weight=0.5,
            Kelly={"fraction": 0.5, "max_fraction": 0.75},
        ),
        "bear_trend": StrategyConfig(
            name="defensive",
            params={"max_drawdown": 0.05, "stop_loss_pct": 0.02},
            weight=0.3,
            Kelly={"fraction": 0.1, "max_fraction": 0.25},
        ),
        "high_volatility": StrategyConfig(
            name="mean_reversion",
            params={"lookback": 10, "entry_z": -2.5, "bb_std": 2.5},
            weight=0.4,
            Kelly={"fraction": 0.15, "max_fraction": 0.25},
        ),
        "low_volatility": StrategyConfig(
            name="trend_follow",
            params={"ma_fast": 20, "ma_slow": 50, "atr_multiplier": 1.5},
            weight=0.6,
            Kelly={"fraction": 0.6, "max_fraction": 0.8},
        ),
        "sideways": StrategyConfig(
            name="mean_reversion",
            params={"lookback": 20, "entry_z": -2.0, "bb_std": 2.0},
            weight=0.3,
            Kelly={"fraction": 0.2, "max_fraction": 0.3},
        ),
        "crisis": StrategyConfig(
            name="defensive",
            params={"max_drawdown": 0.02, "stop_loss_pct": 0.01},
            weight=0.1,
            Kelly={"fraction": 0.05, "max_fraction": 0.1},
        ),
        "recovery": StrategyConfig(
            name="momentum",
            params={"mode": "ts_momentum", "lookbacks": [21, 42, 63]},
            weight=0.6,
            Kelly={"fraction": 0.5, "max_fraction": 0.75},
        ),
    }

    _SECONDARY_MAP = {
        "bull_trend": [
            StrategyConfig(name="trend_follow", params={"ma_fast": 20, "ma_slow": 50}, Kelly={"fraction": 0.4}),
            StrategyConfig(name="breakout", params={"lookback": 20}, Kelly={"fraction": 0.3}),
        ],
        "bear_trend": [
            StrategyConfig(name="mean_reversion", params={"entry_z": -1.5}, Kelly={"fraction": 0.15}),
        ],
        "high_volatility": [
            StrategyConfig(name="defensive", params={"max_drawdown": 0.03}, Kelly={"fraction": 0.05}),
            StrategyConfig(name="volatility_arb", params={}, Kelly={"fraction": 0.1}),
        ],
        "low_volatility": [
            StrategyConfig(name="momentum", params={"mode": "ma_crossover"}, Kelly={"fraction": 0.5}),
        ],
        "sideways": [
            StrategyConfig(name="pairs_trading", params={}, Kelly={"fraction": 0.2}),
            StrategyConfig(name="market_making", params={}, Kelly={"fraction": 0.15}),
        ],
        "crisis": [
            StrategyConfig(name="hedging", params={"hedge_ratio": 0.5}, Kelly={"fraction": 0.02}),
        ],
        "recovery": [
            StrategyConfig(name="trend_follow", params={"ma_fast": 10, "ma_slow": 30}, Kelly={"fraction": 0.4}),
            StrategyConfig(name="mean_reversion", params={"entry_z": -1.8}, Kelly={"fraction": 0.3}),
        ],
    }

    _RISK_MULTIPLIERS = {
        "bull_trend": 1.0,
        "bear_trend": 0.5,
        "high_volatility": 0.5,
        "low_volatility": 1.2,
        "sideways": 0.7,
        "crisis": 0.2,
        "recovery": 1.0,
    }

    _KELLY_SCALES = {
        "bull_trend": 1.0,
        "bear_trend": 0.3,
        "high_volatility": 0.5,
        "low_volatility": 1.2,
        "sideways": 0.7,
        "crisis": 0.1,
        "recovery": 1.2,
    }

    def _normalize_regime(self, regime_label: str) -> str:
        upper = regime_label.upper().strip()
        if upper in self._REGIME_LABEL_MAP:
            return self._REGIME_LABEL_MAP[upper]
        if regime_label in self._DEFAULT_MAP:
            return regime_label
        return "sideways"

    def select_strategy(
        self,
        regime_label: str,
        confidence: float,
        available_strategies: Optional[List[StrategyConfig]] = None,
    ) -> RegimeStrategyMap:
        regime = self._normalize_regime(regime_label)
        primary = self._DEFAULT_MAP.get(regime, self._DEFAULT_MAP["sideways"])
        secondary = self._SECONDARY_MAP.get(regime, [])
        risk_mult = self._RISK_MULTIPLIERS.get(regime, 1.0)

        if regime == "crisis":
            risk_mult *= 0.5
        elif regime == "high_volatility" and confidence > 0.8:
            risk_mult *= 0.7

        return RegimeStrategyMap(
            regime=regime,
            primary_strategy=primary,
            secondary_strategies=secondary,
            risk_multiplier=round(risk_mult, 4),
        )

    def adjust_kelly_for_regime(
        self, base_kelly: float, regime: str, confidence: float
    ) -> float:
        regime = self._normalize_regime(regime)
        scale = self._KELLY_SCALES.get(regime, 0.5)
        adjusted = base_kelly * scale
        if confidence < 0.5:
            adjusted *= 0.5
        elif confidence > 0.9:
            adjusted *= 1.1
        return round(max(0.0, min(adjusted, 1.0)), 4)
