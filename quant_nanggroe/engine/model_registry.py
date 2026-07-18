"""Model Registry — Qlib-Inspired Model Registration Pattern.

Implements a model registry pattern inspired by Qlib's model management
system.  Provides a central registry for quant models with:

* ``register_model(name, cls)`` decorator for auto-registration
* ``get_model(name)`` resolver for model lookup
* ``list_models()`` for discovering available models
* Base ``QuantModel`` ABC with fit(), predict(), explain()

Registered Models
-----------------
* ``linear``: LinearModel — linear regression baseline
* ``xgboost``: XGBoostModel — gradient boosted trees
* ``transformer``: TransformerModel — attention-based model

Usage::

    from quant_nanggroe.engine.model_registry import (
        register_model, get_model, list_models, QuantModel
    )

    # Get a registered model
    model = get_model("linear")
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    importance = model.explain()

    # Register a custom model
    @register_model("my_model", MyModelClass)
    class MyModelClass(QuantModel):
        ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


# ── Registry Storage ────────────────────────────────────────────────────

MODEL_REGISTRY: Dict[str, Type["QuantModel"]] = {}


# ── Pydantic Models ─────────────────────────────────────────────────────


class PredictionResult(BaseModel):
    """Result from a model prediction.

    Attributes:
        signal: Trading signal (-1, 0, 1) or continuous score.
        confidence: Confidence score (0.0–1.0).
        probabilities: Optional class probabilities.
        features_used: Features used in the prediction.
        model_name: Name of the model that produced this prediction.
    """

    model_config = ConfigDict(frozen=False)

    signal: float = 0.0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    probabilities: Dict[str, float] = Field(default_factory=dict)
    features_used: List[str] = Field(default_factory=list)
    model_name: str = ""


class ModelInfo(BaseModel):
    """Information about a registered model.

    Attributes:
        name: Model name in the registry.
        class_name: Name of the model class.
        description: Model description.
        is_trained: Whether an instance has been trained.
        created_at: Registration timestamp.
    """

    model_config = ConfigDict(frozen=False)

    name: str = ""
    class_name: str = ""
    description: str = ""
    is_trained: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ── Base Quant Model ABC ────────────────────────────────────────────────


class QuantModel(ABC):
    """Abstract base class for all quantitative models.

    Every registered model must implement:
    * ``fit(X, y)``: Train the model on features and labels
    * ``predict(X)``: Generate predictions from features
    * ``explain()``: Return feature importance / explanation

    Attributes:
        name: Model name identifier.
        is_trained: Whether the model has been trained.
        params: Model hyperparameters.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.is_trained: bool = False
        self.params: Dict[str, Any] = kwargs
        self._feature_names: List[str] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name identifier."""
        ...

    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Train the model.

        Args:
            X: Feature DataFrame.
            y: Target Series.
            **kwargs: Additional training parameters.

        Returns:
            Dictionary with training metrics.
        """
        ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions from features.

        Args:
            X: Feature DataFrame.

        Returns:
            List of PredictionResult objects.
        """
        ...

    @abstractmethod
    def explain(self) -> Dict[str, float]:
        """Return feature importance scores or model explanation.

        Returns:
            Dictionary mapping feature name → importance score.
        """
        ...

    def validate_input(self, X: pd.DataFrame) -> None:
        """Validate input features.

        Args:
            X: Feature DataFrame.

        Raises:
            ValueError: If input is invalid.
        """
        if X.empty:
            raise ValueError("Input DataFrame is empty")
        if X.isna().all().all():
            raise ValueError("Input DataFrame contains only NaN values")

    @property
    def feature_names(self) -> List[str]:
        """Get feature names from training data."""
        return self._feature_names

    @property
    def info(self) -> ModelInfo:
        """Get model information."""
        return ModelInfo(
            name=self.name,
            class_name=self.__class__.__name__,
            description=self.__doc__ or "",
            is_trained=self.is_trained,
        )


# ── Registration Functions ──────────────────────────────────────────────


def register_model(
    name: str,
    cls: Optional[Type[QuantModel]] = None,
) -> Callable:
    """Register a model class in the model registry.

    Can be used as a decorator or called directly:

    As decorator::

        @register_model("my_model")
        class MyModel(QuantModel):
            ...

    Direct call::

        register_model("my_model", MyModelClass)

    Args:
        name: Name to register the model under.
        cls: Model class to register (for direct call).

    Returns:
        The model class (for decorator usage) or a decorator.
    """
    def decorator(model_cls: Type[QuantModel]) -> Type[QuantModel]:
        if name in MODEL_REGISTRY:
            logger.warning(
                "model_registry_overwrite",
                extra={"name": name, "old": MODEL_REGISTRY[name].__name__},
            )
        MODEL_REGISTRY[name] = model_cls
        logger.info(
            "model_registered",
            extra={"name": name, "class": model_cls.__name__},
        )
        return model_cls

    if cls is not None:
        return decorator(cls)
    return decorator


def get_model(name: str, **kwargs: Any) -> QuantModel:
    """Get a model instance by name.

    Args:
        name: Registered model name.
        **kwargs: Arguments to pass to the model constructor.

    Returns:
        Instance of the registered model.

    Raises:
        KeyError: If the model name is not registered.
    """
    if name not in MODEL_REGISTRY:
        available = list(MODEL_REGISTRY.keys())
        raise KeyError(
            f"Model '{name}' not found in registry. "
            f"Available models: {available}"
        )
    return MODEL_REGISTRY[name](**kwargs)


def list_models() -> List[ModelInfo]:
    """List all registered models.

    Returns:
        List of ModelInfo objects for each registered model.
    """
    infos: List[ModelInfo] = []
    for name, cls in MODEL_REGISTRY.items():
        # Create a temporary instance to get info
        try:
            instance = cls()
            infos.append(instance.info)
        except Exception:
            infos.append(
                ModelInfo(
                    name=name,
                    class_name=cls.__name__,
                    description=cls.__doc__ or "",
                )
            )
    return infos


def has_model(name: str) -> bool:
    """Check if a model is registered.

    Args:
        name: Model name.

    Returns:
        True if the model is registered.
    """
    return name in MODEL_REGISTRY


def unregister_model(name: str) -> bool:
    """Remove a model from the registry.

    Args:
        name: Model name.

    Returns:
        True if the model was found and removed.
    """
    if name in MODEL_REGISTRY:
        del MODEL_REGISTRY[name]
        return True
    return False


# ── Built-in Model Implementations ──────────────────────────────────────


@register_model("linear")
class LinearModel(QuantModel):
    """Linear regression baseline model.

    Simple OLS regression for baseline predictions.  Uses numpy
    for computation — no sklearn dependency required.

    Attributes:
        weights: Learned feature weights.
        intercept: Learned intercept term.
    """

    def __init__(self, fit_intercept: bool = True, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.fit_intercept = fit_intercept
        self.weights: Optional[np.ndarray] = None
        self.intercept: float = 0.0

    @property
    def name(self) -> str:
        return "linear"

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fit linear regression using OLS (numpy).

        Args:
            X: Feature DataFrame.
            y: Target Series.

        Returns:
            Training metrics dictionary.
        """
        self.validate_input(X)
        self._feature_names = list(X.columns)

        X_arr = X.values.astype(float)
        y_arr = y.values.astype(float)

        # Add intercept column if needed
        if self.fit_intercept:
            X_arr = np.column_stack([np.ones(len(X_arr)), X_arr])

        # OLS: w = (X^T X)^{-1} X^T y
        try:
            w = np.linalg.lstsq(X_arr, y_arr, rcond=None)[0]
        except np.linalg.LinAlgError:
            # Fallback: use pseudoinverse
            w = np.linalg.pinv(X_arr) @ y_arr

        if self.fit_intercept:
            self.intercept = float(w[0])
            self.weights = w[1:]
        else:
            self.intercept = 0.0
            self.weights = w

        self.is_trained = True

        # Compute R² score
        y_pred = X_arr @ w
        ss_res = np.sum((y_arr - y_pred) ** 2)
        ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return {
            "r_squared": round(float(r_squared), 4),
            "n_features": len(self._feature_names),
            "n_samples": len(X),
            "intercept": round(self.intercept, 6),
        }

    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions.

        Args:
            X: Feature DataFrame.

        Returns:
            List of PredictionResult objects.
        """
        if not self.is_trained or self.weights is None:
            raise RuntimeError("Model must be fitted before prediction")

        self.validate_input(X)
        X_arr = X.values.astype(float)

        raw = X_arr @ self.weights + self.intercept

        results: List[PredictionResult] = []
        for val in raw:
            # Convert to signal: positive → 1, negative → -1
            signal = float(np.sign(val))
            confidence = min(1.0, abs(val) / (np.std(raw) + 1e-8))

            results.append(
                PredictionResult(
                    signal=signal,
                    confidence=round(float(confidence), 4),
                    features_used=self._feature_names,
                    model_name=self.name,
                )
            )

        return results

    def explain(self) -> Dict[str, float]:
        """Return feature importance as absolute weight magnitudes.

        Returns:
            Dictionary mapping feature name → importance score.
        """
        if not self.is_trained or self.weights is None:
            return {}

        abs_weights = np.abs(self.weights)
        total = np.sum(abs_weights)

        if total == 0:
            return {name: 0.0 for name in self._feature_names}

        return {
            name: round(float(w / total), 6)
            for name, w in zip(self._feature_names, abs_weights)
        }


@register_model("xgboost")
class XGBoostModel(QuantModel):
    """Gradient boosted trees model (XGBoost stub with proper interface).

    Uses xgboost if available, otherwise falls back to a simple
    decision-stump-based approximation for demonstration.

    Attributes:
        n_estimators: Number of boosting rounds.
        max_depth: Maximum tree depth.
        learning_rate: Boosting learning rate.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self._model: Any = None
        self._feature_importances: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "xgboost"

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fit the XGBoost model.

        Args:
            X: Feature DataFrame.
            y: Target Series.

        Returns:
            Training metrics dictionary.
        """
        self.validate_input(X)
        self._feature_names = list(X.columns)

        try:
            import xgboost as xgb

            dtrain = xgb.DMatrix(X.values, label=y.values, feature_names=self._feature_names)
            self._model = xgb.train(
                {
                    "max_depth": self.max_depth,
                    "eta": self.learning_rate,
                    "objective": "reg:squarederror",
                    "eval_metric": "rmse",
                },
                dtrain,
                num_boost_round=self.n_estimators,
            )

            # Get feature importance
            importance = self._model.get_score(importance_type="gain")
            total_gain = sum(importance.values()) if importance else 1.0
            self._feature_importances = {
                name: round(gain / total_gain, 6)
                for name, gain in importance.items()
            }

        except ImportError:
            # Fallback: simple approximation using feature correlation
            logger.info("xgboost_not_available_using_fallback")
            self._model = self._fit_simple_fallback(X, y)

        self.is_trained = True

        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "n_features": len(self._feature_names),
            "n_samples": len(X),
            "method": "xgboost" if self._model is not None else "simple_fallback",
        }

    def _fit_simple_fallback(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, Any]:
        """Simple fallback when xgboost is not available.

        Uses feature correlation with target as a proxy for importance.
        """
        correlations = {}
        for col in X.columns:
            corr = np.corrcoef(X[col].values, y.values)[0, 1]
            correlations[col] = abs(corr) if not np.isnan(corr) else 0.0

        total_corr = sum(correlations.values()) or 1.0
        self._feature_importances = {
            name: round(corr / total_corr, 6)
            for name, corr in correlations.items()
        }

        # Store for prediction
        mean_val = float(np.mean(y.values))
        return {
            "type": "simple_fallback",
            "correlations": correlations,
            "mean_target": mean_val,
        }

    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions.

        Args:
            X: Feature DataFrame.

        Returns:
            List of PredictionResult objects.
        """
        if not self.is_trained:
            raise RuntimeError("Model must be fitted before prediction")

        self.validate_input(X)

        results: List[PredictionResult] = []

        try:
            import xgboost as xgb

            if hasattr(self._model, "predict"):
                dtest = xgb.DMatrix(X.values, feature_names=self._feature_names)
                raw = self._model.predict(dtest)

                for val in raw:
                    signal = float(np.sign(val))
                    confidence = min(1.0, abs(val))
                    results.append(
                        PredictionResult(
                            signal=signal,
                            confidence=round(float(confidence), 4),
                            features_used=self._feature_names,
                            model_name=self.name,
                        )
                    )
                return results

        except ImportError:
            pass

        # Fallback prediction
        mean_target = self._model.get("mean_target", 0.0)
        for _ in range(len(X)):
            results.append(
                PredictionResult(
                    signal=float(np.sign(mean_target)),
                    confidence=0.3,
                    features_used=self._feature_names,
                    model_name=self.name,
                )
            )

        return results

    def explain(self) -> Dict[str, float]:
        """Return feature importance from XGBoost gain scores.

        Returns:
            Dictionary mapping feature name → importance score.
        """
        return self._feature_importances


@register_model("transformer")
class TransformerModel(QuantModel):
    """TransformerModel — NOT FOR PRODUCTION.

    This is a simplified feedforward stub, not a real transformer.
    Uses 2-layer MLP as placeholder. Do not use for live trading.
    """

    def __init__(
        self,
        d_model: int = 64,
        n_heads: int = 4,
        n_layers: int = 2,
        dropout: float = 0.1,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.dropout = dropout
        self._inner_model: Any = None
        self._attention_weights: Dict[str, float] = {}

    @property
    def name(self) -> str:
        return "transformer"

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Fit the transformer model.

        Args:
            X: Feature DataFrame.
            y: Target Series.

        Returns:
            Training metrics dictionary.
        """
        self.validate_input(X)
        self._feature_names = list(X.columns)

        try:
            import torch
            import torch.nn as nn

            self._inner_model = self._build_torch_model(len(self._feature_names))
            self._fit_torch(X, y)

        except ImportError:
            logger.info("pytorch_not_available_using_fallback")
            self._inner_model = self._fit_simple_fallback(X, y)

        self.is_trained = True

        return {
            "d_model": self.d_model,
            "n_heads": self.n_heads,
            "n_layers": self.n_layers,
            "n_features": len(self._feature_names),
            "n_samples": len(X),
            "method": "transformer" if hasattr(self._inner_model, "forward") else "simple_fallback",
        }

    def _build_torch_model(self, n_features: int) -> Any:
        """Build a simple PyTorch model (stub).

        In production, this would be a full Transformer architecture.
        """
        import torch.nn as nn

        class SimpleTransformerStub(nn.Module):
            """Simplified transformer stub for demonstration."""

            def __init__(self, n_in: int, d: int) -> None:
                super().__init__()
                self.fc1 = nn.Linear(n_in, d)
                self.fc2 = nn.Linear(d, 1)
                self.relu = nn.ReLU()

            def forward(self, x: Any) -> Any:
                return self.fc2(self.relu(self.fc1(x)))

        return SimpleTransformerStub(n_features, self.d_model)

    def _fit_torch(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the PyTorch model (simplified).

        In production, this would use proper training with
        validation, early stopping, learning rate scheduling, etc.
        """
        import torch
        import torch.nn as nn

        X_tensor = torch.FloatTensor(X.values)
        y_tensor = torch.FloatTensor(y.values).unsqueeze(1)

        optimizer = torch.optim.Adam(self._inner_model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        for epoch in range(50):
            self._inner_model.train()
            optimizer.zero_grad()
            output = self._inner_model(X_tensor)
            loss = criterion(output, y_tensor)
            loss.backward()
            optimizer.step()

        # Extract attention-like weights from first layer
        with torch.no_grad():
            w = self._inner_model.fc1.weight.abs().mean(dim=0)
            total = w.sum()
            if total > 0:
                self._attention_weights = {
                    name: round(float(w[i] / total), 6)
                    for i, name in enumerate(self._feature_names)
                }

    def _fit_simple_fallback(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, Any]:
        """Simple fallback when PyTorch is not available."""
        # Use variance-weighted features as a proxy for attention
        var_weights = {}
        for col in X.columns:
            corr = np.corrcoef(X[col].values, y.values)[0, 1]
            var = float(np.var(X[col].values))
            var_weights[col] = abs(corr) * var if not np.isnan(corr) else 0.0

        total = sum(var_weights.values()) or 1.0
        self._attention_weights = {
            name: round(w / total, 6)
            for name, w in var_weights.items()
        }

        mean_val = float(np.mean(y.values))
        return {"type": "simple_fallback", "mean_target": mean_val}

    def predict(self, X: pd.DataFrame) -> List[PredictionResult]:
        """Generate predictions.

        Args:
            X: Feature DataFrame.

        Returns:
            List of PredictionResult objects.
        """
        if not self.is_trained:
            raise RuntimeError("Model must be fitted before prediction")

        self.validate_input(X)

        results: List[PredictionResult] = []

        try:
            import torch

            if hasattr(self._inner_model, "forward"):
                self._inner_model.eval()
                with torch.no_grad():
                    X_tensor = torch.FloatTensor(X.values)
                    raw = self._inner_model(X_tensor).squeeze().numpy()

                for val in raw:
                    signal = float(np.sign(val))
                    confidence = min(1.0, abs(float(val)))
                    results.append(
                        PredictionResult(
                            signal=signal,
                            confidence=round(confidence, 4),
                            features_used=self._feature_names,
                            model_name=self.name,
                        )
                    )
                return results

        except ImportError:
            pass

        # Fallback
        mean_target = 0.0
        if isinstance(self._inner_model, dict):
            mean_target = self._inner_model.get("mean_target", 0.0)

        for _ in range(len(X)):
            results.append(
                PredictionResult(
                    signal=float(np.sign(mean_target)),
                    confidence=0.3,
                    features_used=self._feature_names,
                    model_name=self.name,
                )
            )

        return results

    def explain(self) -> Dict[str, float]:
        """Return attention-like feature importance weights.

        Returns:
            Dictionary mapping feature name → attention weight.
        """
        return self._attention_weights


# ═══════════════════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Model Registry Demo")
    print("=" * 60)

    # List all registered models
    print("\n--- Registered Models ---")
    for info in list_models():
        print(f"  {info.name}: {info.class_name} — {info.description[:60]}")

    # Generate synthetic data
    np.random.seed(42)
    n = 200
    X = pd.DataFrame({
        "momentum": np.random.normal(0, 1, n),
        "volatility": np.random.normal(0, 1, n),
        "volume": np.random.normal(0, 1, n),
        "rsi": np.random.normal(50, 10, n),
    })
    y = pd.Series(
        0.5 * X["momentum"]
        - 0.3 * X["volatility"]
        + 0.2 * X["rsi"]
        + np.random.normal(0, 0.1, n),
        name="returns",
    )

    X_train, X_test = X[:150], X[150:]
    y_train, y_test = y[:150], y[150:]

    # Test each model
    for model_name in ["linear", "xgboost", "transformer"]:
        print(f"\n--- Testing: {model_name} ---")

        model = get_model(model_name)
        metrics = model.fit(X_train, y_train)
        print(f"  Fit metrics: {metrics}")

        predictions = model.predict(X_test)
        print(f"  Predictions: {len(predictions)} results")
        if predictions:
            print(f"  First pred: signal={predictions[0].signal}, conf={predictions[0].confidence:.3f}")

        importance = model.explain()
        print(f"  Feature importance:")
        for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
            print(f"    {feat}: {imp:.4f}")

    # Test registry operations
    print(f"\n--- Registry Operations ---")
    print(f"  Has 'linear': {has_model('linear')}")
    print(f"  Has 'unknown': {has_model('unknown')}")
    print(f"  Unregister 'linear': {unregister_model('linear')}")
    print(f"  Has 'linear' after unregister: {has_model('linear')}")

    # Re-register
    register_model("linear", LinearModel)
    print(f"  Has 'linear' after re-register: {has_model('linear')}")

    # Test error handling
    try:
        get_model("nonexistent")
    except KeyError as e:
        print(f"  Expected error: {e}")
