"""Alpha Decay Detection — monitors strategy signal degradation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

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


@dataclass
class DecayStatus:
    """Status report from AlphaDecayMonitor."""
    status: str  # "healthy" | "decaying" | "degraded"
    windows: Dict[str, float]  # e.g. {"20d": 1.2, "60d": 0.8, "120d": 0.5}
    decay_rate: float  # linear regression slope of sharpe vs time
    sharpe_history: List[float]  # rolling sharpe per bar
    reasons: Dict[str, str]


class AlphaDecayMonitor:
    """Tracks rolling Sharpe across multiple windows and detects decay.

    Windows are configurable (default 20, 60, 120 bars). Decay rate is
    the slope of a linear fit of rolling Sharpe over time.
    """

    def __init__(
        self,
        windows: tuple = (20, 60, 120),
        annual_factor: int = 252,
        decay_threshold: float = -0.05,
        degraded_threshold: float = -0.15,
    ) -> None:
        self.windows = windows
        self.annual_factor = annual_factor
        self.decay_threshold = decay_threshold
        self.degraded_threshold = degraded_threshold

    def compute(self, returns: np.ndarray) -> DecayStatus:
        if len(returns) < min(self.windows):
            return DecayStatus(
                status="healthy",
                windows={f"{w}d": 0.0 for w in self.windows},
                decay_rate=0.0,
                sharpe_history=[],
                reasons={"all": "Insufficient data"},
            )

        window_sharpes: Dict[str, float] = {}
        reasons: Dict[str, str] = {}
        full_sharpe: np.ndarray = np.array([])

        for w in self.windows:
            sharpe_list: List[float] = []
            for i in range(len(returns)):
                start = max(0, i - w + 1)
                seg = returns[start:i + 1]
                if len(seg) < 2:
                    sharpe_list.append(0.0)
                else:
                    sharpe_list.append(float(
                        np.mean(seg) / max(np.std(seg, ddof=1), 1e-10)
                        * np.sqrt(self.annual_factor)
                    ))
            sharpe_series = np.array(sharpe_list)
            if len(full_sharpe) == 0:
                full_sharpe = sharpe_series
            window_sharpes[f"{w}d"] = float(sharpe_series[-1])

        # Decay rate: linear regression of the longest-window sharpe
        series = full_sharpe
        if len(series) > 1:
            x = np.arange(len(series))
            decay_rate = float(np.polyfit(x, series, 1)[0])
        else:
            decay_rate = 0.0

        # Determine status from the most recent window
        latest = window_sharpes[f"{max(self.windows)}d"]
        if decay_rate < self.degraded_threshold or latest < 0.0:
            status = "degraded"
            reasons["overall"] = (
                f"Decay rate {decay_rate:.4f} < {self.degraded_threshold} "
                f"or latest sharpe {latest:.2f} < 0"
            )
        elif decay_rate < self.decay_threshold:
            status = "decaying"
            reasons["overall"] = f"Decay rate {decay_rate:.4f} < {self.decay_threshold}"
        else:
            status = "healthy"
            reasons["overall"] = "Stable or improving"

        for w in self.windows:
            key = f"{w}d"
            val = window_sharpes[key]
            if val < 0.0:
                reasons[key] = "Negative Sharpe"
            elif val < 0.5:
                reasons[key] = "Low Sharpe"
            else:
                reasons[key] = "OK"

        return DecayStatus(
            status=status,
            windows=window_sharpes,
            decay_rate=decay_rate,
            sharpe_history=full_sharpe.tolist(),
            reasons=reasons,
        )

    def check_and_log(self, returns: np.ndarray, strategy_name: str = "") -> DecayStatus:
        """Convenience wrapper: compute decay and log a warning if not healthy."""
        result = self.compute(returns)
        if result.status != "healthy":
            logger.warning(
                "Alpha decay [%s] strategy=%s status=%s rate=%.4f windows=%s",
                result.status,
                strategy_name,
                result.status,
                result.decay_rate,
                result.windows,
            )
        return result
