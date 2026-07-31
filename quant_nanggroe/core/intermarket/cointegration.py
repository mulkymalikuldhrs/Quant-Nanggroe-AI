"""
QNA Cointegration & Pairs Framework (Rencana Fase 1.2).

Pure-Python implementation of:
- Engle-Granger cointegration test
- Mean-reverting spread construction
- Z-score entry/exit logic
- Ornstein-Uhlenbeck half-life estimation

Supported pair groups:
- GC1!/SI1!  (Gold / Silver futures)
- 6E1!/DXY   (EUR futures / Dollar Index)
- NQ1!/ES1!  (Nasdaq / S&P futures)
- BTC1!/ETH1!  (Crypto futures)
- ZB1!/ZN1!  (US Treasury futures)
"""

from __future__ import annotations

import dataclasses
import logging
import math
import random
import statistics
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
#  Data structures
# ------------------------------------------------------------------


@dataclass(frozen=True)
class PairGroup:
    """Canonical pair definition with an optional hedge-ratio override."""

    name: str
    asset_a: str
    asset_b: str
    default_beta: Optional[float] = None


DEFAULT_PAIR_GROUPS: Tuple[PairGroup, ...] = (
    PairGroup(name="GC1!/SI1!", asset_a="GC1!", asset_b="SI1!"),
    PairGroup(name="6E1!/DXY", asset_a="6E1!", asset_b="DXY"),
    PairGroup(name="NQ1!/ES1!", asset_a="NQ1!", asset_b="ES1!"),
    PairGroup(name="BTC1!/ETH1!", asset_a="BTC1!", asset_b="ETH1!"),
    PairGroup(name="ZB1!/ZN1!", asset_a="ZB1!", asset_b="ZN1!"),
)


@dataclass(frozen=True)
class EngleGrangerResult:
    """Result from the Engle-Granger cointegration test."""

    cointegrated: bool
    hedge_ratio: float
    p_value_category: str
    p_value: float
    residual_std: float
    spread: Tuple[float, ...]
    confidence: str


@dataclass(frozen=True)
class PairSignal:
    """Single entry/exit signal with confidence."""

    timestamp: int
    pair_name: str
    signal: str  # "long" | "short" | "exit" | "hold"
    z_score: float
    confidence: str
    half_life: Optional[float]


@dataclass(frozen=True)
class PairScores:
    """Aggregated pair analysis output."""

    pair_name: str
    cointegrated: bool
    hedge_ratio: float
    confidence: str
    half_life: Optional[float]
    current_z: float
    latest_signal: PairSignal


# ------------------------------------------------------------------
#  Core math helpers
# ------------------------------------------------------------------


def _as_float_list(prices: Sequence[float]) -> List[float]:
    """Normalize a price sequence, dropping non-positive and non-finite values."""
    out: List[float] = []
    for p in prices:
        if p is None or (isinstance(p, float) and math.isnan(p)):
            continue
        f = float(p)
        if math.isinf(f) or math.isnan(f) or f <= 0:
            continue
        out.append(f)
    return out


def _ols(
    x: Sequence[float],
    y: Sequence[float],
    add_constant: bool = True,
) -> Tuple[float, float]:
    """Ordinary Least Squares: y = a + b * x.

    Returns ``(intercept, slope)`` or ``(0, slope)`` when ``add_constant=False``.
    """
    if len(x) == 0 or len(y) == 0 or len(x) != len(y):
        raise ValueError("x and y must be the same non-empty length")

    mean_x = statistics.fmean(x)
    mean_y = statistics.fmean(y)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_xx = sum(xi * xi for xi in x)
    n = float(len(x))

    if add_constant:
        denom = n * sum_xx - sum_x * sum_x
        if denom == 0.0:
            return 0.0, 0.0
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = mean_y - slope * mean_x
        return intercept, slope

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0.0:
        return 0.0, 0.0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    return 0.0, slope


def _residuals(
    x: Sequence[float],
    y: Sequence[float],
    add_constant: bool = True,
) -> List[float]:
    a, b = _ols(x, y, add_constant=add_constant)
    return [yi - (a + b * xi) for xi, yi in zip(x, y)]


def _adf_test(spread: Sequence[float], max_lag: int = 1) -> Tuple[float, float]:
    """ADF-style unit-root test on underlying price series.

    Returns ``(t_stat, p_value)`` using categorical critical values.
    """
    prices = _as_float_list(spread)
    if len(prices) < max_lag + 10:
        return 0.0, 1.0

    lagged = prices[:-1]
    dy = [s2 - s1 for s1, s2 in zip(lagged, prices[1:])]
    residuals = _residuals(lagged, dy, add_constant=True)

    dof = len(residuals) - 1
    if dof <= 0:
        return 0.0, 1.0

    sse = sum(r * r for r in residuals) / dof
    mean_lag = statistics.fmean(lagged)
    ss_x = sum((xl - mean_lag) ** 2 for xl in lagged)
    if ss_x == 0.0:
        return 0.0, 1.0
    se_b = math.sqrt(sse / ss_x)
    if se_b == 0.0:
        return 0.0, 1.0
    _, slope = _ols(lagged, residuals, add_constant=False)
    t_stat = slope / se_b

    # No-trend critical values for a sample ~200-500.
    if t_stat < -3.43:
        p = 0.01
    elif t_stat < -2.86:
        p = 0.05
    elif t_stat < -2.57:
        p = 0.10
    else:
        p = 1.0
    return t_stat, p


def engle_granger_test(
    prices_a: Sequence[float],
    prices_b: Sequence[float],
    significance: float = 0.05,
) -> EngleGrangerResult:
    """Run Engle-Granger cointegration test.

    H0: unit root in residuals (not cointegrated).
    Reject H0 if p < significance.

    Returns ``EngleGrangerResult`` with categorical confidence:
    ``"high"`` (p < 0.01), ``"medium"`` (p < 0.05), ``"low"`` (p < 0.10), ``"none"``.
    """
    a = _as_float_list(prices_a)
    b = _as_float_list(prices_b)
    min_len = min(len(a), len(b))
    if min_len < 20:
        return EngleGrangerResult(
            cointegrated=False,
            hedge_ratio=0.0,
            p_value_category="none",
            p_value=1.0,
            residual_std=0.0,
            spread=(),
            confidence="none",
        )

    a = a[-min_len:]
    b = b[-min_len:]
    intercept, beta = _ols(b, a, add_constant=True)
    residuals = [ai - (intercept + beta * bi) for bi, ai in zip(b, a)]
    spread = tuple(residuals)
    _, p = _adf_test(spread)

    mean_spread = statistics.mean(spread)
    residual_std = math.sqrt(sum((r - mean_spread) ** 2 for r in spread) / (len(spread) - 1)) if len(spread) > 1 else 0.0
    cointegrated = p < significance

    confidence = (
        "high" if p < 0.01 else "medium" if p < 0.05 else "low" if p < 0.10 else "none"
    )
    p_cat = (
        "<0.01" if p < 0.01 else "<0.05" if p < 0.05 else "<0.10" if p < 0.10 else ">=0.10"
    )
    return EngleGrangerResult(
        cointegrated=cointegrated,
        hedge_ratio=beta,
        p_value_category=p_cat,
        p_value=p,
        residual_std=residual_std,
        spread=spread,
        confidence=confidence,
    )


def compute_spread(
    prices_a: Sequence[float],
    prices_b: Sequence[float],
    beta: float,
) -> Tuple[float, ...]:
    """Compute spread = price_a - beta * price_b."""
    a = _as_float_list(prices_a)
    b = _as_float_list(prices_b)
    min_len = min(len(a), len(b))
    a, b = a[-min_len:], b[-min_len:]
    return tuple(ai - beta * bi for ai, bi in zip(a, b))


def rolling_zscore(values: Sequence[float], window: int = 60) -> Tuple[float, ...]:
    """Rolling Z-score of *values* with given lookback window."""
    vals = list(values)
    out: List[float] = [0.0] * len(vals)
    for i in range(window - 1, len(vals)):
        window_vals = vals[i - window + 1 : i + 1]
        mu = statistics.mean(window_vals)
        try:
            sigma = statistics.pstdev(window_vals)
        except statistics.StatisticsError:
            sigma = 0.0
        if sigma > 1e-12:
            out[i] = (vals[i] - mu) / sigma
        else:
            out[i] = 0.0
    return tuple(out)


def estimate_half_life(spread: Sequence[float]) -> Optional[float]:
    """Estimate Ornstein-Uhlenbeck mean-reversion half-life.

    Model: «s_t = a + phi × s_{t-1}. If phi < 0, half-life = -ln(2) / phi.
    Returns ``None`` when the spread does not exhibit mean reversion.
    """
    s = _as_float_list(spread)
    if len(s) < 10:
        return None
    lagged = s[:-1]
    ds = [si - s0 for s0, si in zip(lagged, s[1:])]
    _, phi = _ols(lagged, ds, add_constant=True)
    # OU model: ds_t = a + phi * s_{t-1}. Mean reversion => phi < 0.
    # half-life = -ln(2) / phi, positive when phi is negative.
    # Reject near-zero phi (drift/no reversion) and super-slow reversion
    # (half-life beyond ~1000 bars is economically meaningless).
    if phi >= -1e-9:
        return None
    hl = -math.log(2.0) / phi
    if hl > 1000.0:
        return None
    return hl


def generate_pair_signals(
    prices_a: Sequence[float],
    prices_b: Sequence[float],
    beta: float,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    window: int = 60,
    confidence: str = "medium",
) -> List[PairSignal]:
    """Generate entry/exit signals based on Z-score thresholds.

    * ``z > entry_z``: short spread  → sell A relative to B
    * ``z < -entry_z``: long spread → buy A relative to B
    * ``|z| < exit_z``: exit current position
    """
    spread = compute_spread(prices_a, prices_b, beta)
    z = rolling_zscore(spread, window=window)
    min_len = min(len(spread), len(z))
    spread = spread[-min_len:]
    z = z[-min_len:]
    half_life = estimate_half_life(spread)

    signals: List[PairSignal] = []
    position = None  # "long" / "short"
    for idx in range(min_len):
        zz = z[idx]
        if position is None:
            if zz > entry_z:
                position = "short"
                sig = "short"
            elif zz < -entry_z:
                position = "long"
                sig = "long"
            else:
                sig = "hold"
        else:
            if position == "long" and zz > -exit_z:
                position = None
                sig = "exit"
            elif position == "short" and zz < exit_z:
                position = None
                sig = "exit"
            else:
                sig = "hold"
        signals.append(
            PairSignal(
                timestamp=idx,
                pair_name="",
                signal=sig,
                z_score=zz,
                confidence=confidence,
                half_life=half_life,
            )
        )
    return signals


def _default_price_fetcher(
    pair: PairGroup,
) -> Tuple[Tuple[float, ...], Tuple[float, ...], float]:
    """Fallback synthetic price generator when no external provider is wired."""
    rnd = random.Random(42)
    n = 500
    w = [0.0]
    for _ in range(n - 1):
        w.append(w[-1] + rnd.gauss(0, 1))
    if pair.asset_b == "DXY":
        a = [w[i] + rnd.gauss(0, 0.5) for i in range(n)]
        b = [-w[i] + 50 + rnd.gauss(0, 0.5) for i in range(n)]
        beta = 1.0
    elif pair.asset_b == "ETH1!":
        a = [w[i] + rnd.gauss(0, 1) for i in range(n)]
        b = [2.5 * w[i] + rnd.gauss(0, 1.5) for i in range(n)]
        beta = 0.4
    elif pair.asset_b == "SI1!":
        a = [w[i] + rnd.gauss(0, 0.8) for i in range(n)]
        b = [0.8 * w[i] + rnd.gauss(0, 0.9) for i in range(n)]
        beta = 1.25
    elif pair.asset_b == "ES1!":
        a = [w[i] + rnd.gauss(0, 0.9) for i in range(n)]
        b = [0.9 * w[i] + rnd.gauss(0, 0.9) for i in range(n)]
        beta = 1.1
    elif pair.asset_b == "ZN1!":
        a = [w[i] + rnd.gauss(0, 0.7) for i in range(n)]
        b = [0.85 * w[i] + rnd.gauss(0, 0.7) for i in range(n)]
        beta = 1.15
    else:
        a = [w[i] + rnd.gauss(0, 1) for i in range(n)]
        b = [w[i] + rnd.gauss(0, 1) for i in range(n)]
        beta = 1.0
    base = 100.0
    a = [base + ai for ai in a]
    b = [base + bi for bi in b]
    return tuple(a), tuple(b), beta


def run_pairs(
    pair_groups: Iterable[PairGroup] = DEFAULT_PAIR_GROUPS,
    data_provider: Optional[object] = None,
) -> List[PairScores]:
    """Run cointegration analysis and signal generation over pair groups."""
    results: List[PairScores] = []
    for pair in pair_groups:
        if data_provider is None:
            prices_a, prices_b, beta = _default_price_fetcher(pair)
        else:
            prices_a, prices_b, beta = data_provider(pair)
        eg = engle_granger_test(prices_a, prices_b)
        spread = compute_spread(prices_a, prices_b, eg.hedge_ratio)
        z = rolling_zscore(spread, window=60)
        signals = generate_pair_signals(
            prices_a,
            prices_b,
            eg.hedge_ratio,
            confidence=eg.confidence,
        )
        half = estimate_half_life(spread)
        latest = signals[-1] if signals else PairSignal(
            timestamp=0,
            pair_name=pair.name,
            signal="hold",
            z_score=0.0,
            confidence=eg.confidence,
            half_life=half,
        )
        latest = dataclasses.replace(latest, pair_name=pair.name)
        results.append(
            PairScores(
                pair_name=pair.name,
                cointegrated=eg.cointegrated,
                hedge_ratio=eg.hedge_ratio,
                confidence=eg.confidence,
                half_life=half,
                current_z=z[-1] if z else 0.0,
                latest_signal=latest,
            )
        )
    return results


__all__ = [
    "PairGroup",
    "DEFAULT_PAIR_GROUPS",
    "EngleGrangerResult",
    "PairSignal",
    "PairScores",
    "engle_granger_test",
    "compute_spread",
    "rolling_zscore",
    "estimate_half_life",
    "generate_pair_signals",
    "run_pairs",
]
