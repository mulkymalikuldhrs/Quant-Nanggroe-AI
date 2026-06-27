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
    "Momentum", "MeanReversion", "PairsTrading", "VolatilityArbitrage",
    "StatisticalArbitrage", "MarketMaking", "RegimeBased", "CryptoSpecific",
]

REGIME_STRATEGY_MAP: Dict[str, List[StrategyConfig]] = {
    "bull_trend": [
        StrategyConfig("Momentum", {"lookback": 126, "signal_smoothing": 10}, weight=0.35,
                       Kelly={"fraction": 0.35}),
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 378}, weight=0.30,
                       Kelly={"fraction": 0.30}),
        StrategyConfig("CryptoSpecific", {"lookback": 12, "entry_threshold": 0.0005}, weight=0.20,
                       Kelly={"fraction": 0.20}),
        StrategyConfig("StatisticalArbitrage", {"lookback": 60, "n_factors": 5}, weight=0.15,
                       Kelly={"fraction": 0.15}),
    ],
    "bear_trend": [
        StrategyConfig("PairsTrading", {"lookback": 120, "hedge_ratio_lookback": 252}, weight=0.30,
                       Kelly={"fraction": 0.15}),
        StrategyConfig("MarketMaking", {"gamma": 0.05, "spread_multiplier": 3.0}, weight=0.25,
                       Kelly={"fraction": 0.10}),
        StrategyConfig("StatisticalArbitrage", {"lookback": 120, "n_factors": 3}, weight=0.25,
                       Kelly={"fraction": 0.12}),
        StrategyConfig("MeanReversion", {"entry_threshold": 3.0}, weight=0.20,
                       Kelly={"fraction": 0.08}),
    ],
    "high_volatility": [
        StrategyConfig("MeanReversion", {"lookback": 10, "entry_threshold": 2.5}, weight=0.35,
                       Kelly={"fraction": 0.12}),
        StrategyConfig("VolatilityArbitrage", {"entry_threshold": 2.5}, weight=0.30,
                       Kelly={"fraction": 0.10}),
        StrategyConfig("MarketMaking", {"gamma": 0.1, "spread_multiplier": 2.5}, weight=0.20,
                       Kelly={"fraction": 0.08}),
        StrategyConfig("StatisticalArbitrage", {"lookback": 30, "n_factors": 2}, weight=0.15,
                       Kelly={"fraction": 0.10}),
    ],
    "low_volatility": [
        StrategyConfig("RegimeBased", {"n_regimes": 2, "hmm_lookback": 126}, weight=0.35,
                       Kelly={"fraction": 0.40}),
        StrategyConfig("Momentum", {"lookback": 252, "signal_smoothing": 3}, weight=0.30,
                       Kelly={"fraction": 0.35}),
        StrategyConfig("CryptoSpecific", {"lookback": 48, "entry_threshold": 0.0001}, weight=0.20,
                       Kelly={"fraction": 0.25}),
        StrategyConfig("PairsTrading", {"lookback": 60, "hedge_ratio_lookback": 126}, weight=0.15,
                       Kelly={"fraction": 0.20}),
    ],
    "sideways": [
        StrategyConfig("MeanReversion", {"lookback": 20, "entry_threshold": 1.5}, weight=0.30,
                       Kelly={"fraction": 0.20}),
        StrategyConfig("PairsTrading", {"lookback": 30, "hedge_ratio_lookback": 60}, weight=0.25,
                       Kelly={"fraction": 0.18}),
        StrategyConfig("MarketMaking", {"gamma": 0.1, "spread_multiplier": 1.0}, weight=0.25,
                       Kelly={"fraction": 0.15}),
        StrategyConfig("StatisticalArbitrage", {"lookback": 30, "n_factors": 2}, weight=0.20,
                       Kelly={"fraction": 0.15}),
    ],
    "crisis": [
        StrategyConfig("RegimeBased", {"n_regimes": 3, "hmm_lookback": 252}, weight=0.35,
                       Kelly={"fraction": 0.05}),
        StrategyConfig("MarketMaking", {"gamma": 0.02, "spread_multiplier": 5.0}, weight=0.30,
                       Kelly={"fraction": 0.03}),
        StrategyConfig("PairsTrading", {"lookback": 120, "hedge_ratio_lookback": 252}, weight=0.20,
                       Kelly={"fraction": 0.04}),
        StrategyConfig("CryptoSpecific", {"lookback": 48, "entry_threshold": 0.0003}, weight=0.15,
                       Kelly={"fraction": 0.03}),
    ],
    "recovery": [
        StrategyConfig("Momentum", {"lookback": 63, "signal_smoothing": 5}, weight=0.35,
                       Kelly={"fraction": 0.40}),
        StrategyConfig("RegimeBased", {"n_regimes": 4, "hmm_lookback": 252}, weight=0.30,
                       Kelly={"fraction": 0.35}),
        StrategyConfig("CryptoSpecific", {"lookback": 24, "entry_threshold": 0.0005}, weight=0.20,
                       Kelly={"fraction": 0.25}),
        StrategyConfig("StatisticalArbitrage", {"lookback": 60, "n_factors": 5}, weight=0.15,
                       Kelly={"fraction": 0.20}),
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
