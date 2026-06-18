"""ML Signal Generator — Generate trading signals with ML models.

Combines Random Forest, Gradient Boosting, MLP, and Ensemble
models with feature engineering and confidence scoring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from quant_nanggroe.engine.ml.feature_engineer import FeatureEngineer, FeatureConfig
from quant_nanggroe.engine.ml.model_manager import ModelManager, ModelInfo, ModelStatus

logger = logging.getLogger(__name__)


class SignalDirection(str, Enum):
    """ML signal directions."""

    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class MLSignal(BaseModel):
    """ML-generated trading signal."""

    direction: SignalDirection = Field(default=SignalDirection.HOLD)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    probability_buy: float = Field(default=0.33, ge=0.0, le=1.0)
    probability_sell: float = Field(default=0.33, ge=0.0, le=1.0)
    model_name: str = Field(default="unknown")
    feature_importance: Dict[str, float] = Field(default_factory=dict)
    composite_score: float = Field(default=0.0)

    model_config = {"from_attributes": True}


# ── Simple ML Models (no sklearn dependency at import time) ───────────────


class SimpleRandomForestModel:
    """Simple Random Forest classifier using the existing EnsembleModel infrastructure."""

    def __init__(self, n_estimators: int = 50, max_depth: int = 5) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._trained = False
        self._trees: List[dict] = []
        self._feature_names: List[str] = []
        self._classes: np.ndarray = np.array([])

    @property
    def name(self) -> str:
        return "random_forest"

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> Dict[str, Any]:
        """Train the Random Forest model."""
        self._feature_names = list(X.columns)
        X_values = X.values
        y_values = y.values
        self._classes = np.unique(y_values)
        n_samples, n_features = X_values.shape

        self._trees = []
        for _ in range(self.n_estimators):
            # Bootstrap sample
            indices = np.random.choice(n_samples, size=n_samples, replace=True)
            X_boot = X_values[indices]
            y_boot = y_values[indices]

            # Random feature subset
            n_select = max(1, int(np.sqrt(n_features)))
            feature_indices = np.random.choice(n_features, size=n_select, replace=False)

            tree = self._build_tree(X_boot, y_boot, feature_indices, depth=0)
            self._trees.append(tree)

        self._trained = True
        return {"n_trees": len(self._trees), "n_features": n_features}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict classes."""
        if not self._trained:
            raise RuntimeError("Model not trained")

        X_values = X.values
        predictions = np.array([self._predict_tree(X_values, tree) for tree in self._trees])
        # Majority vote
        result = []
        for i in range(X_values.shape[0]):
            votes = predictions[:, i]
            # Average for regression-like output
            result.append(float(np.mean(votes)))
        return np.array(result)

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importance."""
        if not self._trained:
            return {}
        importance = {}
        for i, name in enumerate(self._feature_names):
            count = sum(1 for tree in self._trees if self._count_feature(tree, i))
            importance[name] = count / max(len(self._trees), 1)
        total = sum(importance.values()) or 1.0
        return {k: v / total for k, v in importance.items()}

    def _build_tree(
        self, X: np.ndarray, y: np.ndarray, feature_indices: np.ndarray, depth: int
    ) -> dict:
        if depth >= self.max_depth or len(y) < 5:
            return {"leaf": True, "value": float(np.mean(y))}

        best_feature = None
        best_threshold = 0.0
        best_score = -np.inf

        for fi in feature_indices:
            thresholds = np.percentile(X[:, fi], [25, 50, 75])
            for t in thresholds:
                left_mask = X[:, fi] <= t
                right_mask = ~left_mask
                if left_mask.sum() < 2 or right_mask.sum() < 2:
                    continue
                score = abs(np.mean(y[left_mask]) - np.mean(y[right_mask]))
                if score > best_score:
                    best_score = score
                    best_feature = int(fi)
                    best_threshold = t

        if best_feature is None:
            return {"leaf": True, "value": float(np.mean(y))}

        left_mask = X[:, best_feature] <= best_threshold
        right_mask = ~left_mask

        return {
            "leaf": False,
            "feature": best_feature,
            "threshold": best_threshold,
            "left": self._build_tree(X[left_mask], y[left_mask], feature_indices, depth + 1),
            "right": self._build_tree(X[right_mask], y[right_mask], feature_indices, depth + 1),
        }

    def _predict_tree(self, X: np.ndarray, tree: dict) -> np.ndarray:
        if tree["leaf"]:
            return np.full(X.shape[0], tree["value"])

        left_mask = X[:, tree["feature"]] <= tree["threshold"]
        right_mask = ~left_mask
        predictions = np.zeros(X.shape[0])
        if left_mask.any():
            predictions[left_mask] = self._predict_tree(X[left_mask], tree["left"])
        if right_mask.any():
            predictions[right_mask] = self._predict_tree(X[right_mask], tree["right"])
        return predictions

    @staticmethod
    def _count_feature(tree: dict, feature_idx: int) -> bool:
        if tree.get("leaf", False):
            return False
        if tree.get("feature") == feature_idx:
            return True
        return (
            SimpleRandomForestModel._count_feature(tree.get("left", {}), feature_idx)
            or SimpleRandomForestModel._count_feature(tree.get("right", {}), feature_idx)
        )


class SimpleGradientBoostingModel:
    """Simple Gradient Boosting model."""

    def __init__(self, n_estimators: int = 50, learning_rate: float = 0.1, max_depth: int = 3) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self._trained = False
        self._trees: List[dict] = []
        self._base_prediction: float = 0.0
        self._feature_names: List[str] = []

    @property
    def name(self) -> str:
        return "gradient_boosting"

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(self, X: pd.DataFrame, y: pd.Series, **kwargs: Any) -> Dict[str, Any]:
        self._feature_names = list(X.columns)
        X_values = X.values
        y_values = y.values

        self._base_prediction = float(np.mean(y_values))
        residuals = y_values - self._base_prediction
        self._trees = []

        for _ in range(self.n_estimators):
            tree = self._build_stump(X_values, residuals)
            predictions = self._predict_tree(X_values, tree)
            residuals -= self.learning_rate * predictions
            self._trees.append(tree)

        self._trained = True
        return {"n_trees": len(self._trees), "learning_rate": self.learning_rate}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self._trained:
            raise RuntimeError("Model not trained")
        result = np.full(X.shape[0], self._base_prediction)
        for tree in self._trees:
            result += self.learning_rate * self._predict_tree(X.values, tree)
        return result

    def feature_importance(self) -> Dict[str, float]:
        if not self._trained:
            return {}
        importance = {}
        for i, name in enumerate(self._feature_names):
            count = sum(1 for tree in self._trees if tree.get("feature") == i)
            importance[name] = count / max(len(self._trees), 1)
        total = sum(importance.values()) or 1.0
        return {k: v / total for k, v in importance.items()}

    def _build_stump(self, X: np.ndarray, y: np.ndarray) -> dict:
        n_features = X.shape[1]
        best_feature = 0
        best_threshold = 0.0
        best_score = -np.inf

        for fi in range(n_features):
            threshold = float(np.median(X[:, fi]))
            left_mask = X[:, fi] <= threshold
            right_mask = ~left_mask
            if left_mask.sum() < 2 or right_mask.sum() < 2:
                continue
            score = abs(float(np.mean(y[left_mask])) - float(np.mean(y[right_mask])))
            if score > best_score:
                best_score = score
                best_feature = fi
                best_threshold = threshold

        left_mask = X[:, best_feature] <= best_threshold
        right_mask = ~left_mask

        return {
            "feature": best_feature,
            "threshold": best_threshold,
            "left_value": float(np.mean(y[left_mask])) if left_mask.any() else 0.0,
            "right_value": float(np.mean(y[right_mask])) if right_mask.any() else 0.0,
        }

    @staticmethod
    def _predict_tree(X: np.ndarray, tree: dict) -> np.ndarray:
        left_mask = X[:, tree["feature"]] <= tree["threshold"]
        return np.where(left_mask, tree["left_value"], tree["right_value"])


# ── ML Signal Generator ──────────────────────────────────────────────────


class MLSignalGenerator:
    """ML Signal Generator.

    Combines multiple ML models (RF, GBM) with feature engineering
    to generate trading signals with confidence scores.

    Features:
    - Random Forest and Gradient Boosting models
    - Automatic feature engineering
    - Ensemble signal aggregation
    - Confidence scoring
    - Model persistence (save/load)
    """

    def __init__(
        self,
        feature_config: Optional[FeatureConfig] = None,
    ) -> None:
        self._feature_engineer = FeatureEngineer(feature_config)
        self._model_manager = ModelManager()
        self._models: Dict[str, Any] = {}

    @property
    def feature_engineer(self) -> FeatureEngineer:
        return self._feature_engineer

    @property
    def model_manager(self) -> ModelManager:
        return self._model_manager

    def add_model(self, name: str, model: Any = None) -> None:
        """Add an ML model.

        Args:
            name: Model name.
            model: Model instance. If None, creates a default GBM.
        """
        if model is None:
            model = SimpleGradientBoostingModel()
        self._models[name] = model
        self._model_manager.register_model(name, model)

    def train(
        self,
        df: pd.DataFrame,
        target_period: int = 5,
        threshold: float = 0.02,
        min_samples: int = 50,
    ) -> Dict[str, Any]:
        """Train all models on the data.

        Args:
            df: OHLCV DataFrame.
            target_period: Forward period for target creation.
            threshold: Classification threshold.
            min_samples: Minimum samples required.

        Returns:
            Dict of training results.
        """
        # Create features
        features = self._feature_engineer.engineer_features(df)

        # Create target
        target = self._feature_engineer.create_target(df, target_period, threshold)

        # Align and clean
        combined = pd.concat([features, target], axis=1).dropna()
        if len(combined) < min_samples:
            logger.warning("Insufficient samples: %d < %d", len(combined), min_samples)
            return {}

        X = combined.drop(columns=["target"])
        y = combined["target"]

        # Train each model
        results = {}
        for name, model in self._models.items():
            result = self._model_manager.train_model(name, X, y)
            results[name] = {
                "success": result.success,
                "metrics": result.metrics,
                "duration_sec": result.training_duration_sec,
                "feature_importance": result.feature_importance,
            }

            # Update feature importance
            if result.feature_importance:
                self._feature_engineer.set_feature_importance(result.feature_importance)

        return results

    def generate_signal(self, df: pd.DataFrame) -> MLSignal:
        """Generate an ensemble ML signal.

        Args:
            df: OHLCV DataFrame.

        Returns:
            MLSignal with direction, confidence, and probabilities.
        """
        if not self._models:
            return MLSignal(direction=SignalDirection.HOLD, confidence=0.0, model_name="none")

        # Create features
        features = self._feature_engineer.engineer_features(df)
        X = features.tail(1)

        if X.empty or X.isna().all().all():
            return MLSignal(direction=SignalDirection.HOLD, confidence=0.0, model_name="ensemble")

        # Get predictions from each model
        signals = []
        for name, model in self._models.items():
            try:
                if hasattr(model, "is_trained") and not model.is_trained:
                    continue
                pred = model.predict(X)
                if len(pred) > 0:
                    signals.append({"name": name, "prediction": float(pred[-1])})
            except Exception as exc:
                logger.warning("Model %s inference failed: %s", name, exc)

        if not signals:
            return MLSignal(direction=SignalDirection.HOLD, confidence=0.0, model_name="ensemble")

        # Aggregate
        total_pred = sum(s["prediction"] for s in signals) / len(signals)

        # Map to direction
        if total_pred > 0.5:
            direction = SignalDirection.STRONG_BUY
        elif total_pred > 0.1:
            direction = SignalDirection.BUY
        elif total_pred < -0.5:
            direction = SignalDirection.STRONG_SELL
        elif total_pred < -0.1:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.HOLD

        # Confidence
        confidence = min(1.0, abs(total_pred) * 0.5 + 0.3)

        # Probabilities
        prob_buy = max(0.0, min(1.0, 0.5 + total_pred * 0.3))
        prob_sell = max(0.0, min(1.0, 0.5 - total_pred * 0.3))

        # Feature importance
        importance = self._feature_engineer.get_feature_importance()

        return MLSignal(
            direction=direction,
            confidence=confidence,
            probability_buy=prob_buy,
            probability_sell=prob_sell,
            model_name="ensemble",
            feature_importance=importance,
            composite_score=total_pred,
        )
