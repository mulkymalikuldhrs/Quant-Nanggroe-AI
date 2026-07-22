"""TradeBobby SMC Scanner — canonical QNA engine migration.

Migrated from ``E:/trading/strategies/tradebobby_smc_scanner.py`` (also in
legacy ``quant_nanggroe/engine/strategies/tradebobby_smc_scanner.py``),
adapted from the HF ``generate_signals(df) -> df`` interface to the QNA
``BaseStrategy.generate_signal(df) -> Optional[Signal]`` interface.

The Smart Money Concepts detection engine (order blocks, FVG, BOS/CHoCH,
liquidity sweeps, premium/discount zones, confluence scoring) is ported
verbatim from the original.  ``generate_signal`` runs the pipeline and emits a
single Signal for the last bar when confluence is satisfied.

Dependencies: pandas / numpy / enum (standard).
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class SMCPattern(Enum):
    OB = "order_block"
    FVG = "fair_value_gap"
    BOS = "break_of_structure"
    CHOCH = "change_of_character"
    LIQ_SWEEP = "liquidity_sweep"
    PREMIUM = "premium_zone"
    DISCOUNT = "discount_zone"
    BREAKER = "breaker_block"
    IFVG = "inverse_fvg"


class TradeBobbySMCPatterns:
    """TradeBobby SMC pattern detector (ported from Pro_Trading_System_V5.pine)."""

    def __init__(
        self,
        swing_lookback: int = 5,
        fvg_min_pct: float = 0.3,
        ob_displacement: float = 1.5,
        liq_tolerance: float = 0.3,
        min_confluence: int = 3,
    ):
        self.swing_lookback = swing_lookback
        self.fvg_min_pct = fvg_min_pct / 100.0
        self.ob_displacement = ob_displacement
        self.liq_tolerance = liq_tolerance / 100.0
        self.min_confluence = min_confluence

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean()

    def swing_highs_lows(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["swing_high"] = False
        df["swing_low"] = False
        df["swing_type"] = ""
        half_lb = self.swing_lookback // 2
        for i in range(half_lb, len(df) - half_lb):
            if df["high"].iloc[i] == df["high"].iloc[i - half_lb : i + half_lb + 1].max():
                df.loc[df.index[i], "swing_high"] = True
            if df["low"].iloc[i] == df["low"].iloc[i - half_lb : i + half_lb + 1].min():
                df.loc[df.index[i], "swing_low"] = True
        last_high_idx = last_low_idx = None
        for i in range(len(df)):
            if df["swing_high"].iloc[i]:
                if last_high_idx is not None:
                    if df["high"].iloc[i] > df["high"].iloc[last_high_idx]:
                        df.loc[df.index[i], "swing_type"] = "HH"
                    else:
                        df.loc[df.index[i], "swing_type"] = "LH"
                else:
                    df.loc[df.index[i], "swing_type"] = "HH"
                last_high_idx = i
            if df["swing_low"].iloc[i]:
                if last_low_idx is not None:
                    if df["low"].iloc[i] > df["low"].iloc[last_low_idx]:
                        df.loc[df.index[i], "swing_type"] = "HL"
                    else:
                        df.loc[df.index[i], "swing_type"] = "LL"
                else:
                    df.loc[df.index[i], "swing_type"] = "HL"
                last_low_idx = i
        return df

    def detect_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ob_signal"] = 0
        df["ob_strength"] = 0.0
        atr = self._calculate_atr(df)
        for i in range(2, len(df) - 1):
            if pd.isna(atr.iloc[i]):
                continue
            displacement = atr.iloc[i] * self.ob_displacement
            if (
                df["close"].iloc[i] < df["open"].iloc[i]
                and df["close"].iloc[i + 1] > df["high"].iloc[i]
                and df["close"].iloc[i + 1] - df["close"].iloc[i] > displacement
            ):
                df.loc[df.index[i], "ob_signal"] = 1
                strength = (df["close"].iloc[i + 1] - df["close"].iloc[i]) / atr.iloc[i]
                df.loc[df.index[i], "ob_strength"] = min(strength / self.ob_displacement, 3.0)
            elif (
                df["close"].iloc[i] > df["open"].iloc[i]
                and df["close"].iloc[i + 1] < df["low"].iloc[i]
                and df["close"].iloc[i] - df["close"].iloc[i + 1] > displacement
            ):
                df.loc[df.index[i], "ob_signal"] = -1
                strength = (df["close"].iloc[i] - df["close"].iloc[i + 1]) / atr.iloc[i]
                df.loc[df.index[i], "ob_strength"] = min(strength / self.ob_displacement, 3.0)
        return df

    def detect_fvg(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["fvg_signal"] = 0
        for i in range(2, len(df)):
            if df["low"].iloc[i] > df["high"].iloc[i - 2]:
                gap = (df["low"].iloc[i] - df["high"].iloc[i - 2]) / df["close"].iloc[i]
                if gap >= self.fvg_min_pct:
                    df.loc[df.index[i], "fvg_signal"] = 1
            elif df["high"].iloc[i] < df["low"].iloc[i - 2]:
                gap = (df["low"].iloc[i - 2] - df["high"].iloc[i]) / df["close"].iloc[i]
                if gap >= self.fvg_min_pct:
                    df.loc[df.index[i], "fvg_signal"] = -1
        return df

    def detect_bos_choch(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["bos_signal"] = 0
        df["choch_signal"] = 0
        swing_df = self.swing_highs_lows(df)
        last_hh_idx = last_ll_idx = prev_hh_idx = prev_ll_idx = None
        for i in range(self.swing_lookback, len(df)):
            if swing_df["swing_type"].iloc[i] == "HH":
                prev_hh_idx = last_hh_idx
                last_hh_idx = i
            elif swing_df["swing_type"].iloc[i] == "LL":
                prev_ll_idx = last_ll_idx
                last_ll_idx = i
            if last_hh_idx is not None and df["high"].iloc[i] > df["high"].iloc[last_hh_idx]:
                df.loc[df.index[i], "bos_signal"] = 1
            if last_ll_idx is not None and df["low"].iloc[i] < df["low"].iloc[last_ll_idx]:
                df.loc[df.index[i], "bos_signal"] = -1
            if last_hh_idx is not None and prev_hh_idx is not None:
                if (
                    swing_df["swing_type"].iloc[last_hh_idx] == "LH"
                    and swing_df["swing_type"].iloc[prev_hh_idx] == "HH"
                ):
                    df.loc[df.index[i], "choch_signal"] = -1
            if last_ll_idx is not None and prev_ll_idx is not None:
                if (
                    swing_df["swing_type"].iloc[last_ll_idx] == "HL"
                    and swing_df["swing_type"].iloc[prev_ll_idx] == "LL"
                ):
                    df.loc[df.index[i], "choch_signal"] = 1
        return df

    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["liq_sweep"] = 0
        df["liq_type"] = ""
        tolerance = self.liq_tolerance * df["close"].mean()
        for i in range(self.swing_lookback * 2, len(df) - 3):
            window = df.iloc[i - self.swing_lookback * 2 : i]
            recent_high = window["high"].max()
            recent_low = window["low"].min()
            if df["high"].iloc[i] > recent_high + tolerance and df["close"].iloc[i + 1] < recent_high:
                df.loc[df.index[i], "liq_sweep"] = -1
                df.loc[df.index[i], "liq_type"] = "buy_side"
            if df["low"].iloc[i] < recent_low - tolerance and df["close"].iloc[i + 1] > recent_low:
                df.loc[df.index[i], "liq_sweep"] = 1
                df.loc[df.index[i], "liq_type"] = "sell_side"
        return df

    def detect_premium_discount(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["zone"] = 0
        df["zone_pct"] = 50.0
        pd_lookback = max(self.swing_lookback * 10, 50)
        for i in range(pd_lookback, len(df)):
            window = df.iloc[i - pd_lookback : i]
            swing_high = window["high"].max()
            swing_low = window["low"].min()
            current_close = df["close"].iloc[i]
            if swing_high > swing_low:
                zone_pct = (current_close - swing_low) / (swing_high - swing_low) * 100
                df.loc[df.index[i], "zone_pct"] = zone_pct
                if zone_pct <= 30:
                    df.loc[df.index[i], "zone"] = 1
                elif zone_pct >= 70:
                    df.loc[df.index[i], "zone"] = -1
        return df

    def detect_all_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        swing_df = self.swing_highs_lows(df)
        ob_df = self.detect_order_blocks(df)
        fvg_df = self.detect_fvg(df)
        bos_df = self.detect_bos_choch(df)
        liq_df = self.detect_liquidity_sweeps(df)
        pd_df = self.detect_premium_discount(df)
        df["swing_high"] = swing_df["swing_high"]
        df["swing_low"] = swing_df["swing_low"]
        df["swing_type"] = swing_df["swing_type"]
        df["ob_signal"] = ob_df["ob_signal"]
        df["ob_strength"] = ob_df["ob_strength"]
        df["fvg_signal"] = fvg_df["fvg_signal"]
        df["bos_signal"] = bos_df["bos_signal"]
        df["choch_signal"] = bos_df["choch_signal"]
        df["liq_sweep"] = liq_df["liq_sweep"]
        df["liq_type"] = liq_df["liq_type"]
        df["zone"] = pd_df["zone"]
        df["zone_pct"] = pd_df["zone_pct"]
        return df

    def confluence_score(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["confluence_bull"] = 0
        df["confluence_bear"] = 0
        df["confluence_signal"] = 0
        for i in range(len(df)):
            bull_score = 0
            ob_val = df["ob_signal"].iloc[i]
            fvg_val = df["fvg_signal"].iloc[i]
            bos_val = df["bos_signal"].iloc[i]
            choch_val = df["choch_signal"].iloc[i]
            liq_val = df["liq_sweep"].iloc[i]
            zone_val = df["zone"].iloc[i]
            if ob_val == 1 and df["ob_strength"].iloc[i] > 1.0:
                bull_score += 1
            if fvg_val == 1:
                bull_score += 1
            if bos_val == 1:
                bull_score += 1
            if choch_val == 1:
                bull_score += 1
            if liq_val == 1:
                bull_score += 1
            if zone_val == 1:
                bull_score += 1
            bear_score = 0
            if ob_val == -1 and df["ob_strength"].iloc[i] > 1.0:
                bear_score += 1
            if fvg_val == -1:
                bear_score += 1
            if bos_val == -1:
                bear_score += 1
            if choch_val == -1:
                bear_score += 1
            if liq_val == -1:
                bear_score += 1
            if zone_val == -1:
                bear_score += 1
            df.loc[df.index[i], "confluence_bull"] = bull_score
            df.loc[df.index[i], "confluence_bear"] = bear_score
            if bull_score >= self.min_confluence and bull_score > bear_score:
                df.loc[df.index[i], "confluence_signal"] = 1
            elif bear_score >= self.min_confluence and bear_score > bull_score:
                df.loc[df.index[i], "confluence_signal"] = -1
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self.detect_all_patterns(df)
        df = self.confluence_score(df)
        df["entry"] = df["confluence_signal"]
        return df


class TradeBobbySMCStrategy(BaseStrategy):
    """TradeBobby SMC Strategy — Smart Money Concepts scanner + confluence engine."""

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="TradeBobbySMCStrategy", params=params)
        self.swing_lookback: int = int(self.params.get("swing_lookback", 5))
        self.min_confluence: int = int(self.params.get("min_confluence", 3))
        self.fvg_min_pct: float = float(self.params.get("fvg_min_pct", 0.3))
        self.ob_displacement: float = float(self.params.get("ob_displacement", 1.5))
        self.liq_tolerance: float = float(self.params.get("liq_tolerance", 0.3))
        self._scanner = TradeBobbySMCPatterns(
            swing_lookback=self.swing_lookback,
            min_confluence=self.min_confluence,
            fvg_min_pct=self.fvg_min_pct,
            ob_displacement=self.ob_displacement,
            liq_tolerance=self.liq_tolerance,
        )

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return max(self.swing_lookback * 2 + 3, 50)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        df = self._scanner.generate_signals(data)
        i = len(df) - 1
        sig = df["confluence_signal"].iloc[i]
        price = float(df["close"].iloc[i])
        bull = int(df["confluence_bull"].iloc[i])
        bear = int(df["confluence_bear"].iloc[i])
        if sig == 0:
            return None
        signal_type = SignalType.BUY if sig == 1 else SignalType.SELL
        confidence = round(min(0.5 + 0.1 * (bull if sig == 1 else bear), 0.95), 4)
        return Signal(
            symbol=self.name,
            signal_type=signal_type,
            confidence=confidence,
            price=round(price, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=f"TradeBobbySMC {'LONG' if sig == 1 else 'SHORT'} confluence_bull={bull} confluence_bear={bear}",
            evidence={
                "strategy": "tradebobby_smc",
                "confluence_bull": bull,
                "confluence_bear": bear,
                "min_confluence": self.min_confluence,
            },
            factors=["tradebobby_smc", "smc", "confluence"],
        )
