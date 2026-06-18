"""Feature Engineer — Feature engineering from factor library.

Creates technical, fundamental, sentiment, and macro features
for ML models with feature selection and importance analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureCategory(str, Enum):
    """Feature categories."""

    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    VOLUME = "volume"
    STATISTICAL = "statistical"


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""

    include_technical: bool = True
    include_fundamental: bool = False
    include_sentiment: bool = False
    include_macro: bool = False
    include_volume: bool = True
    include_statistical: bool = True
    normalize: bool = True
    fill_method: str = "ffill"
    lookback_periods: Tuple[int, ...] = (5, 10, 20, 50)


class FeatureEngineer:
    """Feature Engineer for ML models.

    Creates comprehensive feature sets from OHLCV data and optional
    fundamental/sentiment/macro data sources.

    Features:
    - Technical features from factor library
    - Fundamental features
    - Sentiment features
    - Macro features
    - Feature selection and importance
    - Custom transform pipeline
    """

    def __init__(self, config: Optional[FeatureConfig] = None) -> None:
        self._config = config or FeatureConfig()
        self._custom_transforms: Dict[str, Callable] = {}
        self._feature_importance: Dict[str, float] = {}

    def engineer_features(
        self,
        df: pd.DataFrame,
        fundamental_data: Optional[Dict[str, Any]] = None,
        sentiment_data: Optional[Dict[str, Any]] = None,
        macro_data: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Engineer features from OHLCV data and optional sources.

        Args:
            df: DataFrame with OHLCV columns.
            fundamental_data: Optional fundamental data dict.
            sentiment_data: Optional sentiment data dict.
            macro_data: Optional macro data dict.

        Returns:
            DataFrame with engineered features.
        """
        features = pd.DataFrame(index=df.index)

        if self._config.include_technical and "close" in df.columns:
            features = self._add_technical_features(features, df)

        if self._config.include_volume and "volume" in df.columns:
            features = self._add_volume_features(features, df)

        if self._config.include_statistical and "close" in df.columns:
            features = self._add_statistical_features(features, df)

        if self._config.include_fundamental and fundamental_data:
            features = self._add_fundamental_features(features, fundamental_data)

        if self._config.include_sentiment and sentiment_data:
            features = self._add_sentiment_features(features, sentiment_data)

        if self._config.include_macro and macro_data:
            features = self._add_macro_features(features, macro_data)

        # Apply custom transforms
        for name, transform in self._custom_transforms.items():
            try:
                features[name] = transform(df)
            except Exception as exc:
                logger.warning("Custom transform %s failed: %s", name, exc)

        # Fill NaN
        features = self._fill_nan(features)

        # Normalize
        if self._config.normalize:
            features = self._normalize(features)

        return features

    def add_transform(self, name: str, transform: Callable) -> None:
        """Add a custom feature transform."""
        self._custom_transforms[name] = transform

    def select_features(
        self,
        features: pd.DataFrame,
        target: Optional[pd.Series] = None,
        top_k: int = 50,
        method: str = "variance",
    ) -> pd.DataFrame:
        """Select top features by importance.

        Args:
            features: Feature DataFrame.
            target: Optional target series for correlation-based selection.
            top_k: Number of features to select.
            method: 'variance', 'correlation', or 'importance'.

        Returns:
            DataFrame with selected features.
        """
        if method == "variance":
            variances = features.var()
            top_features = variances.nlargest(min(top_k, len(variances))).index.tolist()
            return features[top_features]

        elif method == "correlation" and target is not None:
            correlations = features.corrwith(target).abs()
            top_features = correlations.nlargest(min(top_k, len(correlations))).index.tolist()
            return features[top_features]

        elif method == "importance" and self._feature_importance:
            sorted_features = sorted(
                self._feature_importance.items(), key=lambda x: x[1], reverse=True
            )
            top_features = [f[0] for f in sorted_features[:top_k] if f[0] in features.columns]
            if top_features:
                return features[top_features]
            return features

        return features

    def set_feature_importance(self, importance: Dict[str, float]) -> None:
        """Set feature importance scores (from model training)."""
        self._feature_importance = importance

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        return self._feature_importance

    def create_target(
        self,
        df: pd.DataFrame,
        forward_periods: int = 5,
        threshold: float = 0.02,
    ) -> pd.Series:
        """Create target variable for classification.

        Args:
            df: DataFrame with close prices.
            forward_periods: Number of periods to predict ahead.
            threshold: Threshold for BUY/SELL classification.

        Returns:
            Target series (1=BUY, 0=HOLD, -1=SELL).
        """
        future_return = df["close"].shift(-forward_periods) / df["close"] - 1

        target = pd.cut(
            future_return,
            bins=[-np.inf, -threshold, threshold, np.inf],
            labels=[-1, 0, 1],
        )
        target = pd.to_numeric(target, errors="coerce")
        target.name = "target"
        return target

    # ── Private Methods ─────────────────────────────────────────────────

    def _add_technical_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features."""
        close = df["close"]

        # Returns
        for period in self._config.lookback_periods:
            features[f"return_{period}d"] = close.pct_change(period)

        # Moving averages
        for period in self._config.lookback_periods:
            sma = close.rolling(window=period, min_periods=period).mean()
            features[f"sma_{period}"] = sma
            features[f"close_to_sma_{period}"] = (close - sma) / sma.replace(0, np.nan)

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        features["rsi_14"] = 100 - 100 / (1 + rs)

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        features["macd"] = ema12 - ema26
        features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
        features["macd_hist"] = features["macd"] - features["macd_signal"]

        # Bollinger Bands
        sma20 = close.rolling(window=20, min_periods=20).mean()
        std20 = close.rolling(window=20, min_periods=20).std()
        features["bb_position"] = (close - sma20) / (2 * std20).replace(0, np.nan)
        features["bb_width"] = (2 * std20) / sma20.replace(0, np.nan)

        return features

    def _add_volume_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        volume = df["volume"]
        close = df["close"]

        # Volume ratio
        vol_ma = volume.rolling(window=20, min_periods=20).mean()
        features["volume_ratio"] = volume / vol_ma.replace(0, np.nan)

        # OBV
        features["obv"] = (np.sign(close.diff()) * volume).cumsum()
        features["obv_ma"] = features["obv"].rolling(window=20, min_periods=20).mean()

        # Volume-price correlation
        features["volume_price_corr"] = close.rolling(window=20, min_periods=20).corr(volume)

        return features

    def _add_statistical_features(self, features: pd.DataFrame, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features."""
        close = df["close"]

        for period in [10, 20, 50]:
            if len(close) >= period:
                returns = close.pct_change().rolling(window=period, min_periods=period)
                features[f"skew_{period}d"] = returns.skew()
                features[f"kurtosis_{period}d"] = returns.kurt()
                features[f"volatility_{period}d"] = returns.std() * np.sqrt(252)

        # Rolling z-score
        for period in [20, 50]:
            mean = close.rolling(window=period, min_periods=period).mean()
            std = close.rolling(window=period, min_periods=period).std()
            features[f"zscore_{period}"] = (close - mean) / std.replace(0, np.nan)

        # Momentum
        for period in [5, 10, 20]:
            features[f"momentum_{period}"] = close / close.shift(period) - 1

        return features

    def _add_fundamental_features(
        self, features: pd.DataFrame, fundamental_data: Dict[str, Any]
    ) -> pd.DataFrame:
        """Add fundamental features."""
        for key, value in fundamental_data.items():
            if isinstance(value, (int, float)):
                features[f"fundamental_{key}"] = value
        return features

    def _add_sentiment_features(
        self, features: pd.DataFrame, sentiment_data: Dict[str, Any]
    ) -> pd.DataFrame:
        """Add sentiment features."""
        for key, value in sentiment_data.items():
            if isinstance(value, (int, float)):
                features[f"sentiment_{key}"] = value
        return features

    def _add_macro_features(
        self, features: pd.DataFrame, macro_data: Dict[str, Any]
    ) -> pd.DataFrame:
        """Add macro features."""
        for key, value in macro_data.items():
            if isinstance(value, (int, float)):
                features[f"macro_{key}"] = value
        return features

    def _fill_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill NaN values."""
        method = self._config.fill_method
        if method == "ffill":
            return df.ffill().fillna(0.0)
        elif method == "bfill":
            return df.bfill().fillna(0.0)
        elif method == "zero":
            return df.fillna(0.0)
        elif method == "drop":
            return df.dropna()
        return df.ffill().fillna(0.0)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """Z-score normalize features."""
        means = df.mean()
        stds = df.std().replace(0, 1.0)
        return (df - means) / stds
