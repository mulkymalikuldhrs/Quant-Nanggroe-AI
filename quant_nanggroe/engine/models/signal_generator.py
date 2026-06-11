"""ML Signal Generator — Generate trading signals with confidence scores.

Combines multiple ML model predictions into actionable trading signals
with risk-adjusted position sizing recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.models.base import BaseModel, PredictionResult
from quant_nanggroe.engine.models.ensemble import EnsembleModel
from quant_nanggroe.engine.risk.constants import MAX_RISK_PER_TRADE

logger = logging.getLogger(__name__)


@dataclass
class TradingSignal:
    """A trading signal with position recommendation.

    Attributes:
        symbol: Trading symbol.
        direction: 1 (long), -1 (short), 0 (neutral).
        strength: Signal strength (0-1).
        confidence: Model confidence (0-1).
        suggested_size: Suggested position size as fraction of portfolio.
        models_agree: Whether all models agree on direction.
        metadata: Additional signal metadata.
    """

    symbol: str
    direction: int
    strength: float
    confidence: float
    suggested_size: float
    models_agree: bool
    metadata: Dict[str, Any]


class SignalGenerator:
    """ML Signal Generator.

    Takes ML model predictions and converts them into actionable
    trading signals with risk-adjusted position sizing.

    Features:
    - Multi-model signal aggregation
    - Confidence-based position sizing
    - Risk-adjusted signal filtering
    - Signal strength normalization
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        signal_threshold: float = 0.02,
        max_position_fraction: float = MAX_RISK_PER_TRADE,
    ) -> None:
        """Initialize signal generator.

        Args:
            min_confidence: Minimum model confidence to generate signal.
            signal_threshold: Minimum signal strength to act on.
            max_position_fraction: Maximum position as fraction of portfolio.
        """
        self._min_confidence = min_confidence
        self._signal_threshold = signal_threshold
        self._max_position_fraction = min(max_position_fraction, MAX_RISK_PER_TRADE)
        self._models: List[BaseModel] = []

    def add_model(self, model: BaseModel) -> None:
        """Add an ML model to the signal generator.

        Args:
            model: BaseModel instance.
        """
        self._models.append(model)

    def generate_signals(
        self,
        features: Dict[str, pd.DataFrame],
        portfolio_value: float = 1_000_000.0,
    ) -> List[TradingSignal]:
        """Generate trading signals from features.

        Args:
            features: Dict mapping symbol -> feature DataFrame.
            portfolio_value: Current portfolio value.

        Returns:
            List of TradingSignal objects.
        """
        signals: List[TradingSignal] = []

        for symbol, df in features.items():
            if df.empty:
                continue

            # Get predictions from all models
            all_predictions: List[PredictionResult] = []

            for model in self._models:
                if not model.is_trained:
                    continue
                try:
                    preds = model.predict(df)
                    if preds:
                        # Use the last prediction (most recent)
                        all_predictions.append(preds[-1])
                except Exception as exc:
                    logger.warning("Model %s failed for %s: %s", model.name, symbol, exc)

            if not all_predictions:
                continue

            # Aggregate predictions
            signal = self._aggregate_predictions(
                symbol, all_predictions, portfolio_value
            )
            if signal is not None:
                signals.append(signal)

        return signals

    def _aggregate_predictions(
        self,
        symbol: str,
        predictions: List[PredictionResult],
        portfolio_value: float,
    ) -> Optional[TradingSignal]:
        """Aggregate multiple model predictions into a single signal.

        Args:
            symbol: Trading symbol.
            predictions: List of PredictionResult objects.
            portfolio_value: Current portfolio value.

        Returns:
            TradingSignal or None if no actionable signal.
        """
        # Weighted average of signals (weighted by confidence)
        total_confidence = sum(p.confidence for p in predictions)
        if total_confidence <= 0:
            return None

        weighted_signal = sum(p.signal * p.confidence for p in predictions) / total_confidence
        avg_confidence = total_confidence / len(predictions)

        # Check minimum confidence
        if avg_confidence < self._min_confidence:
            return None

        # Determine direction
        if abs(weighted_signal) < self._signal_threshold:
            direction = 0
        else:
            direction = 1 if weighted_signal > 0 else -1

        if direction == 0:
            return None

        # Signal strength (normalized to 0-1)
        strength = min(abs(weighted_signal), 1.0)

        # Models agreement
        directions = [np.sign(p.signal) for p in predictions if p.signal != 0]
        models_agree = len(set(directions)) <= 1 if directions else False

        # Position sizing (confidence-weighted, capped at constitutional limit)
        suggested_size = min(
            strength * avg_confidence * self._max_position_fraction,
            self._max_position_fraction,
        )

        return TradingSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=avg_confidence,
            suggested_size=suggested_size,
            models_agree=models_agree,
            metadata={
                "weighted_signal": weighted_signal,
                "num_models": len(predictions),
                "model_names": [p.model_name for p in predictions],
            },
        )
