"""HMM Regime Detection Upgrade — Fase 1.3.

Replace rule-based regime with a 4-state Hidden Markov Model.
Observable variables: DXY, ZB1, VIX, GC1, ES1, NQ1.
Training window: rolling 252 bars.
Output: per-state probabilities for RISK_ON, RISK_OFF, STAGFLATION, LIQUIDITY_CRISIS.

Preferred backend: hmmlearn (GaussianHMM).
Fallback: sklearn.mixture.GaussianMixture (emission model only, regime = argmax component).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Iterable, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

REGIME_LABELS = [
    "RISK_ON",
    "RISK_OFF",
    "STAGFLATION",
    "LIQUIDITY_CRISIS",
]

OBSERVABLE_TICKERS = {
    "DXY": "DX-Y.NYB",
    "ZB1": "ZB=F",
    "VIX": "^VIX",
    "GC1": "GC=F",
    "ES1": "ES=F",
    "NQ1": "NQ=F",
}


@dataclass
class RegimeDetectionResult:
    """Output of HMM regime detection."""
    label: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    details: dict[str, object] = field(default_factory=dict)

    def dominant_state(self) -> str:
        if not self.probabilities:
            return "NEUTRAL"
        return max(self.probabilities.items(), key=lambda kv: kv[1])[0]


class HMMRegimeDetector:
    """Rolling 4-state HMM regime detector.

    Usage
    -----
    >>> det = HMMRegimeDetector(window=252, seed=42)
    >>> result = det.fit_predict(feature_df, current_row=None)
    >>> print(result.label, result.probabilities)
    """

    def __init__(
        self,
        window: int = 252,
        seed: int = 42,
        use_hmmlearn: Optional[bool] = None,
    ) -> None:
        if window < 10:
            raise ValueError("window must be >= 10 for stable emission estimation.")
        self.window = int(window)
        self.seed = int(seed)
        if use_hmmlearn is None:
            use_hmmlearn = _has_hmmlearn()
        self.use_hmmlearn = bool(use_hmmlearn)
        self._model = None
        self._scaler = None
        self._feature_cols: list[str] = list(OBSERVABLE_TICKERS.keys())

    # ── Public API ─────────────────────────────────────────────────────

    def fit_predict(
        self,
        feature_df: pd.DataFrame,
        current_row: Optional[pd.Series] = None,
    ) -> RegimeDetectionResult:
        """Fit on rolling window and emit regime probabilities for the newest bar.

        Parameters
        ----------
        feature_df:
            Full feature history (rows: time, cols: DXY, ZB1, VIX, GC1, ES1, NQ1).
        current_row:
            The row to classify. Defaults to the last row of `feature_df`.
        """
        if feature_df is None or feature_df.empty:
            return RegimeDetectionResult(
                label="NEUTRAL",
                confidence=0.0,
                probabilities={k: 1.0 / len(REGIME_LABELS) for k in REGIME_LABELS},
            )

        x, cols = _clean_matrix(feature_df, self._feature_cols)
        if x.shape[0] < 10:
            logger.warning("HMM skipped: only %d rows available.", x.shape[0])
            return self._fallback()

        train = x[-min(self.window, x.shape[0]) :]
        x_scaled, scaler = _standardize(train)
        self._scaler = scaler

        if self.use_hmmlearn:
            probs = self._fit_hmmlearn(x_scaled)
        else:
            probs = self._fit_gmm(x_scaled)
        probs = _coerce_probabilities(probs, n_states=len(REGIME_LABELS))

        label, confidence = _decode(probs)
        return RegimeDetectionResult(
            label=label,
            confidence=confidence,
            probabilities=dict(zip(REGIME_LABELS, probs.tolist())),
            details={
                "backend": "hmmlearn" if self.use_hmmlearn else "gaussian_mixture",
                "n_samples_used": int(train.shape[0]),
                "features": cols,
            },
        )

    # ── Internals ──────────────────────────────────────────────────────

    def _fit_hmmlearn(self, x_scaled: np.ndarray) -> np.ndarray:
        try:
            from hmmlearn.hmm import GaussianHMM
        except ImportError:
            logger.debug("hmmlearn unavailable; falling back to GMM.")
            return self._fit_gmm(x_scaled)

        model = GaussianHMM(
            n_components=4,
            covariance_type="full",
            n_iter=400,
            random_state=self.seed,
        )
        model.fit(x_scaled)
        self._model = model
        probs = model.predict_proba(x_scaled[-1:])[0]
        return probs

    def _fit_gmm(self, x_scaled: np.ndarray) -> np.ndarray:
        from sklearn.mixture import GaussianMixture

        model = GaussianMixture(
            n_components=4,
            covariance_type="full",
            random_state=self.seed,
            max_iter=400,
        )
        model.fit(x_scaled)
        self._model = model
        log_probs = model.predict_proba(x_scaled[-1:])
        return log_probs[0]

    def _fallback(self) -> RegimeDetectionResult:
        return RegimeDetectionResult(
            label="NEUTRAL",
            confidence=0.0,
            probabilities={k: 1.0 / len(REGIME_LABELS) for k in REGIME_LABELS},
        )


# ── yfinance integration ──────────────────────────────────────────────

def fetch_observables(
    tickers: Optional[dict[str, str]] = None,
    period: str = "3y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Fetch observable futures/indices from yfinance.

    Returns a DataFrame with columns: DXY, ZB1, VIX, GC1, ES1, NQ1.
    Missing tickers are silently dropped.
    """
    tickers = tickers or OBSERVABLE_TICKERS
    try:
        import yfinance as yf
    except ImportError as exc:
        raise ImportError("yfinance is required for live data fetching.") from exc

    frames: list[pd.DataFrame] = []
    for label, symbol in tickers.items():
        try:
            hist = yf.Ticker(symbol).history(period=period, interval=interval)
            if hist is None or hist.empty:
                logger.debug("No data for %s (%s)", label, symbol)
                continue
            ser = hist["Close"].rename(label)
            frames.append(ser)
        except Exception as e:
            logger.debug("fetch_observables failed for %s: %s", label, e)

    if not frames:
        return pd.DataFrame(columns=list(tickers.keys()))

    df = pd.concat(frames, axis=1).sort_index()
    df.columns = list(tickers.keys())[: len(df.columns)]
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build simple return + level features for HMM input.

    Produces columns: ret_DXY, ret_ZB1, ret_VIX, ret_GC1, ret_ES1, ret_NQ1,
    level_DXY, level_VIX (scaled by 10).
    """
    out = pd.DataFrame(index=df.index)
    for col in df.columns:
        out[f"ret_{col}"] = df[col].pct_change().clip(-1.0, 1.0)
        if col in ("DXY", "VIX"):
            out[f"level_{col}"] = (df[col] / 10.0).clip(-50, 50)
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    return out


# ── Helpers ──────────────────────────────────────────────────────────

def _has_hmmlearn() -> bool:
    try:
        import hmmlearn  # noqa: F401
        return True
    except ImportError:
        return False


def _clean_matrix(
    df: pd.DataFrame, expected: list[str]
) -> tuple[np.ndarray, list[str]]:
    df = df.copy().replace([np.inf, -np.inf], np.nan).ffill().bfill()
    cols = [c for c in expected if c in df.columns]
    if not cols:
        raise ValueError("No expected feature columns found in DataFrame.")
    x = df[cols].values
    if np.isnan(x).any():
        raise ValueError("NaN found after imputation.")
    return x, cols


def _standardize(x: np.ndarray):
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    return x_scaled, scaler


def _coerce_probabilities(probs: np.ndarray, n_states: int) -> np.ndarray:
    probs = np.asarray(probs, dtype=float).flatten()
    if probs.shape[0] != n_states:
        pad = n_states - probs.shape[0]
        probs = np.concatenate([probs, np.zeros(pad)])
    probs = np.clip(probs, 0.0, None)
    s = float(probs.sum())
    if s <= 0:
        return np.full(n_states, 1.0 / n_states)
    return probs / s


def _decode(probs: np.ndarray) -> tuple[str, float]:
    idx = int(np.argmax(probs))
    label = REGIME_LABELS[idx] if idx < len(REGIME_LABELS) else "NEUTRAL"
    confidence = float(probs[idx])
    return label, confidence


def regime_probabilities_from_context(
    dxy_change_pct: float = 0.0,
    bond_zb_change_pct: float = 0.0,
    vix_level: float = 20.0,
) -> dict[str, float]:
    """Diagnostic fallback mapping from macro weather to regime probabilities.

    Used when market data is unavailable.
    """
    if dxy_change_pct > 0.3 and bond_zb_change_pct > 0.2 and vix_level > 30:
        return {
            "RISK_ON": 0.05,
            "RISK_OFF": 0.7,
            "STAGFLATION": 0.15,
            "LIQUIDITY_CRISIS": 0.1,
        }
    if dxy_change_pct < -0.3 and bond_zb_change_pct < -0.1 and vix_level < 20:
        return {
            "RISK_ON": 0.75,
            "RISK_OFF": 0.1,
            "STAGFLATION": 0.05,
            "LIQUIDITY_CRISIS": 0.1,
        }
    if vix_level > 35 and bond_zb_change_pct > 0.3:
        return {
            "RISK_ON": 0.05,
            "RISK_OFF": 0.2,
            "STAGFLATION": 0.25,
            "LIQUIDITY_CRISIS": 0.5,
        }
    if vix_level > 25 and dxy_change_pct > 0.2:
        return {
            "RISK_ON": 0.1,
            "RISK_OFF": 0.5,
            "STAGFLATION": 0.25,
            "LIQUIDITY_CRISIS": 0.15,
        }
    if bond_zb_change_pct > 0.2 and dxy_change_pct > 0.2:
        return {
            "RISK_ON": 0.1,
            "RISK_OFF": 0.6,
            "STAGFLATION": 0.15,
            "LIQUIDITY_CRISIS": 0.15,
        }
    return {
        "RISK_ON": 0.25,
        "RISK_OFF": 0.25,
        "STAGFLATION": 0.25,
        "LIQUIDITY_CRISIS": 0.25,
    }


__all__ = [
    "HMMRegimeDetector",
    "RegimeDetectionResult",
    "REGIME_LABELS",
    "OBSERVABLE_TICKERS",
    "fetch_observables",
    "build_features",
    "regime_probabilities_from_context",
]
