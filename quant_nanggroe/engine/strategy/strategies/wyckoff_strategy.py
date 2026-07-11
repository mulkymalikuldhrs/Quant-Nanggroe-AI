"""Wyckoff Method trading strategy.

Detects accumulation/distribution phases using Wyckoff principles:
preliminary support, selling climax, automatic rally, secondary test,
spring, upthrust, LPS.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class WyckoffStrategy(BaseStrategy):
    """Wyckoff Method strategy.

    Parameters:
        lookback (int): Overall lookback for phase detection (default 50)
        vol_surge_mult (float): Volume surge multiplier for climax (default 2.0)
        spring_atr_mult (float): ATR multiplier for spring depth (default 1.5)
        min_phase_bars (int): Min bars to confirm a phase (default 5)
    """

    def __init__(self, name: str = "Wyckoff", params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name, params)
        self.lookback = params.get("lookback", 50)
        self.vol_mult = params.get("vol_surge_mult", 2.0)
        self.spring_atr = params.get("spring_atr_mult", 1.5)
        self.min_bars = params.get("min_phase_bars", 5)

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return 60

    def _detect_accumulation(self, close: np.ndarray, high: np.ndarray, low: np.ndarray, vol: np.ndarray, atr: np.ndarray) -> Optional[Dict]:
        """Detect Wyckoff accumulation phase."""
        n = len(close)
        avg_vol = np.mean(vol)

        # 1. Preliminary Support (PS) — first high volume after downtrend
        trend = close[-1] - close[-self.lookback]
        if trend > 0:
            return None

        vol_surges = np.where(vol > avg_vol * self.vol_mult)[0]
        if len(vol_surges) < 2:
            return None

        # Find Selling Climax (SC) — biggest volume surge in 30 bars
        window = min(30, n)
        sc_candidates = vol_surges[vol_surges >= n - window]
        if len(sc_candidates) == 0:
            return None
        sc_idx = sc_candidates[np.argmax(vol[sc_candidates])]
        sc_close = close[sc_idx]
        sc_high = high[sc_idx]
        sc_low = low[sc_idx]

        # 2. Automatic Rally (AR) — bounce after SC with decreasing volume
        ar_volumes = vol[sc_idx+1:sc_idx+self.min_bars+1] if sc_idx+self.min_bars < n else []
        if len(ar_volumes) == 0:
            return None
        ar_rising = close[min(sc_idx+1, n-1)] > sc_close
        ar_vol_decline = np.mean(ar_volumes) < avg_vol * 1.5
        if not (ar_rising and ar_vol_decline):
            return None

        ar_high = max(high[sc_idx+1:sc_idx+self.min_bars+1]) if sc_idx+self.min_bars < n else sc_high

        # 3. Secondary Test (ST) — revisit SC area with lower volume
        st_idx = min(sc_idx + self.min_bars + 5, n - 1)
        st_low = low[st_idx]
        st_vol = vol[st_idx]
        near_sc = abs(st_low - sc_low) / sc_low < 0.02
        lower_vol = st_vol < vol[sc_idx] * 0.7
        if not (near_sc and lower_vol):
            return None

        # 4. Check for Spring (final accumulation signal)
        spring_detected = False
        spring_idx = None
        for i in range(st_idx + 1, n):
            if low[i] < sc_low - atr[i] * 0.5:
                spring_detected = True
                spring_idx = i
                break

        return {
            "phase": "accumulation",
            "confidence": 0.7 if spring_detected else 0.5,
            "sc_price": float(sc_close),
            "sc_idx": int(sc_idx),
            "ar_high": float(ar_high),
            "spring_detected": spring_detected,
            "spring_idx": spring_idx,
        }

    def _detect_distribution(self, close: np.ndarray, high: np.ndarray, low: np.ndarray, vol: np.ndarray, atr: np.ndarray) -> Optional[Dict]:
        """Detect Wyckoff distribution phase."""
        n = len(close)
        avg_vol = np.mean(vol)

        trend = close[-1] - close[-self.lookback]
        if trend < 0:
            return None

        vol_surges = np.where(vol > avg_vol * self.vol_mult)[0]
        if len(vol_surges) < 2:
            return None

        window = min(30, n)
        lc_candidates = vol_surges[vol_surges >= n - window]
        if len(lc_candidates) == 0:
            return None
        lc_idx = lc_candidates[np.argmax(vol[lc_candidates])]
        lc_high = high[lc_idx]
        lc_low = low[lc_idx]

        # Automatic decline (AD) after LC
        if lc_idx + self.min_bars >= n:
            return None
        ad_down = close[lc_idx+1] < close[lc_idx]
        if not ad_down:
            return None

        # Secondary Test (ST) — revisit LC area
        st_idx = min(lc_idx + self.min_bars + 3, n - 1)
        st_high = high[st_idx]
        st_vol = vol[st_idx]
        near_lc = abs(st_high - lc_high) / lc_high < 0.02
        lower_vol = st_vol < vol[lc_idx] * 0.7
        if not (near_lc and lower_vol):
            return None

        # Check for Upthrust (UT) — final distribution signal
        ut_detected = False
        for i in range(st_idx + 1, n):
            if high[i] > lc_high + atr[i] * 0.5:
                ut_detected = True
                break

        return {
            "phase": "distribution",
            "confidence": 0.7 if ut_detected else 0.5,
            "lc_price": float(lc_high),
            "lc_idx": int(lc_idx),
            "ut_detected": ut_detected,
        }

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        close = data["close"].values
        high = data["high"].values
        low = data["low"].values
        vol = data["volume"].values
        atr = self.compute_atr(data["high"], data["low"], data["close"]).values

        acc = self._detect_accumulation(close, high, low, vol, atr)
        dist = self._detect_distribution(close, high, low, vol, atr)

        latest_price = float(close[-1])
        atr_val = float(atr[-1])

        if acc and acc["confidence"] >= 0.5:
            sl = float(low[acc["sc_idx"]]) * 0.99 if acc["spring_detected"] else latest_price - atr_val * 2
            return Signal(
                symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.BUY,
                confidence=acc["confidence"],
                price=latest_price,
                stop_loss=sl,
                take_profit=latest_price + atr_val * 4,
                source_strategy=self.name,
                reasoning=f"Wyckoff accumulation: SC={acc['sc_price']:.2f} spring={'yes' if acc['spring_detected'] else 'no'} conf={acc['confidence']:.0%}",
            )

        if dist and dist["confidence"] >= 0.5:
            tp = float(low[dist["lc_idx"]]) * 0.98
            return Signal(
                symbol=str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN",
                signal_type=SignalType.SELL,
                confidence=dist["confidence"],
                price=latest_price,
                stop_loss=latest_price + atr_val * 2,
                take_profit=tp,
                source_strategy=self.name,
                reasoning=f"Wyckoff distribution: LC={dist['lc_price']:.2f} upthrust={'yes' if dist['ut_detected'] else 'no'} conf={dist['confidence']:.0%}",
            )

        return None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(params={self.params})"
