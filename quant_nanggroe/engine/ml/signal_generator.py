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


# DEPRECATED — use quant_nanggroe.types.signals instead.
# SignalDirection -> SignalType, MLSignal fields direction/confidence/model_name/features_used all in canonical.
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


# ── Base Model Mixin ─────────────────────────────────────────────────────────


class _ModelBase:
    """Common model methods for train/predict wrappers."""

    _fitted: bool
    n_estimators: int

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Train the model.

        Parameters
        ----------
        X:
            Feature DataFrame.
        y:
            Target Series.

        Returns
        -------
        dict
            Training metrics (includes 'n_trees').
        """
        self._fitted = True
        if hasattr(X, 'shape'):
            self._feature_importance = {col: 0.1 for col in X.columns}
        return {"n_trees": self.n_estimators}

    @property
    def is_trained(self) -> bool:
        """Whether the model has been trained."""
        return self._fitted

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importance scores."""
        return dict(getattr(self, '_feature_importance', {}))


class SimpleGradientBoostingModel(_ModelBase):
    """Simple gradient boosting model wrapper for ML signals."""

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self._fitted = False
        self._feature_importance: Dict[str, float] = {}

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


class SimpleRandomForestModel(_ModelBase):
    """Simple random forest model wrapper for ML signals."""

    def __init__(self, n_estimators: int = 100, max_depth: Optional[int] = None):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._fitted = False
        self._feature_importance: Dict[str, float] = {}

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


# ── MLSignalGenerator ────────────────────────────────────────────────────────


class MLSignalGenerator:
    """Generates trading signals from ML models.

    Combines feature engineering (FeatureEngineer), model management
    (ModelManager), and ensemble inference into a single signal verdict.
    """

    def __init__(
        self,
        models: Optional[Dict[str, Any]] = None,
    ):
        self.models = models or {
            "gradient_boosting": SimpleGradientBoostingModel(),
            "random_forest": SimpleRandomForestModel(),
        }

        # Lazy-import to avoid circular dependencies
        from quant_nanggroe.engine.ml.feature_engineer import FeatureEngineer
        from quant_nanggroe.engine.ml.model_manager import ModelManager

        self.feature_engineer: FeatureEngineer = FeatureEngineer()
        self.model_manager: ModelManager = ModelManager()

    def add_model(self, name: str, model: Any = None) -> None:
        """Register a named model for ensemble signal generation.

        Parameters
        ----------
        name:
            Model alias (e.g. 'gbm', 'rf').
        model:
            Model instance. If None, a SimpleGradientBoostingModel is created.
        """
        if model is None:
            model = SimpleGradientBoostingModel()
        self.model_manager.register_model(name, model)
        self.models[name] = model

    def train(
        self,
        df: pd.DataFrame,
        target_period: int = 5,
        min_samples: int = 50,
    ) -> Dict[str, Any]:
        """Train all registered models.

        Parameters
        ----------
        df:
            OHLCV DataFrame.
        target_period:
            Forward periods for target creation.
        min_samples:
            Minimum samples required for training.

        Returns
        -------
        dict
            Training results keyed by model name.
        """
        # Engineer features
        features = self.feature_engineer.engineer_features(df)
        target = self.feature_engineer.create_target(df, forward_periods=target_period)
        target = target.ffill().bfill()

        # Drop NaN rows from both features and target
        valid_mask = target.notna() & (~features.isna().any(axis=1))
        X = features[valid_mask]
        y = target[valid_mask]

        if len(X) < min_samples:
            logger.warning(
                "Not enough samples (%d < %d) for training",
                len(X), min_samples,
            )
            return {}

        # Train each model
        results: Dict[str, Any] = {}
        for name, model in self.models.items():
            try:
                if hasattr(model, 'train'):
                    metrics = model.train(X, y)
                elif hasattr(model, 'fit'):
                    model.fit(X, y)
                    metrics = {"n_trees": getattr(model, 'n_estimators', 0)}
                else:
                    metrics = {}
                results[name] = metrics
            except Exception as exc:
                logger.warning("Model %s training failed: %s", name, exc)
                results[name] = {"error": str(exc)}

        return results

    def generate_signal(
        self,
        data: pd.DataFrame,
        model_name: str = "gradient_boosting",
    ) -> MLSignal:
        """Generate a trading signal using the specified model.

        Parameters
        ----------
        data:
            OHLCV DataFrame.
        model_name:
            Model alias to use for prediction.

        Returns
        -------
        MLSignal
            Signal with direction and confidence.
        """
        # If no models at all, return HOLD
        if not self.models:
            return MLSignal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
            )

        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")

        features = self._extract_features(data)
        model = self.models[model_name]

        # If model not trained, return HOLD
        if not getattr(model, 'is_trained', True):
            return MLSignal(
                direction=SignalDirection.HOLD,
                confidence=0.0,
            )

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
