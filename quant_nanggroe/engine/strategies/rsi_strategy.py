"""RSI Strategy — adaptive period (vol-based) + multi-timeframe confirmation.

Works with a SINGLE OHLCV DataFrame. Two enhancements over plain RSI:

1. Adaptive period: the RSI lookback shrinks in high-volatility regimes
   (more responsive) and lengthens in calm regimes (less noise). The
   period is derived from realised return volatility percentile.

2. Multi-timeframe confirmation via window-length proxies:
   - H4 bias  : longer resampled/aggregated window sets the directional bias
   - M15 entry: fast RSI on the base series times the actual entry

Entry only fires when the fast (M15-proxy) RSI oversold/overbought signal
agrees with the H4-proxy directional bias.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import numpy as np

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    Strategy,
    StrategyParameters,
    StrategySignal,
)
from quant_nanggroe.engine.strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register
class RSIStrategy(Strategy):
    """Adaptive RSI with H4-bias / M15-entry multi-timeframe confirmation."""

    name = "rsi"
    description = "Adaptive-period RSI with multi-timeframe (H4 bias + M15 entry) confirmation"
    required_indicators = ["close"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        # Adaptive period bounds
        if not params.get("base_period"):
            params.set("base_period", 14)
        if not params.get("min_period"):
            params.set("min_period", 7)
        if not params.get("max_period"):
            params.set("max_period", 28)
        if not params.get("vol_window"):
            params.set("vol_window", 100)   # window for vol percentile
        # RSI thresholds
        if not params.get("overbought"):
            params.set("overbought", 70.0)
        if not params.get("oversold"):
            params.set("oversold", 30.0)
        # MTF proxy: H4 bias uses aggregation factor over the base (M15) series
        if not params.get("htf_factor"):
            params.set("htf_factor", 16)    # 16 * M15 ~= H4
        if not params.get("htf_ema"):
            params.set("htf_ema", 20)       # bias EMA length on H4 proxy
        super().__init__(parameters=params)

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------

    def _extract(self, data: Any, key: str) -> np.ndarray:
        if hasattr(data, "iloc"):
            return data[key].values.astype(np.float64)
        elif isinstance(data, dict):
            vals = data.get(key, [])
            return np.array(vals, dtype=np.float64) if vals else np.array([], dtype=np.float64)
        return np.array([], dtype=np.float64)

    # ------------------------------------------------------------------
    # RSI (Wilder-smoothed)
    # ------------------------------------------------------------------

    @staticmethod
    def _rsi(closes: np.ndarray, period: int) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        # Seed with simple average of first `period`
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        # Wilder smoothing over the remainder
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss < 1e-12:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ------------------------------------------------------------------
    # Adaptive period from volatility percentile
    # ------------------------------------------------------------------

    def _adaptive_period(self, closes: np.ndarray) -> Tuple[int, float]:
        """Return (period, vol_percentile). High vol -> shorter period."""
        base = int(self._parameters.get("base_period", 14))
        pmin = int(self._parameters.get("min_period", 7))
        pmax = int(self._parameters.get("max_period", 28))
        vw = int(self._parameters.get("vol_window", 100))

        rets = np.diff(closes) / (closes[:-1] + 1e-12)
        if len(rets) < 20:
            return base, 0.5

        window = rets[-vw:] if len(rets) >= vw else rets
        # Rolling short-term vol (last 14 returns) vs distribution of window
        recent_vol = float(np.std(rets[-14:])) if len(rets) >= 14 else float(np.std(rets))
        # Percentile of recent_vol within window's rolling vols
        roll = np.array([
            np.std(window[max(0, i - 14):i + 1])
            for i in range(len(window))
        ])
        roll = roll[np.isfinite(roll)]
        if len(roll) < 2:
            return base, 0.5
        pct = float(np.mean(roll <= recent_vol))  # 0..1, higher = higher vol
        # High vol (pct->1) -> shorter period (toward pmin)
        # Low vol  (pct->0) -> longer period  (toward pmax)
        period = int(round(pmax - pct * (pmax - pmin)))
        period = max(pmin, min(pmax, period))
        return period, pct

    # ------------------------------------------------------------------
    # H4 bias proxy: aggregate base series then EMA slope
    # ------------------------------------------------------------------

    def _htf_bias(self, closes: np.ndarray) -> Tuple[str, float]:
        factor = int(self._parameters.get("htf_factor", 16))
        ema_len = int(self._parameters.get("htf_ema", 20))
        if len(closes) < factor * 3:
            return "neutral", 0.0
        # Aggregate: take every `factor`-th close as H4 proxy bar
        htf = closes[::factor]
        if len(htf) < ema_len + 2:
            # fall back to whatever we have
            htf = closes[-(ema_len * factor):][::max(1, factor)]
            if len(htf) < 3:
                return "neutral", 0.0
        # EMA
        alpha = 2.0 / (min(ema_len, len(htf)) + 1)
        ema = htf[0]
        ema_prev = ema
        for i in range(1, len(htf)):
            ema_prev = ema
            ema = alpha * htf[i] + (1 - alpha) * ema
        slope = (ema - ema_prev) / (ema_prev + 1e-12)
        # Also require price above/below ema for confirmation
        last = htf[-1]
        if slope > 0 and last >= ema:
            return "bullish", min(abs(slope) * 50, 1.0)
        if slope < 0 and last <= ema:
            return "bearish", min(abs(slope) * 50, 1.0)
        return "neutral", 0.0

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            closes = self._extract(data, "close")
            factor = int(self._parameters.get("htf_factor", 16))
            min_needed = max(factor * 3, int(self._parameters.get("base_period", 14)) + 5)
            if len(closes) < min_needed:
                return self._hold(f"Insufficient data (need {min_needed}+ bars)")

            overbought = float(self._parameters.get("overbought", 70.0))
            oversold = float(self._parameters.get("oversold", 30.0))

            # 1) Adaptive period from volatility
            period, vol_pct = self._adaptive_period(closes)

            # 2) M15-entry RSI (fast, adaptive period on base series)
            rsi_val = self._rsi(closes, period)

            # 3) H4 bias
            bias, bias_str = self._htf_bias(closes)

            current_price = float(closes[-1])
            indicators = {
                "rsi": round(rsi_val, 2),
                "adaptive_period": period,
                "vol_percentile": round(vol_pct, 3),
                "h4_bias": bias,
                "h4_bias_strength": round(bias_str, 4),
                "overbought": overbought,
                "oversold": oversold,
            }

            # M15 raw entry signal
            if rsi_val < oversold:
                entry_dir = "bullish"
            elif rsi_val > overbought:
                entry_dir = "bearish"
            else:
                return self._hold(f"RSI {rsi_val:.1f} neutral (period={period})", indicators)

            # MTF confirmation: entry must agree with H4 bias
            if bias == "neutral":
                return self._hold(
                    f"RSI {rsi_val:.1f} {entry_dir} but H4 bias neutral — no confirm",
                    indicators,
                )
            if entry_dir != bias:
                return self._hold(
                    f"RSI {rsi_val:.1f} {entry_dir} conflicts H4 bias {bias}",
                    indicators,
                )

            # Confirmed
            is_bullish = entry_dir == "bullish"
            direction = SignalDirection.BUY if is_bullish else SignalDirection.SELL

            # Confidence: RSI extremity * bias strength
            extremity = (
                (oversold - rsi_val) / oversold if is_bullish
                else (rsi_val - overbought) / (100.0 - overbought)
            )
            extremity = max(0.0, min(extremity, 1.0))
            confidence = min(0.5 + extremity * 0.3 + bias_str * 0.2, 0.95)

            if confidence > 0.7:
                strength = SignalStrength.STRONG
            elif confidence > 0.5:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # SL/TP via recent volatility
            recent_range = float(np.std(closes[-min(20, len(closes)):]))
            atr_like = max(recent_range, current_price * 0.005)
            if is_bullish:
                sl = current_price - atr_like * 1.5
                tp = current_price + atr_like * 3.0
            else:
                sl = current_price + atr_like * 1.5
                tp = current_price - atr_like * 3.0

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=round(confidence, 4),
                entry_price=round(current_price, 6),
                stop_loss=round(sl, 6),
                take_profit=round(tp, 6),
                risk_reward_ratio=self.calculate_risk_reward(current_price, sl, tp, direction),
                reasoning=(
                    f"RSI {rsi_val:.1f} {entry_dir} (period={period}, vol_pct={vol_pct:.2f}) "
                    f"confirmed by H4 bias {bias}"
                ),
                indicators=indicators,
            )

        except Exception as exc:
            logger.error("RSIStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["RSIStrategy"]
