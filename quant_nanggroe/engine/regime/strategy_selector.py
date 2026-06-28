from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    Kelly: Dict[str, Any] = field(default_factory=lambda: {"fraction": 0.25})


@dataclass
class RegimeStrategyMap:
    regime: str
    active_strategies: List[StrategyConfig] = field(default_factory=list)
    risk_multiplier: float = 1.0
    regime_confidence: float = 0.0


REAL_QNA_STRATEGIES = [
    "RegimeBased",
    "MeanReversion",
    "TrendFollow",
]

REGIME_STRATEGY_MAP: Dict[str, List[StrategyConfig]] = {
    "bull_trend": [
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 378}, weight=1.0,
                       Kelly={"fraction": 0.35}),
        StrategyConfig("TrendFollow", {"fast_period": 50, "slow_period": 200, "adx_threshold": 25},
                       weight=0.8, Kelly={"fraction": 0.30}),
    ],
    "bear_trend": [
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 378}, weight=1.0,
                       Kelly={"fraction": 0.15}),
        StrategyConfig("TrendFollow", {"fast_period": 50, "slow_period": 200, "adx_threshold": 25},
                       weight=0.6, Kelly={"fraction": 0.12}),
    ],
    "high_volatility": [
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 378}, weight=1.0,
                       Kelly={"fraction": 0.12}),
    ],
    "low_volatility": [
        StrategyConfig("RegimeBased", {"n_regimes": 2, "hmm_lookback": 126}, weight=1.0,
                       Kelly={"fraction": 0.40}),
        StrategyConfig("MeanReversion", {"strategy_type": "bollinger", "lookback": 20,
                                          "bollinger_std": 2.0, "atr_stop_mult": 1.5},
                       weight=0.7, Kelly={"fraction": 0.35}),
    ],
    "sideways": [
        StrategyConfig("RegimeBased", {"n_regimes": 2, "hmm_lookback": 126}, weight=1.0,
                       Kelly={"fraction": 0.20}),
        StrategyConfig("MeanReversion", {"strategy_type": "bollinger", "lookback": 20,
                                          "bollinger_std": 2.0, "atr_stop_mult": 1.5},
                       weight=0.9, Kelly={"fraction": 0.25}),
    ],
    "crisis": [
        StrategyConfig("RegimeBased", {"n_regimes": 3, "hmm_lookback": 252}, weight=1.0,
                       Kelly={"fraction": 0.05}),
    ],
    "recovery": [
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 252}, weight=1.0,
                       Kelly={"fraction": 0.35}),
    ],
}

_RISK_MULTIPLIERS: Dict[str, float] = {
    "bull_trend": 1.0, "bear_trend": 0.4, "high_volatility": 0.4,
    "low_volatility": 1.2, "sideways": 0.6, "crisis": 0.15, "recovery": 1.0,
}

_REGIME_LABEL_MAP: Dict[str, str] = {
    "BULL": "bull_trend", "BEAR": "bear_trend", "HIGH_VOL": "high_volatility",
    "LOW_VOL": "low_volatility", "SIDEWAYS": "sideways", "CRISIS": "crisis",
}


class RegimeStrategySelector:
    def normalize_regime(self, regime_label: str) -> str:
        upper = regime_label.upper().strip()
        if upper in _REGIME_LABEL_MAP:
            return _REGIME_LABEL_MAP[upper]
        if regime_label in REGIME_STRATEGY_MAP:
            return regime_label
        return "sideways"

    def select_strategies(
        self, regime_label: str, confidence: float,
    ) -> RegimeStrategyMap:
        regime = self.normalize_regime(regime_label)
        strategies = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP["sideways"])
        risk_mult = _RISK_MULTIPLIERS.get(regime, 0.6)

        if regime == "crisis":
            risk_mult *= 0.5
        elif regime in ("high_volatility", "bear_trend") and confidence > 0.8:
            risk_mult *= 0.7

        return RegimeStrategyMap(
            regime=regime,
            active_strategies=[s for s in strategies],
            risk_multiplier=round(risk_mult, 4),
            regime_confidence=round(confidence, 4),
        )

    def get_regime_multiplier(self, regime_label: str) -> float:
        regime = self.normalize_regime(regime_label)
        return _RISK_MULTIPLIERS.get(regime, 0.6)

    def adjust_kelly(self, base_fraction: float, regime: str, confidence: float) -> float:
        regime = self.normalize_regime(regime)
        mult = _RISK_MULTIPLIERS.get(regime, 0.6)
        adjusted = base_fraction * mult
        if confidence < 0.5:
            adjusted *= 0.5
        elif confidence > 0.9:
            adjusted *= 1.1
        return round(max(0.01, min(adjusted, 1.0)), 4)

    def get_strategy_names(self, regime_label: str) -> List[str]:
        regime = self.normalize_regime(regime_label)
        strategies = REGIME_STRATEGY_MAP.get(regime, REGIME_STRATEGY_MAP["sideways"])
        return [s.name for s in strategies]
