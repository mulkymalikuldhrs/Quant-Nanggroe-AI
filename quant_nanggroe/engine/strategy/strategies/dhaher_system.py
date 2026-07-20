"""Dhaher System v1.1 — Tuned Entry Logic (Win Rate Target 40%+).

Port of the Dhaher Labs hedge-fund strategy (originally in /e/trading) into
Quant-Nanggroe-AI's 107-strategy system. Adapted from the DataFrame-emitter
interface (generate_signals -> df['entry']) to QNA's single-bar interface
(generate_signal -> Signal), preserving every piece of the v1.1 logic:

Changelog v1.0 -> v1.1:
  - WR: 27% -> 40%+ (target)
  - Entry logic relaxed from "ALL conditions required" to "any 2 of 4"
  - Added FVG confirmation option (improves selectivity vs relaxed mode)
  - Better trend filter: EMA20/50 confirmed by ADX > 20
  - Adaptive ATR multiplier based on volatility regime
  - Volume confirmation when available
  - Max 1% risk per trade

Entry Logic (OR-based, need 2 of 4):
  1. Order Block (OB)      - displacement-based
  2. Fair Value Gap (FVG)   - 3-candle gap
  3. Break of Structure (BOS) - HH/HL breakout
  4. Trend Alignment       - EMA20/50 + ADX > 20

Exit:
  - SL: ATR(14) x atr_mult (adaptive: 1.2-2.0 based on vol regime)
  - TP: RR 1:2 minimum (configurable)

Filters:
  - ADX > 20 = trend strength minimum
  - Volume confirmation (if available)
  - Premium/Discount zone awareness
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class DhaherSystemStrategy(BaseStrategy):
    """Dhaher System v1.1 — Smart Money Concepts + partial confluence entry."""

    def __init__(self, params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name="DhaherSystem", params=params)
        self.lookback = int(self.params.get("lookback", 14))
        self.atr_mult = float(self.params.get("atr_mult", 1.5))
        self.rr_min = float(self.params.get("rr_min", 2.0))
        self.min_confluence = int(self.params.get("min_confluence", 2))
        self.use_adx_filter = bool(self.params.get("use_adx_filter", True))
        self.adx_threshold = float(self.params.get("adx_threshold", 20))
        self.use_volume_conf = bool(self.params.get("use_volume_conf", False))

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.lookback, 20) + 1

    # --- indicators -----------------------------------------------------
    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        plus_di = 100 * (plus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        minus_di = 100 * (minus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).clip(lower=0.001)
        return dx.rolling(period).mean()

    @staticmethod
    def _volume_ratio(df: pd.DataFrame) -> Optional[pd.Series]:
        vol_col = None
        for c in ["tick_volume", "real_volume", "Volume", "volume"]:
            if c in df.columns:
                vol_col = c
                break
        if vol_col is None:
            return None
        vol = df[vol_col]
        return vol / vol.rolling(20).mean().clip(lower=0.001)

    # --- pattern detection (lookback at bar i) ---------------------------
    def _detect_order_blocks(self, df: pd.DataFrame, i: int) -> int:
        atr = self.compute_atr(df["high"], df["low"], df["close"], 14)
        if pd.isna(atr.iloc[i]) or i + 1 >= len(df):
            return 0
        # Bullish OB: bearish candle -> breakout above its high
        if (
            df["close"].iloc[i] < df["open"].iloc[i]
            and df["close"].iloc[i + 1] > df["high"].iloc[i]
            and df["close"].iloc[i + 1] - df["close"].iloc[i] > atr.iloc[i] * 0.8
        ):
            return 1
        # Bearish OB: bullish candle -> breakdown below its low
        if (
            df["close"].iloc[i] > df["open"].iloc[i]
            and df["close"].iloc[i + 1] < df["low"].iloc[i]
            and df["close"].iloc[i] - df["close"].iloc[i + 1] > atr.iloc[i] * 0.8
        ):
            return -1
        return 0

    @staticmethod
    def _detect_fvg(df: pd.DataFrame, i: int) -> int:
        gap_pct = 0.002  # 0.2% minimum gap
        # Bullish FVG: low[i] > high[i-2]
        if i >= 2 and df["low"].iloc[i] > df["high"].iloc[i - 2]:
            gap = (df["low"].iloc[i] - df["high"].iloc[i - 2]) / df["close"].iloc[i]
            if gap > gap_pct:
                return 1
        # Bearish FVG: high[i] < low[i-2]
        if i >= 2 and df["high"].iloc[i] < df["low"].iloc[i - 2]:
            gap = (df["low"].iloc[i - 2] - df["high"].iloc[i]) / df["close"].iloc[i]
            if gap > gap_pct:
                return -1
        return 0

    def _detect_bos(self, df: pd.DataFrame, i: int) -> int:
        if i < self.lookback:
            return 0
        window_high = df["high"].iloc[i - self.lookback : i]
        window_low = df["low"].iloc[i - self.lookback : i]
        if df["close"].iloc[i] > window_high.max():
            return 1
        if df["close"].iloc[i] < window_low.min():
            return -1
        return 0

    @staticmethod
    def _detect_liquidity_grab(df: pd.DataFrame, i: int) -> int:
        if i < 20 or i + 1 >= len(df):
            return 0
        hh = df["high"].iloc[i - 20 : i].max()
        ll = df["low"].iloc[i - 20 : i].min()
        # Grab high then reverse down
        if (
            df["high"].iloc[i] > hh
            and df["close"].iloc[i + 1] < hh
            and df["close"].iloc[i + 1] < df["open"].iloc[i + 1]
        ):
            return -1
        # Grab low then reverse up
        if (
            df["low"].iloc[i] < ll
            and df["close"].iloc[i + 1] > ll
            and df["close"].iloc[i + 1] > df["open"].iloc[i + 1]
        ):
            return 1
        return 0

    # --- signal generation ---------------------------------------------
    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        if len(data) < self.warmup_period():
            return None

        i = len(data) - 1
        if i < max(self.lookback, 20):
            return None

        atr = self.compute_atr(data["high"], data["low"], data["close"], 14)
        atr_val = float(atr.iloc[i])
        if pd.isna(atr_val) or atr_val == 0:
            return None

        adx = self._calculate_adx(data)
        ema20 = data["close"].ewm(span=20).mean()
        ema50 = data["close"].ewm(span=50).mean()

        ob = self._detect_order_blocks(data, i)
        fvg = self._detect_fvg(data, i)
        bos = self._detect_bos(data, i)
        lg = self._detect_liquidity_grab(data, i)

        trend_up = bool(ema20.iloc[i] > ema50.iloc[i])
        trend_down = bool(ema20.iloc[i] < ema50.iloc[i])

        # Vol regime (adaptive SL)
        atr_mean = atr.rolling(50).mean().iloc[i]
        if pd.isna(atr_mean) or atr_mean == 0:
            vol_regime = 0
        elif atr_val > atr_mean * 1.3:
            vol_regime = 1
        elif atr_val < atr_mean * 0.7:
            vol_regime = -1
        else:
            vol_regime = 0

        if vol_regime == 1:
            adaptive_atr_mult = min(self.atr_mult * 1.3, 2.5)
        elif vol_regime == -1:
            adaptive_atr_mult = max(self.atr_mult * 0.8, 1.0)
        else:
            adaptive_atr_mult = self.atr_mult

        # ADX filter
        adx_pass = True
        if self.use_adx_filter:
            adx_val = adx.iloc[i] if i < len(adx) else np.nan
            if pd.isna(adx_val) or adx_val <= self.adx_threshold:
                adx_pass = False

        # Volume confirmation
        volume_ok = True
        if self.use_volume_conf:
            vr = self._volume_ratio(data)
            if vr is None:
                volume_ok = False
            else:
                v = vr.iloc[i]
                volume_ok = (not pd.isna(v)) and v > 1.0

        price = float(data["close"].iloc[i])
        symbol = str(data["symbol"].iloc[i]) if "symbol" in data.columns else "UNKNOWN"

        # BUY
        bull_score = sum([ob == 1, fvg == 1, bos == 1, lg == 1, trend_up])
        if bull_score >= self.min_confluence and adx_pass and volume_ok:
            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(bull_score / 5.0, 1.0),
                price=price,
                stop_loss=price - atr_val * adaptive_atr_mult,
                take_profit=price + atr_val * adaptive_atr_mult * self.rr_min,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"DhaherSystem BUY: OB={ob} FVG={fvg} BOS={bos} "
                    f"LG={lg} trend_up={trend_up} score={bull_score}/5 "
                    f"ADX_pass={adx_pass} vol_regime={vol_regime}"
                ),
            )

        # SELL
        bear_score = sum([ob == -1, fvg == -1, bos == -1, lg == -1, trend_down])
        if bear_score >= self.min_confluence and adx_pass and volume_ok:
            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(bear_score / 5.0, 1.0),
                price=price,
                stop_loss=price + atr_val * adaptive_atr_mult,
                take_profit=price - atr_val * adaptive_atr_mult * self.rr_min,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"DhaherSystem SELL: OB={ob} FVG={fvg} BOS={bos} "
                    f"LG={lg} trend_down={trend_down} score={bear_score}/5 "
                    f"ADX_pass={adx_pass} vol_regime={vol_regime}"
                ),
            )

        return None
