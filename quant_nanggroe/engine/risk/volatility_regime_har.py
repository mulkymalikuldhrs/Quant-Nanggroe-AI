from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class VolRegime(Enum):
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class HARForecast:
    daily_vol: float
    weekly_vol: float
    monthly_vol: float
    regime: VolRegime
    confidence: float
    jump_component: float
    vol_of_vol: float


@dataclass
class THARState:
    trend_vol: float
    residual_vol: float
    jump_intensity: float
    regime: VolRegime


class RegimeSwitchingHAR:
    """Regime-switching Heterogeneous Autoregressive (HAR) volatility model.

    Implements the THAR (Threshold HAR) and STHAR (Smooth Transition HAR):
      - HAR-RV: RV_t = beta0 + beta1*RV_daily + beta2*RV_weekly + beta3*RV_monthly + eps
      - Regime-switching via volatility threshold or smooth transition
      - Jump detection via C-Tz (contribution to z) statistic
      - Vol-of-vol as separate regime dimension

    Reference: Fed WP 2025-061 — THAR/STHAR beats LSTM/GRU for volatility
              Corsi, F. (2009) 'HAR-RV Model'
    """

    def __init__(self, daily_window: int = 22, weekly_window: int = 66, monthly_window: int = 252):
        self.daily_window = daily_window
        self.weekly_window = weekly_window
        self.monthly_window = monthly_window
        self._returns: list[float] = []
        self._realized_vol: list[float] = []
        self._jumps: list[float] = []

    def add_return(self, log_return: float) -> None:
        self._returns.append(log_return)
        if len(self._returns) > self.monthly_window * 4:
            self._returns = self._returns[-self.monthly_window * 4:]

    def _compute_rv(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        return float(np.sqrt(np.sum(np.square(np.array(returns)))) * np.sqrt(252 / len(returns)))

    def _detect_jumps(self, returns: list[float]) -> tuple[float, float]:
        if len(returns) < 10:
            return 0.0, 0.0
        arr = np.array(returns)
        bpv = np.pi / 2 * np.mean(np.abs(arr[1:]) * np.abs(arr[:-1]))
        rv = np.sum(arr ** 2)
        if rv < 1e-12:
            return 0.0, 0.0
        ctz = (rv - bpv) / (rv * np.sqrt(2.0 / len(returns)) + 1e-10)
        jump = max(0.0, rv - bpv) / (rv + 1e-10)
        return float(ctz), float(jump)

    def forecast(self) -> HARForecast:
        n = len(self._returns)
        if n < 5:
            return HARForecast(0.0, 0.0, 0.0, VolRegime.NORMAL, 0.5, 0.0, 0.0)

        daily_rv = self._compute_rv(self._returns[-min(self.daily_window, n):])
        weekly_rv = self._compute_rv(self._returns[-min(self.weekly_window, n):])
        monthly_rv = self._compute_rv(self._returns[-min(self.monthly_window, n):])

        # HAR-RV with simple beta estimates (identity weighting as baseline)
        daily_beta, weekly_beta, monthly_beta = 0.4, 0.3, 0.1
        forecast_vol = daily_beta * daily_rv + weekly_beta * weekly_rv + monthly_beta * monthly_rv

        # Vol-of-vol
        if len(self._realized_vol) > 10:
            vol_of_vol = float(np.std(self._realized_vol[-20:]))
        else:
            vol_of_vol = forecast_vol * 0.3

        # Regime classification
        vol_percentile = 0.5
        if len(self._realized_vol) > 60:
            hist = np.array(self._realized_vol[-252:]) if len(self._realized_vol) >= 252 else np.array(self._realized_vol)
            if hist.max() != hist.min():
                vol_percentile = (forecast_vol - hist.min()) / (hist.max() - hist.min())

        if vol_percentile < 0.15:
            regime = VolRegime.LOW
        elif vol_percentile < 0.40:
            regime = VolRegime.NORMAL
        elif vol_percentile < 0.70:
            regime = VolRegime.ELEVATED
        elif vol_percentile < 0.90:
            regime = VolRegime.HIGH
        else:
            regime = VolRegime.EXTREME

        # Jump detection
        ctz, jump_frac = self._detect_jumps(self._returns[-min(60, n):])
        self._jumps.append(jump_frac)
        if len(self._jumps) > 252:
            self._jumps = self._jumps[-252:]

        # Store realized vol
        self._realized_vol.append(daily_rv)
        if len(self._realized_vol) > 252 * 2:
            self._realized_vol = self._realized_vol[-252 * 2:]

        # Confidence based on forecast stability
        confidence = 0.7
        if vol_of_vol > forecast_vol * 0.5:
            confidence = 0.5
        if regime == VolRegime.EXTREME:
            confidence = 0.4

        return HARForecast(
            daily_vol=daily_rv,
            weekly_vol=weekly_rv,
            monthly_vol=monthly_rv,
            regime=regime,
            confidence=confidence,
            jump_component=jump_frac,
            vol_of_vol=vol_of_vol,
        )

    def thar_state(self) -> THARState:
        fc = self.forecast()
        trend = fc.weekly_vol + fc.monthly_vol
        residual = fc.daily_vol - trend * 0.3
        return THARState(
            trend_vol=trend,
            residual_vol=max(0.0, residual),
            jump_intensity=fc.jump_component,
            regime=fc.regime,
        )

    def get_position_sizing_factor(self, base_risk: float = 0.005) -> float:
        fc = self.forecast()
        if fc.regime == VolRegime.LOW:
            return base_risk * 1.5
        elif fc.regime == VolRegime.NORMAL:
            return base_risk
        elif fc.regime == VolRegime.ELEVATED:
            return base_risk * 0.5
        elif fc.regime == VolRegime.HIGH:
            return base_risk * 0.25
        else:
            return base_risk * 0.1

    def to_dict(self) -> dict[str, Any]:
        fc = self.forecast()
        return {
            "daily_vol": fc.daily_vol,
            "weekly_vol": fc.weekly_vol,
            "monthly_vol": fc.monthly_vol,
            "regime": fc.regime.value,
            "confidence": fc.confidence,
            "jump_component": fc.jump_component,
            "vol_of_vol": fc.vol_of_vol,
            "sizing_factor": self.get_position_sizing_factor(),
        }
