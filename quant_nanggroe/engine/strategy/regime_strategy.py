"""
Strategy that dynamically adapts to detected market regimes.
"""
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
import logging

from quant_nanggroe.engine.regime.strategy_selector import (
    RegimeStrategySelector,
    StrategyConfig,
    RegimeStrategyMap,
)
from quant_nanggroe.engine.regime.hmm_detector import Regime

logger = logging.getLogger(__name__)

try:
    from quant_nanggroe.engine.regime.ensemble import RegimeEnsemble
    from quant_nanggroe.engine.regime.hmm_detector import HMMRegimeDetector
    from quant_nanggroe.engine.regime.volatility_clustering import VolatilityRegimeDetector
    from quant_nanggroe.engine.regime.macro_regime import MacroRegimeDetector
    from quant_nanggroe.engine.regime.correlation_regime import CorrelationRegimeDetector
    _CAN_ENSEMBLE = True
except ImportError:
    _CAN_ENSEMBLE = False


class RegimeAdaptiveStrategy:
    """
    Trading strategy that automatically adjusts based on detected market regime.

    Combines regime detection + strategy selection + Kelly sizing.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.selector = RegimeStrategySelector()
        self.detector = self._build_detector()
        self.current_regime = "unknown"
        self.current_map: Optional[RegimeStrategyMap] = None

    def _build_detector(self):
        if not _CAN_ENSEMBLE:
            return None
        hmm = HMMRegimeDetector(
            n_regimes=self.config.get("n_regimes", 4),
            lookback=self.config.get("lookback", 252),
        )
        vol = VolatilityRegimeDetector(
            lookback=self.config.get("volatility_window", 21),
        )
        detectors = [hmm, vol]
        try:
            detectors.append(MacroRegimeDetector())
        except Exception:
            pass
        try:
            detectors.append(CorrelationRegimeDetector())
        except Exception:
            pass
        return RegimeEnsemble(detectors)

    async def analyze(self, prices: pd.DataFrame) -> Dict[str, Any]:
        close = prices.get("close", prices.iloc[:, 0]) if prices is not None else pd.Series(dtype=float)
        returns = close.pct_change().dropna().tolist()
        volumes = None
        if "volume" in prices.columns:
            volumes = prices["volume"].tolist()

        regime_result = None
        confidence = 0.5

        if self.detector is not None and returns:
            try:
                regime_result = self.detector.predict(
                    recent_returns=returns,
                    recent_volumes=volumes,
                    returns=returns,
                )
                if regime_result is not None:
                    regime_value = regime_result.regime.value if hasattr(regime_result.regime, "value") else str(regime_result.regime)
                    self.current_regime = regime_value
                    confidence = regime_result.confidence
            except Exception as exc:
                logger.warning("regime_detection_failed", extra={"error": str(exc)})
                self.current_regime = "SIDEWAYS"

        regime_label = self.current_regime

        self.current_map = self.selector.select_strategy(
            regime_label,
            confidence,
            self._get_available_strategies(),
        )

        adjusted_kelly = self.selector.adjust_kelly_for_regime(
            self.current_map.primary_strategy.Kelly.get("fraction", 0.25),
            regime_label,
            confidence,
        )

        return {
            "regime": regime_label,
            "confidence": round(confidence, 4),
            "recommended_strategy": self.current_map.primary_strategy.name,
            "risk_multiplier": self.current_map.risk_multiplier,
            "kelly_adjustment": {
                **self.current_map.primary_strategy.Kelly,
                "adjusted_fraction": adjusted_kelly,
            },
            "secondary_strategies": [s.name for s in self.current_map.secondary_strategies],
        }

    def _get_available_strategies(self) -> List[StrategyConfig]:
        return [
            StrategyConfig(
                name="trend_follow",
                params={"ma_fast": 20, "ma_slow": 50},
                Kelly={"fraction": 0.5},
            ),
            StrategyConfig(
                name="mean_reversion",
                params={"window": 20, "std": 2},
                Kelly={"fraction": 0.25},
            ),
            StrategyConfig(
                name="momentum",
                params={"lookback": 60},
                Kelly={"fraction": 0.4},
            ),
            StrategyConfig(
                name="defensive",
                params={"max_drawdown": 0.05},
                Kelly={"fraction": 0.1},
            ),
        ]
