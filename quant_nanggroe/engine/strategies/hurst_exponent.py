"""Hurst Exponent — mean-reverting vs trending via the Hurst exponent."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class HurstExponentStrategy(Strategy):
    """Hurst Exponent — mean-reverting vs trending via rescaled range."""

    name = "hurst_exponent"
    description = "Hurst exponent: trending vs mean-reverting"

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        super().__init__(parameters=parameters or StrategyParameters())
        self.lookback: int = int(self._parameters.get("lookback", 100))
        self.min_lag: int = int(self._parameters.get("min_lag", 2))
        self.max_lag: int = int(self._parameters.get("max_lag", 20))

    @staticmethod
    def _hurst(series: np.ndarray, min_lag: int, max_lag: int) -> float:
        lags = range(min_lag, min(max_lag, len(series) // 2))
        tau = []
        for lag in lags:
            dd = series[lag:] - series[:-lag]
            tau.append(np.std(dd))
        if len(tau) < 3:
            return 0.5
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            if not hasattr(data, "iloc") or data is None or data.empty:
                return self._hold("No data")
            c = data["close"]
            if len(c) < self.lookback:
                return self._hold("Insufficient data")
            log_prices = np.log(c.values[-self.lookback:])
            if len(log_prices) < self.max_lag * 2 + 2:
                return self._hold("Insufficient data")
            h = self._hurst(log_prices, self.min_lag, self.max_lag)
            price = float(c.iloc[-1])
            # ── TREND STRENGTH CONFIRMATION (Phase-Improve) ──
            diff = c.diff()
            up = diff.clip(lower=0).rolling(14).sum()
            dn = (-diff.clip(upper=0)).rolling(14).sum()
            plus_dm = up.rolling(14).mean()
            minus_dm = dn.rolling(14).mean()
            dx = np.abs(plus_dm - minus_dm) / (plus_dm + minus_dm + 1e-10)
            adx = float(dx.rolling(14).mean().iloc[-1]) if len(dx) > 14 else 0.0
            if h > 0.6 and adx >= 20.0:
                ret = float(c.iloc[-1]) / float(c.iloc[-5]) - 1.0
                sig = 1.0 if ret > 0 else -1.0
                strength = np.clip((adx - 20) / 30.0, 0.1, 0.95)
                return StrategySignal(
                    strategy_name=self.name,
                    symbol=kwargs.get("symbol", ""),
                    direction=SignalDirection.BUY if sig > 0 else SignalDirection.SELL,
                    confidence=round(float(strength), 2),
                    entry_price=round(price, 6),
                    reasoning=f"Hurst {h:.3f} > 0.6: trending, ADX={adx:.1f}",
                    indicators={"hurst": round(h, 4), "adx": round(adx, 2)},
                )
            if h < 0.4:
                mean = float(log_prices[-10:].mean())
                z = (log_prices[-1] - mean) / np.std(log_prices[-10:]) if len(log_prices) >= 10 else 0
                if z < -0.5 and adx >= 20.0:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.BUY,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Hurst {h:.3f} < 0.4: mean-reversion",
                        indicators={"hurst": round(h, 4)},
                    )
                if z > 0.5:
                    return StrategySignal(
                        strategy_name=self.name,
                        symbol=kwargs.get("symbol", ""),
                        direction=SignalDirection.SELL,
                        confidence=0.5,
                        entry_price=round(price, 6),
                        reasoning=f"Hurst {h:.3f} < 0.4: mean-reversion",
                        indicators={"hurst": round(h, 4)},
                    )
            return self._hold(f"Hurst {h:.3f} neutral")
        except Exception as exc:
            logger.error("HurstExponent error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["HurstExponentStrategy"]
