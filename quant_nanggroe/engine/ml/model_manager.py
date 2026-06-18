"""Model Manager — Model registration, versioning, training, and inference.

Manages the lifecycle of ML models:
- Model registration and versioning
- Training pipeline
- Inference pipeline
- Model health monitoring
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model lifecycle status."""

    REGISTERED = "registered"
    TRAINING = "training"
    TRAINED = "trained"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class ModelInfo(BaseModel):
    """Model registration info."""

    name: str = Field(..., min_length=1)
    version: str = Field(default="1.0.0")
    status: ModelStatus = Field(default=ModelStatus.REGISTERED)
    created_at: float = Field(default_factory=time.time)
    trained_at: Optional[float] = None
    training_duration_sec: Optional[float] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    feature_count: int = 0
    sample_count: int = 0

    model_config = {"from_attributes": True}


@dataclass
class TrainingResult:
    """Result from model training."""

    model_name: str
    success: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    training_duration_sec: float = 0.0
    feature_importance: Dict[str, float] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class InferenceResult:
    """Result from model inference."""

    model_name: str
    predictions: np.ndarray = field(default_factory=lambda: np.array([]))
    confidence: float = 0.0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class ModelManager:
    """Model Manager for ML models.

    Features:
    - Model registration with versioning
    - Training pipeline with metrics
    - Inference pipeline with latency tracking
    - Model health monitoring
    - Model persistence (save/load)
    """

    def __init__(self) -> None:
        self._models: Dict[str, Any] = {}
        self._model_info: Dict[str, ModelInfo] = {}
        self._training_history: List[TrainingResult] = []
        self._health_checks: Dict[str, Dict[str, Any]] = {}

    def register_model(self, name: str, model: Any, version: str = "1.0.0") -> ModelInfo:
        """Register a model.

        Args:
            name: Unique model name.
            model: Model object (must have train/predict methods).
            version: Model version string.

        Returns:
            ModelInfo for the registered model.
        """
        if name in self._models:
            logger.warning("Model %s already registered, overwriting", name)

        self._models[name] = model
        info = ModelInfo(name=name, version=version, status=ModelStatus.REGISTERED)
        self._model_info[name] = info

        logger.info("Registered model: %s v%s", name, version)
        return info

    def train_model(
        self,
        name: str,
        X: pd.DataFrame,
        y: pd.Series,
        **kwargs: Any,
    ) -> TrainingResult:
        """Train a registered model.

        Args:
            name: Model name.
            X: Feature DataFrame.
            y: Target Series.

        Returns:
            TrainingResult with metrics.
        """
        if name not in self._models:
            return TrainingResult(
                model_name=name,
                success=False,
                error=f"Model {name} not registered",
            )

        model = self._models[name]
        info = self._model_info[name]
        info.status = ModelStatus.TRAINING

        start_time = time.time()
        try:
            # Train the model
            if hasattr(model, "train"):
                train_metrics = model.train(X, y, **kwargs)
            elif hasattr(model, "fit"):
                model.fit(X, y)
                train_metrics = {}
            else:
                raise ValueError(f"Model {name} has no train/fit method")

            duration = time.time() - start_time

            # Update model info
            info.status = ModelStatus.TRAINED
            info.trained_at = time.time()
            info.training_duration_sec = duration
            info.feature_count = len(X.columns)
            info.sample_count = len(X)
            info.metrics = train_metrics if isinstance(train_metrics, dict) else {}

            # Get feature importance if available
            feature_importance = {}
            if hasattr(model, "feature_importance"):
                feature_importance = model.feature_importance()

            result = TrainingResult(
                model_name=name,
                success=True,
                metrics=info.metrics,
                training_duration_sec=duration,
                feature_importance=feature_importance,
            )

            logger.info("Model %s trained in %.2fs", name, duration)

        except Exception as exc:
            duration = time.time() - start_time
            info.status = ModelStatus.FAILED

            result = TrainingResult(
                model_name=name,
                success=False,
                training_duration_sec=duration,
                error=str(exc),
            )

            logger.error("Model %s training failed: %s", name, exc)

        self._training_history.append(result)
        return result

    def predict(
        self,
        name: str,
        X: pd.DataFrame,
    ) -> InferenceResult:
        """Run inference with a trained model.

        Args:
            name: Model name.
            X: Feature DataFrame.

        Returns:
            InferenceResult with predictions.
        """
        if name not in self._models:
            return InferenceResult(
                model_name=name,
                error=f"Model {name} not registered",
            )

        model = self._models[name]
        info = self._model_info[name]

        if info.status != ModelStatus.TRAINED:
            return InferenceResult(
                model_name=name,
                error=f"Model {name} not trained (status: {info.status})",
            )

        start_time = time.time()
        try:
            if hasattr(model, "predict"):
                predictions = model.predict(X)
                if isinstance(predictions, list):
                    predictions = np.array([p.signal if hasattr(p, "signal") else p for p in predictions])
                elif isinstance(predictions, pd.DataFrame):
                    predictions = predictions.values.flatten()
            else:
                raise ValueError(f"Model {name} has no predict method")

            latency = (time.time() - start_time) * 1000  # ms

            # Compute average confidence
            confidence = 0.5
            if hasattr(predictions, "__len__") and len(predictions) > 0:
                confidence = min(1.0, float(np.mean(np.abs(predictions))))

            return InferenceResult(
                model_name=name,
                predictions=predictions,
                confidence=confidence,
                latency_ms=latency,
            )

        except Exception as exc:
            return InferenceResult(
                model_name=name,
                error=str(exc),
            )

    def get_model_info(self, name: str) -> Optional[ModelInfo]:
        """Get model information."""
        return self._model_info.get(name)

    def list_models(self) -> List[str]:
        """List all registered model names."""
        return sorted(self._models.keys())

    def list_trained_models(self) -> List[str]:
        """List all trained model names."""
        return [
            name for name, info in self._model_info.items()
            if info.status == ModelStatus.TRAINED
        ]

    def health_check(self, name: str) -> Dict[str, Any]:
        """Check model health.

        Returns a health report including:
        - Model status
        - Last training time
        - Feature count
        - Sample count
        - Metrics
        """
        info = self._model_info.get(name)
        if info is None:
            return {"status": "not_found", "model": name}

        health = {
            "model": name,
            "status": info.status.value,
            "version": info.version,
            "trained_at": info.trained_at,
            "training_duration_sec": info.training_duration_sec,
            "feature_count": info.feature_count,
            "sample_count": info.sample_count,
            "metrics": info.metrics,
            "healthy": info.status == ModelStatus.TRAINED,
        }

        self._health_checks[name] = health
        return health

    def deprecate_model(self, name: str) -> bool:
        """Mark a model as deprecated."""
        info = self._model_info.get(name)
        if info is None:
            return False
        info.status = ModelStatus.DEPRECATED
        return True

    def get_training_history(self) -> List[TrainingResult]:
        """Get training history for all models."""
        return self._training_history
