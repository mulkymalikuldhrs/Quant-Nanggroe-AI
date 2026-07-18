"""Alpha Decay Detection — monitors strategy signal degradation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DecayResult:
    rolling_sharpe: float
    sharpe_trend: float
    ic_mean: float
    ic_std: float
    half_life_bars: Optional[float]
    is_decaying: bool
    reason: str


class AlphaDecayDetector:
    def __init__(self, lookback: int = 60, decay_threshold: float = -0.1):
        self._lookback = lookback
        self._decay_threshold = decay_threshold

    def detect(self, returns: np.ndarray, signals: np.ndarray) -> DecayResult:
        if len(returns) < self._lookback:
            return DecayResult(0.0, 0.0, 0.0, 0.0, None, False, "Insufficient data")

        rolling_sharpe = np.array([
            np.mean(returns[max(0, i - 20):i + 1]) / max(np.std(returns[max(0, i - 20):i + 1]), 1e-10) * np.sqrt(252)
            for i in range(len(returns))
        ])

        x = np.arange(len(rolling_sharpe[-self._lookback:]))
        y = rolling_sharpe[-self._lookback:]
        slope = np.polyfit(x, y, 1)[0] if len(x) > 1 else 0.0

        min_len = min(len(returns), len(signals))
        ic_series = np.array([
            np.corrcoef(signals[max(0, i - 20):i + 1], returns[max(0, i - 20):i + 1])[0, 1]
            for i in range(self._lookback, min_len)
        ])
        ic_series = ic_series[~np.isnan(ic_series)]
        ic_mean = float(np.mean(ic_series)) if len(ic_series) > 0 else 0.0
        ic_std = float(np.std(ic_series)) if len(ic_series) > 0 else 0.0

        half_life = None
        if len(rolling_sharpe) > 10:
            y_lag = rolling_sharpe[:-1]
            beta = np.polyfit(y_lag, rolling_sharpe[1:], 1)[0]
            if 0 < beta < 1:
                half_life = -np.log(2) / np.log(beta)

        is_decaying = slope < self._decay_threshold or ic_mean < 0.02
        reason = "Sharpe declining" if slope < self._decay_threshold else "IC near zero" if ic_mean < 0.02 else "Stable"

        return DecayResult(
            rolling_sharpe=float(np.mean(rolling_sharpe[-self._lookback:])) if len(rolling_sharpe) >= self._lookback else 0.0,
            sharpe_trend=float(slope),
            ic_mean=ic_mean,
            ic_std=ic_std,
            half_life_bars=half_life,
            is_decaying=is_decaying,
            reason=reason,
        )
