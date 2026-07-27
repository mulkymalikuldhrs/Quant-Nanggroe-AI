"""Multi-Timeframe Strategy — trend alignment across proxy windows.

Works with a SINGLE OHLCV DataFrame (daily bars from pipeline).
Uses multiple window lengths as proxies for higher/medium/lower timeframes:

- Long window (50 bars):  HTF proxy — sets the trend direction
- Medium window (20 bars): MTF proxy — confirms alignment
- Short window (5 bars):  LTF proxy — entry timing

Alignment rules (require_alignment):
- "all": HTF + MTF + LTF must agree
- "htf_mtf": HTF + MTF agree, LTF can be neutral
- "htf": HTF sets direction, MTF/LTF just refine confidence
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
class MultiTimeframeStrategy(Strategy):
    """Multi-timeframe trend alignment strategy using window-length proxies.

    Detects trend direction at short/medium/long windows and requires
    alignment before generating a signal.
    """

    name = "multi_timeframe"
    description = "MTF alignment: long/medium/short window trend consensus"
    required_indicators = ["close"]

    def __init__(self, parameters: Optional[StrategyParameters] = None) -> None:
        params = parameters or StrategyParameters()
        if not params.get("htf_bars"):
            params.set("htf_bars", 50)       # ~2.5 months daily
        if not params.get("mtf_bars"):
            params.set("mtf_bars", 20)        # ~1 month daily
        if not params.get("ltf_bars"):
            params.set("ltf_bars", 5)         # ~1 week daily
        if not params.get("slope_threshold"):
            params.set("slope_threshold", 0.005)  # 0.5 % min slope
        if not params.get("require_alignment"):
            params.set("require_alignment", "htf_mtf")  # all | htf_mtf | htf
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
    # Trend detection via SMA slope
    # ------------------------------------------------------------------

    def _detect_trend(self, closes: np.ndarray, window: int) -> Tuple[str, float]:
        """Return (direction, strength) where strength = normalised slope."""
        if len(closes) < window + 2:
            return "neutral", 0.0
        sma = np.convolve(closes, np.ones(window) / window, mode="valid")
        if len(sma) < 2:
            return "neutral", 0.0
        # Slope over second half of SMA window
        half = max(1, len(sma) // 2)
        slope = (sma[-1] - sma[-half]) / (sma[-half] + 1e-10)
        threshold = self._parameters.get("slope_threshold", 0.005)
        if slope > threshold:
            return "bullish", min(abs(slope) / (threshold * 3), 1.0)
        elif slope < -threshold:
            return "bearish", min(abs(slope) / (threshold * 3), 1.0)
        return "neutral", 0.0

    # ------------------------------------------------------------------
    # Volatility regime
    # ------------------------------------------------------------------

    def _detect_volatility(self, closes: np.ndarray, window: int) -> str:
        if len(closes) < window + 1:
            return "normal"
        rets = np.diff(closes[-window:]) / (closes[-window:-1] + 1e-10)
        if len(rets) < 2:
            return "normal"
        vol = np.std(rets)
        avg_ret = np.mean(np.abs(rets))
        if avg_ret > 0 and vol / avg_ret > 3.0:
            return "high"
        return "normal"

    # ------------------------------------------------------------------
    # Alignment checks
    # ------------------------------------------------------------------

    def _check_alignment(
        self, htf_dir: str, mtf_dir: str, ltf_dir: str,
    ) -> Tuple[bool, str, float]:
        """Return (aligned, reason, confidence_multiplier)."""
        require = self._parameters.get("require_alignment", "htf_mtf")

        # HTF must be directional
        if htf_dir == "neutral":
            return False, "HTF neutral — no clear trend", 0.0

        # MTF check
        if require in ("all", "htf_mtf"):
            if mtf_dir not in (htf_dir, "neutral"):
                return False, f"MTF disagreement: {mtf_dir} vs HTF {htf_dir}", 0.0

        # LTF check
        if require == "all":
            if ltf_dir not in (htf_dir, "neutral"):
                return False, f"LTF disagreement: {ltf_dir} vs HTF {htf_dir}", 0.0

        # Compute confidence multiplier based on alignment strength
        aligned_count = sum(1 for d in [mtf_dir, ltf_dir] if d == htf_dir)
        total_active = sum(1 for d in [mtf_dir, ltf_dir] if d != "neutral")
        if total_active == 0:
            mult = 0.6  # HTF alone, no confirmation
        else:
            mult = 0.6 + (aligned_count / total_active) * 0.4
        return True, f"Aligned: HTF={htf_dir} MTF={mtf_dir} LTF={ltf_dir}", min(mult, 1.0)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        try:
            closes = self._extract(data, "close")
            if len(closes) < self._parameters.get("htf_bars", 50) + 5:
                return self._hold(f"Insufficient data (need {self._parameters.get('htf_bars', 50) + 5}+ bars)")

            htf_bars = self._parameters.get("htf_bars", 50)
            mtf_bars = self._parameters.get("mtf_bars", 20)
            ltf_bars = self._parameters.get("ltf_bars", 5)

            # Detect trends
            htf_dir, htf_str = self._detect_trend(closes, htf_bars)
            mtf_dir, mtf_str = self._detect_trend(closes, mtf_bars)
            ltf_dir, ltf_str = self._detect_trend(closes, ltf_bars)

            # Volatility
            vol = self._detect_volatility(closes, htf_bars)

            indicators = {
                "htf_trend": htf_dir, "htf_strength": round(htf_str, 4),
                "mtf_trend": mtf_dir, "mtf_strength": round(mtf_str, 4),
                "ltf_trend": ltf_dir, "ltf_strength": round(ltf_str, 4),
                "volatility": vol,
                "htf_bars": htf_bars, "mtf_bars": mtf_bars, "ltf_bars": ltf_bars,
            }

            # Check alignment
            aligned, reason, conf_mult = self._check_alignment(htf_dir, mtf_dir, ltf_dir)
            if not aligned:
                return self._hold(f"MTF not aligned: {reason}", indicators)

            current_price = float(closes[-1])

            # Determine direction and confidence
            is_bullish = htf_dir == "bullish"
            direction = SignalDirection.BUY if is_bullish else SignalDirection.SELL

            # Base confidence from HTF strength * alignment multiplier
            base_conf = htf_str if htf_str > 0 else 0.3
            confidence = min(base_conf * conf_mult, 0.9)

            # Apply volatility penalty
            if vol == "high":
                confidence *= 0.8

            # Determine signal strength
            if confidence > 0.6:
                strength = SignalStrength.STRONG
            elif confidence > 0.35:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # SL/TP based on ATR-like volatility
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
                entry_price=current_price,
                stop_loss=round(sl, 2),
                take_profit=round(tp, 2),
                risk_reward=self.calculate_risk_reward(current_price, sl, tp, direction),
                reasoning=f"MTF aligned: {reason} (conf={confidence:.2f}, vol={vol})",
                indicators=indicators,
            )

        except Exception as exc:
            logger.error("MultiTimeframeStrategy error: %s", exc)
            return self._hold(f"Error: {exc}")

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )


__all__ = ["MultiTimeframeStrategy"]
