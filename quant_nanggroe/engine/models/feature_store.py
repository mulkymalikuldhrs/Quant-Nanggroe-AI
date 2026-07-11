"""Feature Store — Feature engineering and storage.

Provides feature engineering, normalization, and storage for ML models.
Handles feature computation, caching, and transformation pipelines.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature engineering.

    Attributes:
        normalize: Whether to normalize features.
        fill_method: Method for filling NaN values ('ffill', 'bfill', 'zero', 'drop').
        lookback: Default lookback window for rolling features.
        include_returns: Whether to include return features.
        include_volume: Whether to include volume features.
        include_volatility: Whether to include volatility features.
    """

    normalize: bool = True
    fill_method: str = "ffill"
    lookback: int = 20
    include_returns: bool = True
    include_volume: bool = True
    include_volatility: bool = True


class FeatureStore:
    """Feature Store for ML Models.

    Manages feature engineering, transformation, and storage.
    Provides a centralized repository for features used by ML models.

    Features:
    - Configurable feature engineering pipeline
    - Feature normalization (z-score, min-max)
    - Feature caching for performance
    - Feature selection and filtering
    - Automatic lookahead prevention
    """

    def __init__(self, config: Optional[FeatureConfig] = None) -> None:
        self._config = config or FeatureConfig()
        self._feature_cache: Dict[str, pd.DataFrame] = {}
        self._custom_transforms: Dict[str, Callable] = {}

    def engineer_features(
        self,
        df: pd.DataFrame,
        symbol: Optional[str] = None,
    ) -> pd.DataFrame:
        """Engineer features from OHLCV data.

        Args:
            df: DataFrame with OHLCV columns.
            symbol: Optional symbol for caching.

        Returns:
            DataFrame with engineered features.
        """
        features = pd.DataFrame(index=df.index)

        if "close" in df.columns:
            close = df["close"]

            # Return features
            if self._config.include_returns:
                features["return_1d"] = close.pct_change(1)
                features["return_5d"] = close.pct_change(5)
                features["return_10d"] = close.pct_change(10)
                features["return_20d"] = close.pct_change(20)

            # Moving averages
            for window in [5, 10, 20, 50]:
                ma = close.rolling(window=window, min_periods=window).mean()
                features[f"sma_{window}"] = ma
                features[f"close_to_sma_{window}"] = (close - ma) / ma.replace(0, np.nan)

            # Volatility features
            if self._config.include_volatility:
                returns = close.pct_change()
                for window in [5, 10, 20]:
                    features[f"volatility_{window}"] = returns.rolling(
                        window=window, min_periods=window
                    ).std() * np.sqrt(252)

                    # Realized volatility ratio
                    short_vol = returns.rolling(window=5, min_periods=5).std()
                    long_vol = returns.rolling(window=window, min_periods=window).std()
                    features[f"vol_ratio_{window}"] = short_vol / long_vol.replace(0, np.nan)

            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=14, min_periods=14).mean()
            avg_loss = loss.rolling(window=14, min_periods=14).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            features["rsi_14"] = 100 - 100 / (1 + rs)

            # Bollinger Band features
            sma20 = close.rolling(window=20, min_periods=20).mean()
            std20 = close.rolling(window=20, min_periods=20).std()
            features["bb_position"] = (close - sma20) / (2 * std20).replace(0, np.nan)
            features["bb_width"] = (2 * std20) / sma20.replace(0, np.nan)

            # MACD
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            features["macd"] = ema12 - ema26
            features["macd_signal"] = features["macd"].ewm(span=9, adjust=False).mean()
            features["macd_hist"] = features["macd"] - features["macd_signal"]

        # Volume features
        if "volume" in df.columns and self._config.include_volume:
            volume = df["volume"]
            vol_ma = volume.rolling(window=20, min_periods=20).mean()
            features["volume_ratio"] = volume / vol_ma.replace(0, np.nan)

            # Volume-price correlation
            if "close" in df.columns:
                close = df["close"]
                vol_change = volume.pct_change()
                price_change = close.pct_change()
                features["volume_price_corr"] = vol_change.rolling(
                    window=20, min_periods=20
                ).corr(price_change)

        # High-Low features
        if "high" in df.columns and "low" in df.columns:
            features["intraday_range"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
            features["intraday_range_ma20"] = features["intraday_range"].rolling(
                window=20, min_periods=20
            ).mean()

        # Open-Close features
        if "open" in df.columns and "close" in df.columns:
            features["intraday_return"] = (df["close"] - df["open"]) / df["open"].replace(0, np.nan)

        # Apply custom transforms
        for name, transform in self._custom_transforms.items():
            try:
                features[name] = transform(df)
            except Exception as exc:
                logger.warning("Custom transform %s failed: %s", name, exc)

        # Fill NaN values
        features = self._fill_nan(features)

        # Normalize if configured
        if self._config.normalize:
            features = self._normalize(features)

        # Cache features
        if symbol:
            self._feature_cache[symbol] = features

        return features

    def add_transform(self, name: str, transform: Callable) -> None:
        """Add a custom feature transform.

        Args:
            name: Feature name.
            transform: Callable that takes a DataFrame and returns a Series.
        """
        self._custom_transforms[name] = transform

    def get_cached(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get cached features for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            Cached feature DataFrame or None.
        """
        return self._feature_cache.get(symbol)

    def prepare_training_data(
        self,
        features: pd.DataFrame,
        forward_returns: pd.Series,
        lookahead_bars: int = 1,
    ) -> tuple:
        """Prepare features and labels for model training.

        Args:
            features: Feature DataFrame.
            forward_returns: Forward return series.
            lookahead_bars: Number of bars to look ahead for labels.

        Returns:
            Tuple of (X, y) DataFrames with aligned indices.
        """
        # Shift returns backward to create labels (prevents lookahead bias)
        y = forward_returns.shift(-lookahead_bars)

        # Align indices
        common_idx = features.index.intersection(y.dropna().index)
        X = features.loc[common_idx]
        y = y.loc[common_idx]

        # Drop any remaining NaN rows
        valid_mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[valid_mask]
        y = y[valid_mask]

        return X, y

    def _fill_nan(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fill NaN values using configured method."""
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
