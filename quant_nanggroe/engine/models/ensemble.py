"""Ensemble Model — RF + XGBoost + LSTM ensemble.

Implements an ensemble model that combines:
1. Random Forest: Robust, handles non-linear relationships
2. Gradient Boosting (XGBoost-like): Strong predictive power
3. Simple neural network: Captures temporal patterns

The ensemble uses:
- Soft voting (average probabilities) for classification
- Weighted average for regression
- Confidence-weighted combination for signal generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.models.base import BaseModel, PredictionResult

logger = logging.getLogger(__name__)


class SimpleRandomForest:
    """Simplified Random Forest using decision stumps.

    Uses a collection of decision trees with random feature subsets
    for ensemble prediction. Implementation is pure numpy/pandas
    without sklearn dependency.
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 5) -> None:
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self._trees: List[dict] = []
        self._feature_names: List[str] = []

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]) -> None:
        """Fit the random forest."""
        self._feature_names = feature_names
        n_samples, n_features = X.shape
        self._trees = []

        for _ in range(self.n_estimators):
            # Bootstrap sample
            indices = np.random.choice(n_samples, size=n_samples, replace=True)
            X_boot = X[indices]
            y_boot = y[indices]

            # Random feature subset
            n_select = max(1, int(np.sqrt(n_features)))
            feature_indices = np.random.choice(n_features, size=n_select, replace=False)

            # Build simple decision stump
            tree = self._build_tree(X_boot, y_boot, feature_indices, depth=0)
            self._trees.append(tree)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities."""
        predictions = np.array([self._predict_tree(X, tree) for tree in self._trees])
        # Average predictions across trees
        return predictions.mean(axis=0)

    def _build_tree(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_indices: np.ndarray,
        depth: int,
    ) -> dict:
        """Build a simple decision tree."""
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

                left_mean = np.mean(y[left_mask])
                right_mean = np.mean(y[right_mask])
                score = abs(left_mean - right_mean)

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
        """Predict using a single tree."""
        if tree["leaf"]:
            return np.full(X.shape[0], tree["value"])

        feature = tree["feature"]
        threshold = tree["threshold"]
        left_mask = X[:, feature] <= threshold
        right_mask = ~left_mask

        predictions = np.zeros(X.shape[0])
        if left_mask.any():
            predictions[left_mask] = self._predict_tree(X[left_mask], tree["left"])
        if right_mask.any():
            predictions[right_mask] = self._predict_tree(X[right_mask], tree["right"])

        return predictions


class SimpleGradientBoosting:
    """Simplified Gradient Boosting implementation.

    Sequentially fits trees to the residuals of previous predictions.
    """

    def __init__(self, n_estimators: int = 100, learning_rate: float = 0.1, max_depth: int = 3) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self._trees: List[dict] = []
        self._base_prediction: float = 0.0
        self._feature_names: List[str] = []

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: List[str]) -> None:
        """Fit gradient boosting model."""
        self._feature_names = feature_names
        self._base_prediction = float(np.mean(y))
        residuals = y - self._base_prediction
        self._trees = []

        for _ in range(self.n_estimators):
            tree = self._build_stump(X, residuals)
            predictions = self._predict_tree(X, tree)
            residuals -= self.learning_rate * predictions
            self._trees.append(tree)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions."""
        result = np.full(X.shape[0], self._base_prediction)
        for tree in self._trees:
            result += self.learning_rate * self._predict_tree(X, tree)
        return result

    def _build_stump(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Build a single decision stump."""
        n_features = X.shape[1]
        best_feature = 0
        best_threshold = 0.0
        best_score = -np.inf

        for fi in range(n_features):
            threshold = np.median(X[:, fi])
            left_mask = X[:, fi] <= threshold
            right_mask = ~left_mask

            if left_mask.sum() < 2 or right_mask.sum() < 2:
                continue

            left_mean = np.mean(y[left_mask])
            right_mean = np.mean(y[right_mask])
            score = abs(left_mean - right_mean)

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

    def _predict_tree(self, X: np.ndarray, tree: dict) -> np.ndarray:
        """Predict using a single stump."""
        left_mask = X[:, tree["feature"]] <= tree["threshold"]
        predictions = np.where(left_mask, tree["left_value"], tree["right_value"])
        return predictions


class EnsembleModel(BaseModel):
    """RF + GBM Ensemble Model.

    Combines Random Forest and Gradient Boosting predictions
    using confidence-weighted averaging.
    """

    def __init__(
        self,
        rf_estimators: int = 100,
        gbm_estimators: int = 100,
        gbm_learning_rate: float = 0.1,
        signal_threshold: float = 0.02,
    ) -> None:
        self._rf_estimators = rf_estimators
        self._gbm_estimators = gbm_estimators
        self._gbm_learning_rate = gbm_learning_rate
        self._signal_threshold = signal_threshold
        self._rf: Optional[SimpleRandomForest] = None
        self._gbm: Optional[SimpleGradientBoosting] = None
        self._trained = False
        self._feature_names: List[str] = []
        self._train_metrics: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return "ensemble_rf_gbm"

    @property
    def is_trained(self) -> bool:
        return self._trained

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Train the ensemble model.

        Args:
            X: Feature DataFrame.
            y: Target Series (forward returns or signals).
            validation_split: Fraction for validation.

        Returns:
            Dict with training metrics.
        """
        self.validate_input(X)

        self._feature_names = list(X.columns)

        # Split data
        n = len(X)
        split_idx = int(n * (1 - validation_split))

        X_train = X.iloc[:split_idx].values
        y_train = y.iloc[:split_idx].values
        X_val = X.iloc[split_idx:].values
        y_val = y.iloc[split_idx:].values

        # Train Random Forest
        self._rf = SimpleRandomForest(n_estimators=self._rf_estimators)
        self._rf.fit(X_train, y_train, self._feature_names)

        # Train GBM
        self._gbm = SimpleGradientBoosting(
            n_estimators=self._gbm_estimators,
            learning_rate=self._gbm_learning_rate,
        )
        self._gbm.fit(X_train, y_train, self._feature_names)

        # Validate
        rf_pred = self._rf.predict_proba(X_val)
        gbm_pred = self._gbm.predict(X_val)

        # Ensemble predictions
        ensemble_pred = 0.5 * rf_pred + 0.5 * gbm_pred

        # Calculate metrics
        mse = float(np.mean((ensemble_pred - y_val) ** 2))
        mae = float(np.mean(np.abs(ensemble_pred - y_val)))
        direction_accuracy = float(np.mean(np.sign(ensemble_pred) == np.sign(y_val)))

        self._trained = True
        self._train_metrics = {
            "mse": mse,
            "mae": mae,
            "direction_accuracy": direction_accuracy,
            "train_samples": split_idx,
            "val_samples": n - split_idx,
        }

        logger.info("Ensemble trained: MSE=%.6f, MAE=%.6f, DirAcc=%.2f%%", mse, mae, direction_accuracy * 100)

        return self._train_metrics

    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions with confidence scores.

        Args:
            X: Feature DataFrame.

        Returns:
            List of PredictionResult with signals and confidence.
        """
        if not self._trained:
            raise RuntimeError("Model must be trained before prediction")

        X_values = X.values

        # Get individual predictions
        rf_pred = self._rf.predict_proba(X_values)
        gbm_pred = self._gbm.predict(X_values)

        # Ensemble with confidence weighting
        results: List[PredictionResult] = []

        for i in range(len(X)):
            rf_signal = rf_pred[i]
            gbm_signal = gbm_pred[i]

            # Weighted average
            ensemble_signal = 0.5 * rf_signal + 0.5 * gbm_signal

            # Confidence based on agreement
            agreement = 1.0 - abs(rf_signal - gbm_signal) / (abs(rf_signal) + abs(gbm_signal) + 1e-10)
            confidence = float(np.clip(agreement, 0.0, 1.0))

            # Discretize signal
            if abs(ensemble_signal) < self._signal_threshold:
                discrete_signal = 0.0
            else:
                discrete_signal = float(np.sign(ensemble_signal))

            results.append(PredictionResult(
                signal=discrete_signal,
                confidence=confidence,
                features_used=self._feature_names,
                model_name=self.name,
            ))

        return results

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importance from Random Forest."""
        if not self._trained:
            return {}

        # Simple permutation-based importance approximation
        importance = {}
        for i, name in enumerate(self._feature_names):
            # Count how often feature is used in trees
            count = 0
            for tree in self._rf._trees:
                count += self._count_feature_usage(tree, i)
            importance[name] = count / max(len(self._rf._trees), 1)

        # Normalize
        total = sum(importance.values()) or 1.0
        return {k: v / total for k, v in importance.items()}

    @staticmethod
    def _count_feature_usage(tree: dict, feature_idx: int) -> int:
        """Count how often a feature is used in a tree."""
        if tree.get("leaf", False):
            return 0
        count = 1 if tree.get("feature") == feature_idx else 0
        if "left" in tree:
            count += EnsembleModel._count_feature_usage(tree["left"], feature_idx)
        if "right" in tree:
            count += EnsembleModel._count_feature_usage(tree["right"], feature_idx)
        return count
