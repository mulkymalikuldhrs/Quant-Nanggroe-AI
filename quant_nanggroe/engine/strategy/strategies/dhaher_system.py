"""Dhaher System v1.1 — canonical QNA engine migration.

Migrated from ``E:/trading/strategies/dhaher_system.py`` (also present in the
legacy QNA package ``quant_nanggroe/engine/strategies/dhaher_system.py``).

The legacy module implemented the HF ``generate_signals(df) -> df`` interface
(returns a column ``entry``).  This canonical version implements the QNA
``BaseStrategy.generate_signal(df) -> Optional[Signal]`` interface: it runs the
same Smart-Money-Concepts confluence engine and emits a single ``Signal`` for
the most recent bar when confluence is met.

Interface contract (see ``base_strategy.py``):
    generate_signal(df) -> Optional[Signal]
    required_columns() -> List[str]
    warmup_period()    -> int

Dependencies: pandas / numpy only (no torch, no external model packages).
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class DhaherSystem(BaseStrategy):
    """Dhaher System v1.1 — Smart Money Concepts + partial-confluence entry.

    Entry logic (OR-based, need ``min_confluence`` of the following, default 2):
      1. Order Block (OB)     — displacement-based
      2. Fair Value Gap (FVG) — 3-candle gap
      3. Break of Structure (BOS) — HH/HL breakout
      4. Trend Alignment      — EMA20/50 + ADX > 20

    Exit:
      - SL: ATR(14) x atr_mult (adaptive 1.2-2.0 by volatility regime)
      - TP: RR 1:2 minimum (configurable)

    Filters: ADX > 20 trend strength, optional volume confirmation,
    premium/discount zone awareness.
    """

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="DhaherSystem", params=params)
        self.lookback: int = int(self.params.get("lookback", 14))
        self.atr_mult: float = float(self.params.get("atr_mult", 1.5))
        self.rr_min: float = float(self.params.get("rr_min", 2.0))
        self.max_positions: int = int(self.params.get("max_positions", 3))
        self.risk_per_trade: float = float(self.params.get("risk_per_trade", 0.01))
        self.min_confluence: int = int(self.params.get("min_confluence", 2))
        self.use_adx_filter: bool = bool(self.params.get("use_adx_filter", True))
        self.adx_threshold: float = float(self.params.get("adx_threshold", 20))
        self.use_volume_conf: bool = bool(self.params.get("use_volume_conf", False))

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.lookback, 20) + 2

    # ------------------------------------------------------------------
    # Indicators (ported verbatim from legacy logic)
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.concat(
            [
                high - low,
                (high - close.shift(1)).abs(),
                (low - close.shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(period).mean()
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_di = 100 * (plus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        minus_di = 100 * (minus_dm.rolling(period).sum() / atr.clip(lower=0.001))
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).clip(lower=0.001)
        return dx.rolling(period).mean()

    def _calculate_volume_profile(self, df: pd.DataFrame):
        vol_col = None
        for c in ["tick_volume", "real_volume", "Volume", "volume"]:
            if c in df.columns:
                vol_col = c
                break
        if vol_col is None:
            return None, None
        vol = df[vol_col]
        vol_avg = vol.rolling(20).mean()
        vol_ratio = vol / vol_avg.clip(lower=0.001)
        return vol, vol_ratio

    def _detect_order_blocks(self, df: pd.DataFrame) -> pd.Series:
        ob = pd.Series(0, index=df.index)
        atr = self._calculate_atr(df)
        for i in range(2, len(df) - 1):
            if pd.isna(atr.iloc[i]):
                continue
            if (
                df["close"].iloc[i] < df["open"].iloc[i]
                and df["close"].iloc[i + 1] > df["high"].iloc[i]
                and df["close"].iloc[i + 1] - df["close"].iloc[i] > atr.iloc[i] * 0.8
            ):
                ob.iloc[i + 1] = 1
            elif (
                df["close"].iloc[i] > df["open"].iloc[i]
                and df["close"].iloc[i + 1] < df["low"].iloc[i]
                and df["close"].iloc[i] - df["close"].iloc[i + 1] > atr.iloc[i] * 0.8
            ):
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
            window_high = df["high"].iloc[i - self.lookback : i]
            window_low = df["low"].iloc[i - self.lookback : i]
            if df["close"].iloc[i] > window_high.max():
                bos.iloc[i] = 1
            elif df["close"].iloc[i] < window_low.min():
                bos.iloc[i] = -1
        return bos

    def _detect_liquidity_grab(self, df: pd.DataFrame) -> pd.Series:
        lg = pd.Series(0, index=df.index)
        for i in range(20, len(df) - 3):
            hh = df["high"].iloc[i - 20 : i].max()
            ll = df["low"].iloc[i - 20 : i].min()
            if (
                df["high"].iloc[i] > hh
                and df["close"].iloc[i + 1] < hh
                and df["close"].iloc[i + 1] < df["open"].iloc[i + 1]
            ):
                lg.iloc[i + 1] = -1
            if (
                df["low"].iloc[i] < ll
                and df["close"].iloc[i + 1] > ll
                and df["close"].iloc[i + 1] > df["open"].iloc[i + 1]
            ):
                lg.iloc[i + 1] = 1
        return lg

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        df = data.copy()
        df["atr"] = self._calculate_atr(df)
        df["adx"] = self._calculate_adx(df)
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        df["ob"] = self._detect_order_blocks(df)
        df["fvg"] = self._detect_fvg(df)
        df["bos"] = self._detect_bos(df)
        df["lg"] = self._detect_liquidity_grab(df)

        df["trend_up"] = (df["ema20"] > df["ema50"]).astype(int)
        df["trend_down"] = (df["ema20"] < df["ema50"]).astype(int)

        atr_mean = df["atr"].rolling(50).mean()
        df["vol_regime"] = 0
        df.loc[df["atr"] > atr_mean * 1.3, "vol_regime"] = 1
        df.loc[df["atr"] < atr_mean * 0.7, "vol_regime"] = -1

        _vol, df["vol_ratio"] = self._calculate_volume_profile(df)

        i = len(df) - 1
        if pd.isna(df["atr"].iloc[i]) or df["atr"].iloc[i] == 0:
            return None

        atr_val = float(df["atr"].iloc[i])
        vol_regime = int(df["vol_regime"].iloc[i])
        if vol_regime == 1:
            adaptive_atr_mult = min(self.atr_mult * 1.3, 2.5)
        elif vol_regime == -1:
            adaptive_atr_mult = max(self.atr_mult * 0.8, 1.0)
        else:
            adaptive_atr_mult = self.atr_mult

        if self.use_adx_filter:
            adx_pass = bool(df["adx"].iloc[i] > self.adx_threshold)
        else:
            adx_pass = True

        # Bullish confluence
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

        volume_ok = (not self.use_volume_conf) or (
            df["vol_ratio"].iloc[i] is not None
            and not pd.isna(df["vol_ratio"].iloc[i])
            and df["vol_ratio"].iloc[i] > 1.0
        )

        price = float(df["close"].iloc[i])
        if bull_score >= self.min_confluence and adx_pass and volume_ok:
            sl = round(price - atr_val * adaptive_atr_mult, 6)
            tp = round(price + atr_val * adaptive_atr_mult * self.rr_min, 6)
            confidence = round(min(0.55 + 0.09 * bull_score, 0.95), 4)
            return Signal(
                symbol=self.name,
                signal_type=SignalType.BUY,
                confidence=confidence,
                price=round(price, 6),
                stop_loss=sl,
                take_profit=tp,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"DhaherSystem LONG confluence={bull_score} "
                    f"adx_pass={adx_pass} vol_ok={volume_ok}"
                ),
                evidence={
                    "strategy": "dhaher_system",
                    "bull_score": bull_score,
                    "atr": round(atr_val, 6),
                    "adaptive_atr_mult": round(adaptive_atr_mult, 3),
                },
                factors=["dhaher_system", "smc", "confluence"],
            )

        # Bearish confluence
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

        if bear_score >= self.min_confluence and adx_pass and volume_ok:
            sl = round(price + atr_val * adaptive_atr_mult, 6)
            tp = round(price - atr_val * adaptive_atr_mult * self.rr_min, 6)
            confidence = round(min(0.55 + 0.09 * bear_score, 0.95), 4)
            return Signal(
                symbol=self.name,
                signal_type=SignalType.SELL,
                confidence=confidence,
                price=round(price, 6),
                stop_loss=sl,
                take_profit=tp,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"DhaherSystem SHORT confluence={bear_score} "
                    f"adx_pass={adx_pass} vol_ok={volume_ok}"
                ),
                evidence={
                    "strategy": "dhaher_system",
                    "bear_score": bear_score,
                    "atr": round(atr_val, 6),
                    "adaptive_atr_mult": round(adaptive_atr_mult, 3),
                },
                factors=["dhaher_system", "smc", "confluence"],
            )

        return None
