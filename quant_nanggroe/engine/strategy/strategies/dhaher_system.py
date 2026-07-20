"""Dhaher System v1.1 — SMC Partial Confluence Strategy.

Ported from E:\trading\strategies\dhaher_system.py and adapted for QNA's
BaseStrategy framework. This is the production-tuned version with:

- Partial confluence: need 2 of 4 patterns (not all 3 like strict SMC)
- ADX trend filter
- Adaptive ATR based on volatility regime
- Liquidity grab detection
- Volume confirmation option

Key insight from E:\trading: requiring ALL patterns simultaneously was too
restrictive (27% win rate). Partial confluence with 2/4 patterns targets 40%+
while maintaining strong risk-reward ratios.

References:
    - Dhaher, M. (2026). Dhaher System v1.1 — SMC + Price Action
    - ICT Smart Money Concepts
    - TradeBobby SMC patterns
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class DhaherSystemStrategy(BaseStrategy):
    """Dhaher System v1.1 — SMC partial confluence with ADX filter.

    Parameters:
        lookback (int): Window for BOS detection (default 14)
        atr_mult (float): ATR multiplier for SL (default 1.5, range 1.2-2.0)
        rr_min (float): Minimum risk-reward ratio (default 2.0)
        min_confluence (int): Minimum patterns for entry (default 2 of 5)
        use_adx_filter (bool): Enable ADX trend filter (default True)
        adx_threshold (int): Minimum ADX value (default 20)
        use_volume_conf (bool): Volume confirmation (default False)
    """

    def __init__(self, name: str = "DhaherSystem", params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name, params)
        self.lookback = params.get("lookback", 14)
        self.atr_mult = params.get("atr_mult", 1.5)
        self.rr_min = params.get("rr_min", 2.0)
        self.min_confluence = params.get("min_confluence", 2)
        self.use_adx_filter = params.get("use_adx_filter", True)
        self.adx_threshold = params.get("adx_threshold", 20)
        self.use_volume_conf = params.get("use_volume_conf", False)

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.lookback, 50)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate signal using partial confluence SMC logic."""
        if len(data) < self.warmup_period():
            return None

        df = data.copy()

        # Indicators
        df["atr"] = self._calc_atr(df)
        df["adx"] = self._calc_adx(df)
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        # Patterns
        df["ob"] = self._detect_order_blocks(df)
        df["fvg"] = self._detect_fvg(df)
        df["bos"] = self._detect_bos(df)
        df["lg"] = self._detect_liquidity_grab(df)

        # Trend
        df["trend_up"] = (df["ema20"] > df["ema50"]).astype(int)
        df["trend_down"] = (df["ema20"] < df["ema50"]).astype(int)

        # Vol regime
        atr_mean = df["atr"].rolling(50).mean()
        df["vol_regime"] = 0
        df.loc[df["atr"] > atr_mean * 1.3, "vol_regime"] = 1
        df.loc[df["atr"] < atr_mean * 0.7, "vol_regime"] = -1

        # Check last bar
        i = len(df) - 1
        if pd.isna(df["atr"].iloc[i]) or df["atr"].iloc[i] == 0:
            return None

        atr_val = df["atr"].iloc[i]
        vol_regime = df["vol_regime"].iloc[i]

        # Adaptive SL
        if vol_regime == 1:
            adaptive_mult = min(self.atr_mult * 1.3, 2.5)
        elif vol_regime == -1:
            adaptive_mult = max(self.atr_mult * 0.8, 1.0)
        else:
            adaptive_mult = self.atr_mult

        # ADX check
        if self.use_adx_filter and df["adx"].iloc[i] < self.adx_threshold:
            return None

        # BUY score
        bull_score = 0
        if df["ob"].iloc[i] == 1:
            bull_score += 1
        if df["fvg"].iloc[i] == 1:
            bull_score += 1
        if df["bos"].iloc[i] == 1:
            bull_score += 1
        if df["lg"].iloc[i] == 1:
            bull_score += 1
        if df["trend_up"].iloc[i]:
            bull_score += 1

        if bull_score >= self.min_confluence:
            sl = df["close"].iloc[i] - atr_val * adaptive_mult
            tp = df["close"].iloc[i] + atr_val * adaptive_mult * self.rr_min
            confidence = min(0.3 + bull_score * 0.12, 0.95)
            return Signal(
                signal_type=SignalType.BUY,
                symbol=data.attrs.get("symbol", ""),
                price=float(df["close"].iloc[i]),
                stop_loss=float(sl),
                take_profit=float(tp),
                confidence=confidence,
                metadata={
                    "strategy": self.name,
                    "confluence_score": bull_score,
                    "adaptive_mult": round(adaptive_mult, 3),
                    "vol_regime": vol_regime,
                },
            )

        # SELL score
        bear_score = 0
        if df["ob"].iloc[i] == -1:
            bear_score += 1
        if df["fvg"].iloc[i] == -1:
            bear_score += 1
        if df["bos"].iloc[i] == -1:
            bear_score += 1
        if df["lg"].iloc[i] == -1:
            bear_score += 1
        if df["trend_down"].iloc[i]:
            bear_score += 1

        if bear_score >= self.min_confluence:
            sl = df["close"].iloc[i] + atr_val * adaptive_mult
            tp = df["close"].iloc[i] - atr_val * adaptive_mult * self.rr_min
            confidence = min(0.3 + bear_score * 0.12, 0.95)
            return Signal(
                signal_type=SignalType.SELL,
                symbol=data.attrs.get("symbol", ""),
                price=float(df["close"].iloc[i]),
                stop_loss=float(sl),
                take_profit=float(tp),
                confidence=confidence,
                metadata={
                    "strategy": self.name,
                    "confluence_score": bear_score,
                    "adaptive_mult": round(adaptive_mult, 3),
                    "vol_regime": vol_regime,
                },
            )

        return None

    # ── Internal detectors ──────────────────────────────────────────

    def _calc_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def _calc_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_dm = high.diff().clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        plus_di = 100 * (plus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        minus_di = 100 * (minus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).clip(lower=0.001)
        return dx.rolling(period).mean()

    def _detect_order_blocks(self, df: pd.DataFrame) -> pd.Series:
        ob = pd.Series(0, index=df.index)
        atr = self._calc_atr(df)
        for i in range(2, len(df) - 1):
            if pd.isna(atr.iloc[i]):
                continue
            if (df["close"].iloc[i] < df["open"].iloc[i]
                    and df["close"].iloc[i + 1] > df["high"].iloc[i]
                    and df["close"].iloc[i + 1] - df["close"].iloc[i] > atr.iloc[i] * 0.8):
                ob.iloc[i + 1] = 1
            elif (df["close"].iloc[i] > df["open"].iloc[i]
                  and df["close"].iloc[i + 1] < df["low"].iloc[i]
                  and df["close"].iloc[i] - df["close"].iloc[i + 1] > atr.iloc[i] * 0.8):
                ob.iloc[i + 1] = -1
        return ob

    def _detect_fvg(self, df: pd.DataFrame) -> pd.Series:
        fvg = pd.Series(0, index=df.index)
        gap_pct = 0.002
        for i in range(2, len(df)):
            if df["low"].iloc[i] > df["high"].iloc[i - 2]:
                gap = (df["low"].iloc[i] - df["high"].iloc[i - 2]) / df["close"].iloc[i]
                if gap > gap_pct:
                    fvg.iloc[i] = 1
            if df["high"].iloc[i] < df["low"].iloc[i - 2]:
                gap = (df["low"].iloc[i - 2] - df["high"].iloc[i]) / df["close"].iloc[i]
                if gap > gap_pct:
                    fvg.iloc[i] = -1
        return fvg

    def _detect_bos(self, df: pd.DataFrame) -> pd.Series:
        bos = pd.Series(0, index=df.index)
        for i in range(self.lookback, len(df)):
            wh = df["high"].iloc[i - self.lookback:i].max()
            wl = df["low"].iloc[i - self.lookback:i].min()
            if df["close"].iloc[i] > wh:
                bos.iloc[i] = 1
            elif df["close"].iloc[i] < wl:
                bos.iloc[i] = -1
        return bos

    def _detect_liquidity_grab(self, df: pd.DataFrame) -> pd.Series:
        lg = pd.Series(0, index=df.index)
        for i in range(20, len(df) - 3):
            hh = df["high"].iloc[i - 20:i].max()
            ll = df["low"].iloc[i - 20:i].min()
            if (df["high"].iloc[i] > hh
                    and df["close"].iloc[i + 1] < hh
                    and df["close"].iloc[i + 1] < df["open"].iloc[i + 1]):
                lg.iloc[i + 1] = -1
            if (df["low"].iloc[i] < ll
                    and df["close"].iloc[i + 1] > ll
                    and df["close"].iloc[i + 1] > df["open"].iloc[i + 1]):
                lg.iloc[i + 1] = 1
        return lg
