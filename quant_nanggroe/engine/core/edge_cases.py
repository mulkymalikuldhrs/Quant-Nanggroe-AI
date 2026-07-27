"""
Edge Case Handling — QNA modules
Defensive wrappers, input validation, and graceful degradation
for all QNA quant modules.
"""
import logging
from typing import Any, Dict, List, Optional, TypeVar

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DataFrameValidator:
    """Validates and sanitizes DataFrame inputs"""

    @staticmethod
    def validate_price_data(df: pd.DataFrame, required_cols: Optional[List[str]] = None) -> pd.DataFrame:
        if df is None or df.empty:
            raise ValueError("Empty DataFrame")

        if required_cols:
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                raise ValueError(f"Missing columns: {missing}")

        df = df.copy()
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        return df

    @staticmethod
    def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                raise ValueError(f"Cannot convert index to datetime: {e}")
        return df

    @staticmethod
    def handle_missing(df: pd.DataFrame, method: str = "ffill", 
                         max_gap: int = 5) -> pd.DataFrame:
        if method == "ffill":
            df = df.ffill(limit=max_gap)
        elif method == "bfill":
            df = df.bfill(limit=max_gap)
        elif method == "interpolate":
            df = df.interpolate(limit=max_gap)
        elif method == "drop":
            df = df.dropna()
        return df

    @staticmethod
    def validate_returns(returns: pd.Series) -> pd.Series:
        if returns is None or len(returns) < 2:
            raise ValueError("Need at least 2 return observations")

        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
        # Clip extreme values (beyond 10 std)
        std = returns.std()
        if std > 0:
            returns = returns.clip(-10 * std, 10 * std)
        return returns

    @staticmethod
    def validate_weights(weights: Dict[str, float]) -> Dict[str, float]:
        if not weights:
            raise ValueError("Empty weights dict")

        total = sum(weights.values())
        if total <= 0:
            raise ValueError("Weights sum must be positive")

        # Normalize to 1.0
        return {k: v / total for k, v in weights.items()}


class SafeCalculator:
    """Safe mathematical operations with fallback"""

    @staticmethod
    def safe_divide(a: float, b: float, default: float = 0.0) -> float:
        try:
            return a / b if abs(b) > 1e-15 else default
        except (ZeroDivisionError, TypeError, ValueError):
            return default

    @staticmethod
    def safe_log(x: float, default: float = 0.0) -> float:
        try:
            if x <= 0:
                return default
            return np.log(x)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_sqrt(x: float, default: float = 0.0) -> float:
        try:
            if x < 0:
                return default
            return np.sqrt(x)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_mean(values: List[float], default: float = 0.0) -> float:
        if not values:
            return default
        try:
            return float(np.mean([v for v in values if v is not None]))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_std(values: List[float], default: float = 0.0) -> float:
        if len(values) < 2:
            return default
        try:
            return float(np.std([v for v in values if v is not None]))
        except (ValueError, TypeError):
            return default


class EmptyResult:
    """Null result object for empty/edge case returns"""
    def __init__(self, data_type: str = "unknown"):
        self.data_type = data_type
        self.empty = True
        self.error = "No data available"

    def to_dict(self) -> Dict[str, Any]:
        return {"empty": True, "data_type": self.data_type, "error": self.error}


# Edge case test data generators
class EdgeCaseData:
    @staticmethod
    def empty_series() -> pd.Series:
        return pd.Series([], dtype=float)

    @staticmethod
    def constant_series(value: float = 100.0, n: int = 100) -> pd.Series:
        return pd.Series([value] * n)

    @staticmethod
    def single_value_series(value: float = 100.0) -> pd.Series:
        return pd.Series([value])

    @staticmethod
    def NaN_series(n: int = 100) -> pd.Series:
        return pd.Series([np.nan] * n)

    @staticmethod
    def inf_series(n: int = 100) -> pd.Series:
        return pd.Series([np.inf] * n)

    @staticmethod
    def mixed_nan_series(n: int = 100, nan_ratio: float = 0.3) -> pd.Series:
        data = np.random.randn(n)
        mask = np.random.random(n) < nan_ratio
        data[mask] = np.nan
        return pd.Series(data)

    @staticmethod
    def extreme_values(n: int = 100) -> pd.Series:
        data = np.random.randn(n) * 0.02
        data[0] = 100.0  # extreme outlier
        data[-1] = -100.0
        return pd.Series(data)
