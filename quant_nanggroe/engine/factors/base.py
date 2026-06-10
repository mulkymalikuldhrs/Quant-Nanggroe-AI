"""Alpha Factor base class and operators.

All operators act on **wide** ``pd.DataFrame`` where ``index = trading_date``
(DatetimeIndex) and ``columns = instrument_code`` (str). The factor compute
contract returns a pd.Series or pd.DataFrame of the same shape — raw scores,
NaN preserved in warmup / missing data; +/- inf is forbidden.

NaN policy: every operator propagates NaN; no silent ``fillna(0)``. A constant
window for ``ts_corr`` / ``ts_cov`` returns NaN, not zero.

Lookahead ban: ``delta(df, d)`` requires ``d >= 1``; the negative-shift
form is intentionally absent. All factors must pass lookahead-banned validation.

Reference: Kakushadze (2015), "101 Formulaic Alphas", arXiv:1601.00991
"""

from __future__ import annotations

import ast
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

import numpy as np
import pandas as pd


class Market(str, Enum):
    """Market identifier for market-specific formulas."""

    EQUITY_US = "equity_us"
    EQUITY_CN = "equity_cn"
    EQUITY_HK = "equity_hk"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


@dataclass(frozen=True, slots=True)
class FactorMeta:
    """Metadata for a registered alpha factor."""

    id: str
    zoo: str
    theme: List[str]
    formula_latex: str = ""
    columns_required: List[str] = field(default_factory=list)
    universe: List[str] = field(default_factory=list)
    frequency: List[str] = field(default_factory=lambda: ["1D"])
    decay_horizon: int = 0
    min_warmup_bars: int = 0
    notes: str = ""


class AlphaFactor(ABC):
    """Abstract base class for all alpha factors.

    Every factor must:
    - Inherit from AlphaFactor
    - Implement compute(df: pd.DataFrame) -> pd.Series
    - Be AST-pure (no external API calls, no randomness)
    - Have proper docstring with formula reference
    - Include lookahead-banned validation

    The compute method receives a DataFrame with OHLCV columns and returns
    a Series of factor values aligned with the input index.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this factor."""
        ...

    @property
    @abstractmethod
    def meta(self) -> FactorMeta:
        """Factor metadata."""
        ...

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute the factor values.

        Args:
            df: DataFrame with OHLCV data. Index is DatetimeIndex,
                columns include 'open', 'high', 'low', 'close', 'volume',
                and optionally 'vwap', 'amount'.

        Returns:
            pd.Series of factor values aligned with the input index.
            Must not contain +/- inf. NaN in warmup periods is expected.
        """
        ...

    def validate_lookahead(self) -> bool:
        """Validate that this factor has no lookahead bias.

        Scans the compute method's AST for negative shift operations
        or future-data access patterns.

        Returns:
            True if the factor is lookahead-free.
        """
        import textwrap

        source = inspect.getsource(self.compute)
        # Dedent to remove leading whitespace (class/method indentation)
        source = textwrap.dedent(source)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            # Check for negative shift (lookahead)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "shift":
                    for arg in node.args:
                        if isinstance(arg, ast.UnaryOp) and isinstance(arg.op, ast.USub):
                            return False
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, (int, float)) and arg.value < 0:
                            return False
        return True

    def validate_output(self, result: pd.Series) -> pd.Series:
        """Validate factor output quality.

        Ensures:
        - No +/- inf values
        - Not >95% NaN
        - Proper alignment with expected index

        Args:
            result: Factor output series.

        Returns:
            Validated series (inf replaced with NaN).

        Raises:
            ValueError: If output fails validation.
        """
        result = result.replace([np.inf, -np.inf], np.nan)

        nan_ratio = result.isna().mean()
        if nan_ratio > 0.95:
            raise ValueError(
                f"Factor {self.name}: output >95% NaN (ratio={nan_ratio:.3f})"
            )

        return result


# ─── Operator Functions ──────────────────────────────────────────────────────
# These are pure functions that operate on wide DataFrames (index=dates, columns=instruments).
# They are used by factor implementations to compose complex alpha formulas.


def _as_float(df: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Convert DataFrame or Series to float64 if needed."""
    if isinstance(df, pd.Series):
        if df.dtype == np.float64:
            return df
        return df.astype(np.float64)
    if df.dtypes.eq(np.float64).all():
        return df
    return df.astype(np.float64)


def rank(df: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Cross-sectional percentile rank per row (axis=1, ties=average, pct=True).

    NaN inputs stay NaN. An all-NaN row returns an all-NaN row.
    Accepts both DataFrame and Series inputs.
    """
    if isinstance(df, pd.Series):
        return df.rank(method="average", pct=True, na_option="keep")
    return df.rank(axis=1, method="average", pct=True, na_option="keep")


def scale(df: pd.DataFrame, a: float = 1.0) -> pd.DataFrame:
    """Per-row L1 normalize so sum of absolute values equals ``a``.

    Rows whose abs-sum is 0 (or all-NaN) become NaN — never silent zero.
    """
    df = _as_float(df)
    abs_sum = df.abs().sum(axis=1, skipna=True)
    abs_sum = abs_sum.where(abs_sum > 0)
    return df.mul(a).div(abs_sum, axis=0)


def ts_rank(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling rank (last value's rank within the n-window), per column.

    Warmup (first ``n-1`` rows per column) returns NaN. Result is a percentile
    in [0, 1] so it is compositionally compatible with cross-sectional rank.
    """
    if n < 1:
        raise ValueError(f"ts_rank window must be >= 1, got {n}")

    def _last_rank(arr: np.ndarray) -> float:
        if np.isnan(arr).all():
            return np.nan
        last = arr[-1]
        if np.isnan(last):
            return np.nan
        valid = arr[~np.isnan(arr)]
        if valid.size == 0:
            return np.nan
        less = (valid < last).sum()
        eq = (valid == last).sum()
        rank_avg = less + 0.5 * (eq + 1)
        return float(rank_avg / valid.size)

    return df.rolling(window=n, min_periods=n).apply(_last_rank, raw=True)


def ts_corr(x: pd.DataFrame | pd.Series, y: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling Pearson correlation per column, min_periods=n.

    Constant series in the window → NaN (no silent zero).
    Accepts both DataFrame and Series inputs. When both inputs are Series,
    computes a single rolling correlation time-series.
    """
    if n < 2:
        raise ValueError(f"ts_corr window must be >= 2, got {n}")

    # Series × Series case: compute single rolling correlation
    if isinstance(x, pd.Series) and isinstance(y, pd.Series):
        x = _as_float(x)
        y = _as_float(y)
        # Use pandas rolling corr between two Series
        result = x.rolling(window=n, min_periods=n).corr(y)
        return result.replace([np.inf, -np.inf], np.nan)

    # DataFrame × DataFrame case: align columns
    x = _as_float(x)
    y = _as_float(y)

    # If columns don't overlap, rename to a common column for element-wise corr
    if isinstance(x, pd.DataFrame) and isinstance(y, pd.DataFrame):
        if not x.columns.equals(y.columns):
            # Rename both to same column name for proper alignment
            common_col = "_corr_col"
            x_renamed = x.rename(columns={x.columns[0]: common_col})
            y_renamed = y.rename(columns={y.columns[0]: common_col})
            if common_col in x_renamed.columns and common_col in y_renamed.columns:
                xa = x_renamed[[common_col]]
                ya = y_renamed[[common_col]]
                corr = xa.rolling(window=n, min_periods=n).corr(ya)
                # Rename back
                corr = corr.rename(columns={common_col: x.columns[0]})
                return corr.replace([np.inf, -np.inf], np.nan)

        cols = x.columns.union(y.columns)
        xa = x.reindex(columns=cols)
        ya = y.reindex(columns=cols)
        corr = xa.rolling(window=n, min_periods=n).corr(ya)
        return corr.replace([np.inf, -np.inf], np.nan)

    return pd.DataFrame()


def ts_cov(x: pd.DataFrame | pd.Series, y: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling sample covariance per column, min_periods=n.

    Accepts both DataFrame and Series inputs. When both inputs are Series,
    computes a single rolling covariance time-series.
    """
    if n < 2:
        raise ValueError(f"ts_cov window must be >= 2, got {n}")

    # Series × Series case
    if isinstance(x, pd.Series) and isinstance(y, pd.Series):
        x = _as_float(x)
        y = _as_float(y)
        result = x.rolling(window=n, min_periods=n).cov(y)
        return result.replace([np.inf, -np.inf], np.nan)

    # DataFrame × DataFrame case
    x = _as_float(x)
    y = _as_float(y)

    if isinstance(x, pd.DataFrame) and isinstance(y, pd.DataFrame):
        if not x.columns.equals(y.columns):
            common_col = "_cov_col"
            x_renamed = x.rename(columns={x.columns[0]: common_col})
            y_renamed = y.rename(columns={y.columns[0]: common_col})
            if common_col in x_renamed.columns and common_col in y_renamed.columns:
                xa = x_renamed[[common_col]]
                ya = y_renamed[[common_col]]
                cov = xa.rolling(window=n, min_periods=n).cov(ya)
                cov = cov.rename(columns={common_col: x.columns[0]})
                return cov.replace([np.inf, -np.inf], np.nan)

        cols = x.columns.union(y.columns)
        xa = x.reindex(columns=cols)
        ya = y.reindex(columns=cols)
        cov = xa.rolling(window=n, min_periods=n).cov(ya)
        return cov.replace([np.inf, -np.inf], np.nan)

    return pd.DataFrame()


def ts_mean(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling mean per column, warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_mean window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).mean()


def ts_std(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling sample std (ddof=1) per column, warmup → NaN."""
    if n < 2:
        raise ValueError(f"ts_std window must be >= 2, got {n}")
    return df.rolling(window=n, min_periods=n).std(ddof=1)


def ts_max(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling max per column, warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_max window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).max()


def ts_min(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling min per column, warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_min window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).min()


def _argmax_last(arr: np.ndarray) -> float:
    if np.isnan(arr).all():
        return np.nan
    arr_filled = np.where(np.isnan(arr), -np.inf, arr)
    return float(np.argmax(arr_filled))


def _argmin_last(arr: np.ndarray) -> float:
    if np.isnan(arr).all():
        return np.nan
    arr_filled = np.where(np.isnan(arr), np.inf, arr)
    return float(np.argmin(arr_filled))


def ts_argmax(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling argmax (0-based index into the window), warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_argmax window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).apply(_argmax_last, raw=True)


def ts_argmin(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling argmin (0-based index into the window), warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_argmin window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).apply(_argmin_last, raw=True)


def delta(df: pd.DataFrame | pd.Series, d: int) -> pd.DataFrame | pd.Series:
    """First difference at lag ``d``: ``df - df.shift(d)``.

    Lookahead ban: ``d >= 1`` strictly. Negative lag forbidden.
    """
    if d < 1:
        raise ValueError(f"delta lag must be >= 1 (lookahead ban), got {d}")
    return df - df.shift(d)


def decay_linear(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Linear decay-weighted moving average, weights ``n, n-1, ..., 1`` normalized.

    Warmup (first ``n-1`` rows) → NaN.
    """
    if n < 1:
        raise ValueError(f"decay_linear window must be >= 1, got {n}")
    weights = np.arange(n, 0, -1, dtype=np.float64)
    weights /= weights.sum()

    def _apply(arr: np.ndarray) -> float:
        if np.isnan(arr).any():
            return np.nan
        return float(np.dot(arr, weights))

    return df.rolling(window=n, min_periods=n).apply(_apply, raw=True)


def signed_power(df: pd.DataFrame | pd.Series, p: float) -> pd.DataFrame | pd.Series:
    """``sign(df) * |df|**p`` — preserves sign; never produces complex output.

    Accepts both DataFrame and Series inputs, returning the same type.
    """
    arr = np.asarray(df, dtype=np.float64)
    out = np.sign(arr) * np.power(np.abs(arr), p)
    if isinstance(df, pd.Series):
        return pd.Series(out, index=df.index, name=df.name)
    return pd.DataFrame(out, index=df.index, columns=df.columns)


def ts_sum(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling sum per column, warmup → NaN.

    Equivalent to the WorldQuant ``ts_sum(x, d)`` operator.
    """
    if n < 1:
        raise ValueError(f"ts_sum window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).sum()


def ts_product(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling product per column, warmup → NaN.

    Used for multiplicative return aggregation in alpha formulas.
    """
    if n < 1:
        raise ValueError(f"ts_product window must be >= 1, got {n}")

    def _prod(arr: np.ndarray) -> float:
        if np.isnan(arr).any():
            return np.nan
        return float(np.prod(arr))

    return df.rolling(window=n, min_periods=n).apply(_prod, raw=True)


def ts_median(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling median per column, warmup → NaN.

    Robust central-tendency estimator, less sensitive to outliers than ts_mean.
    """
    if n < 1:
        raise ValueError(f"ts_median window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).median()


def ts_skewness(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling skewness per column, warmup → NaN.

    Measures asymmetry of the return distribution.
    """
    if n < 3:
        raise ValueError(f"ts_skewness window must be >= 3, got {n}")
    return df.rolling(window=n, min_periods=n).skew()


def ts_kurtosis(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling excess kurtosis per column, warmup → NaN.

    Measures tail heaviness of the return distribution.
    """
    if n < 4:
        raise ValueError(f"ts_kurtosis window must be >= 4, got {n}")
    return df.rolling(window=n, min_periods=n).kurt()


def delay(df: pd.DataFrame | pd.Series, d: int) -> pd.DataFrame | pd.Series:
    """Lag operator: ``df.shift(d)``.

    Lookahead ban: ``d >= 1`` strictly. Equivalent to WorldQuant ``delay(x, d)``.
    """
    if d < 1:
        raise ValueError(f"delay lag must be >= 1 (lookahead ban), got {d}")
    return df.shift(d)


def safe_div(
    a: pd.DataFrame | pd.Series,
    b: pd.DataFrame | pd.Series | float | int,
    eps: float = 1e-12,
) -> pd.DataFrame | pd.Series:
    """Safe division: ``a / (b + eps * sign(b))``.

    Where ``b == 0`` exactly (or NaN), result is NaN — never silently inf or 0.
    Accepts both DataFrame and Series inputs.
    """
    if isinstance(b, (int, float)):
        denom = b if abs(b) > eps else np.nan
        result = a / denom
        if isinstance(result, pd.Series):
            return result.replace([np.inf, -np.inf], np.nan)
        return result.replace([np.inf, -np.inf], np.nan)

    if isinstance(a, pd.Series) or isinstance(b, pd.Series):
        b_safe = b.replace(0, np.nan) if isinstance(b, (pd.Series, pd.DataFrame)) else b
        result = a / b_safe
        return result.replace([np.inf, -np.inf], np.nan)

    a = _as_float(a)
    b = _as_float(b)
    sign = np.sign(b.to_numpy(dtype=np.float64, na_value=np.nan))
    denom_arr = b.to_numpy(dtype=np.float64, na_value=np.nan) + eps * sign
    denom = pd.DataFrame(denom_arr, index=b.index, columns=b.columns)
    result = a.div(denom)
    return result.replace([np.inf, -np.inf], np.nan)


def ts_sum(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling sum per column, warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_sum window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).sum()


def ts_product(df: pd.DataFrame | pd.Series, n: int) -> pd.DataFrame | pd.Series:
    """Rolling product per column, warmup → NaN."""
    if n < 1:
        raise ValueError(f"ts_product window must be >= 1, got {n}")
    return df.rolling(window=n, min_periods=n).apply(np.prod, raw=True)


def cross_sectional_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows → NaN.

    This is a cross-sectional operator (operates across columns per row),
    useful for creating long-short rankings of factor values.
    """
    mean = df.mean(axis=1, skipna=True)
    std = df.std(axis=1, ddof=1, skipna=True)
    centered = df.sub(mean, axis=0)
    result = centered.div(std.where(std > 0), axis=0)
    return result.replace([np.inf, -np.inf], np.nan)


def vwap(panel: Dict[str, pd.DataFrame], market: Market = Market.EQUITY_US) -> pd.DataFrame:
    """Market-aware VWAP-equivalent reference price.

    - ``equity_cn``: ``(amount * 1000) / (volume * 100 + 1)``
    - ``equity_us`` / ``equity_hk`` / ``futures``: typical price ``(H + L + C + O) / 4``
    - ``crypto``: prefer ``panel["vwap"]`` if provided, else typical price.
    """
    if isinstance(market, str):
        market = Market(market)

    if "vwap" in panel:
        return panel["vwap"]

    if market == Market.EQUITY_CN:
        if "amount" not in panel or "volume" not in panel:
            raise KeyError("vwap(equity_cn) requires panel['amount'] and panel['volume']")
        return safe_div(panel["amount"] * 1000.0, panel["volume"] * 100.0 + 1.0)

    required = ("open", "high", "low", "close")
    missing = [k for k in required if k not in panel]
    if missing:
        raise KeyError(f"vwap({market.value}) requires panel keys {required}; missing {missing}")
    return (panel["open"] + panel["high"] + panel["low"] + panel["close"]) / 4.0
