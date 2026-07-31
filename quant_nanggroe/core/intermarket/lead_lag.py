"""
QNA Intermarket — Dynamic Lead-Lag Matrix (Fase 1.1).

Provides time-shifted cross-correlation across 34 futures/spot series.
Computes lead-lag relationships over multiple rolling windows and lags.

Usage:
    from quant_nanggroe.core.intermarket.lead_lag import (
        LeadLagResult,
        measure_lead_lag,
        build_lead_lag_matrix,
        SERIES,
    )

    result = measure_lead_lag("GC1", "XAUUSD", max_lag=20)
    matrix = build_lead_lag_matrix(windows=(30, 60, 120))
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  Universe
# ══════════════════════════════════════════════════════════════════════

# Internal QNA label -> Yahoo Finance ticker.
SERIES: Dict[str, str] = {
    # Futures
    "GC1": "GC=F",
    "SI1": "SI=F",
    "6E1": "6E=F",
    "6B1": "6B=F",
    "6J1": "6J=F",
    "6A1": "6A=F",
    "6C1": "6C=F",
    "6S1": "6S=F",
    "ES1": "ES=F",
    "NQ1": "NQ=F",
    "YM1": "YM=F",
    "ZB1": "ZB=F",
    "ZN1": "ZN=F",
    "DXY": "DX-Y.NYB",
    "BTC1": "BTC=F",
    "ETH1": "ETH=F",
    "VIX1": "^VIX",
    # Spot / Cash equivalents
    "XAUUSD": "XAUUSD=X",
    "XAGUSD": "XAGUSD=X",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "US500": "^GSPC",
    "NAS100": "^NDX",
    "US30": "^DJI",
    "BTCUSD": "BTC-USD",
    "ETHUSD": "ETH-USD",
}

DEFAULT_WINDOWS: Tuple[int, int, int] = (30, 60, 120)
DEFAULT_MAX_LAG: int = 20


# ══════════════════════════════════════════════════════════════════════
#  Data structures
# ══════════════════════════════════════════════════════════════════════

@dataclass
class LeadLagResult:
    """Result of a single lead-lag measurement for one window.

    Attributes:
        lead_asset: Symbol of the leading asset.
        lag_asset: Symbol of the lagging asset.
        lag: Number of periods the leader leads by. Negative means the
             caller-supplied ``asset_a`` leads.
        confidence: Normalized confidence in [0.0, 1.0].
        window: Rolling window size used for this measurement.
        best_lag_corr: Raw cross-correlation at the chosen lag.
    """

    lead_asset: str
    lag_asset: str
    lag: int = 0
    confidence: float = 0.0
    window: int = 0
    best_lag_corr: float = 0.0


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════

def _as_series(prices: Union[str, pd.Series, np.ndarray]) -> Optional[pd.Series]:
    """Normalize input into a clean price Series."""
    if isinstance(prices, str):
        return _fetch_prices(prices)
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)
    if isinstance(prices, pd.Series):
        out = prices.astype(float).dropna()
        out = out[out > 0]
        return out if len(out) > 5 else None
    return None


def _fetch_prices(symbol: str, lookback_days: int = 540) -> Optional[pd.Series]:
    """Download daily close prices via yfinance."""
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover - optional dep
        logger.debug("yfinance is unavailable: %s", exc)
        return None
    ticker = symbol
    if symbol in SERIES:
        ticker = SERIES[symbol]
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
    except Exception as exc:  # pragma: no cover
        logger.debug("yfinance history failed for %s (%s): %s", symbol, ticker, exc)
        return None
    if hist is None or hist.empty or "Close" not in hist.columns:
        return None
    s = hist["Close"].rename(symbol).dropna()
    s = s[s > 0]
    if len(s) < 30:
        return None
    return s.iloc[-lookback_days:] if lookback_days and lookback_days < len(s) else s


def _pearson_lagged(
    a: np.ndarray,
    b: np.ndarray,
    max_lag: int,
) -> Tuple[int, float]:
    """Return (lag, |pearson|) maximizing absolute correlation.

    Positive lag means B leads A (B shifted forward relative to A).
    Negative lag means A leads B.
    """
    ra = np.diff(np.log(np.maximum(a, 1e-12)))
    rb = np.diff(np.log(np.maximum(b, 1e-12)))
    n = min(len(ra), len(rb))
    ra, rb = ra[-n:], rb[-n:]
    if n < max_lag + 5:
        return 0, 0.0

    best_lag = 0
    best_abs_corr = 0.0
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            x = ra
            y = rb
        elif lag > 0:
            x = ra[lag:]
            y = rb[:-lag]
        else:
            x = ra[:lag]
            y = rb[-lag:]
        m = min(len(x), len(y))
        if m < 5:
            continue
        xm, ym = x[-m:], y[-m:]
        if np.std(xm) == 0 or np.std(ym) == 0:
            continue
        corr = float(np.corrcoef(xm, ym)[0, 1])
        if math.isnan(corr):
            continue
        if abs(corr) > best_abs_corr:
            best_abs_corr = abs(corr)
            best_lag = lag

    return best_lag, best_abs_corr


def _windowed_score(
    a: np.ndarray,
    b: np.ndarray,
    lead_asset_a: str,
    lag_asset_a: str,
    lead_asset_b: str,
    lag_asset_b: str,
    window: int,
    max_lag: int,
) -> LeadLagResult:
    """Measure lead-lag on the last *window* candles."""
    n = min(len(a), len(b))
    aw = a[-window:] if window <= n else a
    bw = b[-window:] if window <= n else b
    lag, corr = _pearson_lagged(aw, bw, max_lag)
    if lag > 0:
        lead, lag_name, direction_lag = lead_asset_b, lag_asset_a, lag
    elif lag < 0:
        lead, lag_name, direction_lag = lead_asset_a, lag_asset_b, -lag
    else:
        lead, lag_name, direction_lag = lead_asset_a, lag_asset_b, 0
    confidence = min(corr, 1.0)
    return LeadLagResult(
        lead_asset=lead,
        lag_asset=lag_name,
        lag=direction_lag,
        confidence=confidence,
        window=window,
        best_lag_corr=corr,
    )


# ══════════════════════════════════════════════════════════════════════
#  Public API
# ══════════════════════════════════════════════════════════════════════

def _labels(asset_a, asset_b):
    a_label = getattr(asset_a, 'name', None) or str(asset_a if not isinstance(asset_a, np.ndarray) else 'asset_a')
    b_label = getattr(asset_b, 'name', None) or str(asset_b if not isinstance(asset_b, np.ndarray) else 'asset_b')
    return a_label, b_label


def measure_lead_lag(
    asset_a: Union[str, pd.Series, np.ndarray],
    asset_b: Union[str, pd.Series, np.ndarray],
    max_lag: int = DEFAULT_MAX_LAG,
) -> Dict[str, object]:
    sa = _as_series(asset_a)
    sb = _as_series(asset_b)
    if sa is None or sb is None or len(sa) < 10 or len(sb) < 10:
        a_label, b_label = _labels(asset_a, asset_b)
        return {
            "lead_asset": a_label,
            "lag_asset": b_label,
            "lag": 0,
            "confidence": 0.0,
        }

    common = sa.index.intersection(sb.index)
    if len(common) < 10:
        a_label, b_label = _labels(asset_a, asset_b)
        return {
            "lead_asset": a_label,
            "lag_asset": b_label,
            "lag": 0,
            "confidence": 0.0,
        }
    pa = sa.loc[common].values
    pb = sb.loc[common].values

    a_label, b_label = _labels(asset_a, asset_b)
    lag, corr = _pearson_lagged(pa, pb, max_lag)
    if lag > 0:
        lead, lag_name, direction_lag = b_label, a_label, lag
    elif lag < 0:
        lead, lag_name, direction_lag = a_label, b_label, -lag
    else:
        lead, lag_name, direction_lag = a_label, b_label, 0

    return {
        "lead_asset": lead,
        "lag_asset": lag_name,
        "lag": direction_lag,
        "confidence": min(corr, 1.0),
    }


def build_lead_lag_matrix(
    windows: Iterable[int] = DEFAULT_WINDOWS,
    max_lag: int = DEFAULT_MAX_LAG,
    universe: Optional[Iterable[str]] = None,
) -> Dict[str, Dict[str, List[LeadLagResult]]]:
    """Build full lead-lag matrix across the 34-series universe.

    Downloads daily closes for every symbol, then evaluates each unique
    pair over every requested rolling window.

    Args:
        windows: Rolling window sizes in candles.
        max_lag: Maximum lag magnitude to test.
        universe: Optional asset list. Defaults to ``SERIES.keys()``.

    Returns:
        Nested dict: ``matrix[a][b] = [LeadLagResult, ...]``
    """
    assets = list(universe if universe is not None else SERIES.keys())
    if not assets:
        return {}

    prices: Dict[str, Optional[pd.Series]] = {}
    for asset in assets:
        prices[asset] = _fetch_prices(asset)

    matrix: Dict[str, Dict[str, List[LeadLagResult]]] = {}
    wins = tuple(windows)
    for i, a in enumerate(assets):
        matrix[a] = {}
        sa = prices.get(a)
        for j, b in enumerate(assets):
            if j <= i:
                continue
            sb = prices.get(b)
            if sa is None or sb is None:
                continue
            common = sa.index.intersection(sb.index)
            if len(common) < 30:
                continue
            pa = sa.loc[common].values
            pb = sb.loc[common].values
            matrix[a][b] = [
                _windowed_score(pa, pb, a, b, b, a, win, max_lag) for win in wins
            ]
    return matrix


def matrix_to_rows(
    matrix: Dict[str, Dict[str, List[LeadLagResult]]],
    min_confidence: float = 0.0,
) -> pd.DataFrame:
    """Flatten matrix into a row-oriented DataFrame for analysis/export."""
    rows: List[Dict[str, object]] = []
    for a, sub in matrix.items():
        for b, results in sub.items():
            for res in results:
                if min_confidence > 0 and abs(res.confidence) < min_confidence:
                    continue
                rows.append(
                    {
                        "asset_a": a,
                        "asset_b": b,
                        "lead_asset": res.lead_asset,
                        "lag_asset": res.lag_asset,
                        "lag_candles": res.lag,
                        "confidence": res.confidence,
                        "window": res.window,
                        "best_lag_corr": res.best_lag_corr,
                    }
                )
    return pd.DataFrame(rows)
