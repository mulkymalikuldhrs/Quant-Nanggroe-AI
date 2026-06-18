"""Base class for all trading strategies.

Provides the abstract interface and common utilities that every strategy
must implement. All concrete strategies extend BaseStrategy and implement
the generate_signal, required_columns, and warmup_period methods.

References:
    - De Prado, M. (2018). Advances in Financial Machine Learning. Wiley.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.types.signals import Signal, SignalType


class BaseStrategy(ABC):
    """Base class for all trading strategies.

    Every concrete strategy must:
    - Implement generate_signal() to produce trading signals
    - Implement required_columns() to declare OHLCV dependencies
    - Implement warmup_period() to specify minimum data length

    Attributes:
        name: Human-readable strategy name.
        params: Strategy-specific configuration parameters.
        is_warmed_up: Whether the strategy has received enough data.
    """

    def __init__(self, name: str, params: Optional[Dict] = None):
        """Initialize the base strategy.

        Args:
            name: Strategy name identifier.
            params: Optional dict of strategy parameters.
        """
        self.name = name
        self.params = params or {}
        self.is_warmed_up = False

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate a trading signal from market data.

        Args:
            data: DataFrame with OHLCV columns and DatetimeIndex.

        Returns:
            A Signal object if conditions are met, None otherwise.
        """
        ...

    @abstractmethod
    def required_columns(self) -> List[str]:
        """Return required OHLCV columns for this strategy.

        Returns:
            List of column names that must be present in the data.
        """
        ...

    @abstractmethod
    def warmup_period(self) -> int:
        """Return minimum number of bars needed before signal generation.

        Returns:
            Minimum number of observations required.
        """
        ...

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Validate that data has required columns and sufficient length.

        Args:
            data: Market data DataFrame.

        Returns:
            True if data is valid and strategy is warmed up.
        """
        if data is None or data.empty:
            return False

        required = self.required_columns()
        has_cols = all(c in data.columns for c in required)
        has_len = len(data) >= self.warmup_period()
        self.is_warmed_up = has_len

        if not has_cols:
            missing = [c for c in required if c not in data.columns]
            raise ValueError(
                f"Strategy '{self.name}' missing required columns: {missing}"
            )

        return has_cols and has_len

    @staticmethod
    def compute_sma(series: pd.Series, period: int) -> pd.Series:
        """Compute Simple Moving Average.

        Args:
            series: Price or indicator series.
            period: Lookback window.

        Returns:
            SMA series.
        """
        return series.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def compute_ema(series: pd.Series, period: int) -> pd.Series:
        """Compute Exponential Moving Average.

        Args:
            series: Price or indicator series.
            period: Span parameter.

        Returns:
            EMA series.
        """
        return series.ewm(span=period, adjust=False, min_periods=period).mean()

    @staticmethod
    def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Compute Relative Strength Index using Wilder's smoothing.

        Args:
            series: Price series.
            period: RSI lookback period (default 14).

        Returns:
            RSI values between 0 and 100.
        """
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean()
        avg_loss = loss.ewm(
            alpha=1.0 / period, min_periods=period, adjust=False
        ).mean()

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi

    @staticmethod
    def compute_atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Compute Average True Range.

        Args:
            high: High price series.
            low: Low price series.
            close: Close price series.
            period: ATR lookback period.

        Returns:
            ATR series.
        """
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def compute_bollinger_bands(
        series: pd.Series, period: int = 20, num_std: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Compute Bollinger Bands.

        Args:
            series: Price series.
            period: Moving average period.
            num_std: Number of standard deviations for bands.

        Returns:
            Tuple of (upper_band, middle_band, lower_band).
        """
        middle = series.rolling(window=period, min_periods=period).mean()
        std = series.rolling(window=period, min_periods=period).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return upper, middle, lower

    @staticmethod
    def compute_macd(
        series: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Compute MACD, signal line, and histogram.

        Args:
            series: Price series.
            fast_period: Fast EMA period.
            slow_period: Slow EMA period.
            signal_period: Signal line EMA period.

        Returns:
            Tuple of (macd_line, signal_line, histogram).
        """
        fast_ema = series.ewm(span=fast_period, adjust=False).mean()
        slow_ema = series.ewm(span=slow_period, adjust=False).mean()
        macd_line = fast_ema - slow_ema
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def compute_zscore(series: pd.Series, period: int) -> pd.Series:
        """Compute rolling Z-score.

        Args:
            series: Input series.
            period: Rolling window size.

        Returns:
            Z-score series.
        """
        rolling_mean = series.rolling(window=period, min_periods=period).mean()
        rolling_std = series.rolling(window=period, min_periods=period).std()
        return (series - rolling_mean) / (rolling_std + 1e-10)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', params={self.params})"
