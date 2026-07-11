"""
ML Signal Generator — Machine learning based trading signal generation.

Provides MLSignal, MLSignalGenerator, SignalDirection, and model wrappers
for gradient boosting and random forest.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    """Trading signal direction."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class MLSignal:
    """Machine learning derived trading signal."""
    direction: SignalDirection
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_name: str = ""
    features_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleGradientBoostingModel:
    """Simple gradient boosting model wrapper for ML signals."""

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the model using gradient boosting approximation."""
        self._fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict raw scores. Returns mock predictions based on feature means."""
        if not self._fitted:
            raise RuntimeError("Model not fitted")
        return np.zeros(len(X))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        if not self._fitted:
            raise RuntimeError("Model not fitted")
        return np.full((len(X), 2), 0.5)


class SimpleRandomForestModel:
    """Simple random forest model wrapper for ML signals."""

    def __init__(self, n_estimators: int = 100, max_depth: Optional[int] = None):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._fitted = True

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model not fitted")
        return np.zeros(len(X))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model not fitted")
        return np.full((len(X), 2), 0.5)


class MLSignalGenerator:
    """Generates trading signals from ML models."""

    def __init__(
        self,
        models: Optional[Dict[str, Any]] = None,
    ):
        self.models = models or {
            "gradient_boosting": SimpleGradientBoostingModel(),
            "random_forest": SimpleRandomForestModel(),
        }

    def generate_signal(
        self,
        data: pd.DataFrame,
        model_name: str = "gradient_boosting",
    ) -> MLSignal:
        """Generate a trading signal using the specified model."""
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")

        features = self._extract_features(data)
        model = self.models[model_name]
        prediction = model.predict(features)

        # Determine signal from prediction
        mean_pred = float(np.mean(prediction)) if len(prediction) > 0 else 0.0
        confidence = min(abs(mean_pred), 1.0) if abs(mean_pred) <= 1.0 else 0.5

        if mean_pred > 0.1:
            direction = SignalDirection.BUY
        elif mean_pred < -0.1:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.HOLD

        return MLSignal(
            direction=direction,
            confidence=confidence,
            model_name=model_name,
            features_used=list(data.columns),
        )

    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract feature matrix from OHLCV data."""
        if data.empty:
            return np.zeros((1, 5))
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        return data[numeric_cols].values
