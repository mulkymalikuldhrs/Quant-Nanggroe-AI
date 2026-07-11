"""Base Model — Abstract interface for ML models.

Defines the train/predict interface that all ML models must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class PredictionResult:
    """Result from a model prediction.

    Attributes:
        signal: Trading signal (-1, 0, 1) or continuous score.
        confidence: Confidence score (0-1).
        probabilities: Optional class probabilities.
        features_used: List of features used in prediction.
        model_name: Name of the model that produced this prediction.
    """

    signal: float
    confidence: float
    probabilities: Optional[Dict[str, float]] = None
    features_used: List[str] = field(default_factory=list)
    model_name: str = ""


class BaseModel(ABC):
    """Abstract base class for all ML models.

    Every model must implement:
    - train(X, y): Train the model on features and labels
    - predict(X): Generate predictions from features
    - feature_importance(): Return feature importance scores
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name identifier."""
        ...

    @property
    @abstractmethod
    def is_trained(self) -> bool:
        """Whether the model has been trained."""
        ...

    @abstractmethod
    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        validation_split: float = 0.2,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Train the model.

        Args:
            X: Feature DataFrame.
            y: Target Series.
            validation_split: Fraction of data for validation.
            **kwargs: Additional training parameters.

        Returns:
            Dict with training metrics.
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
    def feature_importance(self) -> Dict[str, float]:
        """Return feature importance scores.

        Returns:
            Dict mapping feature name -> importance score.
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
