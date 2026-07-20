"""Smart Money Concepts (SMC) trading strategy.

Implements institutional order-flow concepts developed by
Michael Huddleston ("Inner Circle Trader"):

- Order Blocks (OB) — consolidation zones before major moves where
  institutional orders were absorbed
- Liquidity Sweeps — false-breakouts above swing highs or below
  swing lows designed to trigger retail stop-losses
- Fair Value Gaps (FVG) — price inefficiencies between candle
  bodies where price tends to return
- Market Structure Shifts (MSS / CHOCH) — break of structure
  indicating trend reversal

Signals require min_confluence patterns to align before entering.

References:
    - Huddleston, M. "Inner Circle Trader" (ICT) concepts.
    - "Smart Money Concepts" — institutional FX methodology adapted
      from ICT and Wyckoff principles.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class SMCStrategy(BaseStrategy):
    """Smart Money Concept strategy using ICT concepts.

    Detects order blocks, liquidity sweeps, fair value gaps (FVG),
    and market structure shifts to generate entry signals.

    Parameters:
        min_confluence (int): Minimum SMC patterns required for signal (default 2)
        sl_atr_mult (float): Stop loss as ATR multiple (default 1.5)
        tp_atr_mult (float): Take profit as ATR multiple (default 3.0)
    """

    def __init__(self, params: Optional[Dict] = None):
        params = params or {}
        super().__init__(name="SMC", params=params)
        self.min_confluence = self.params.get("min_confluence", 2)
        self.sl_atr_mult = self.params.get("sl_atr_mult", 1.5)
        self.tp_atr_mult = self.params.get("tp_atr_mult", 3.0)

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return 20

    def _detect_order_blocks(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"].values
        ob_signal = np.zeros(len(data))
        for i in range(2, len(data)):
            if close[i - 1] > close[i - 2] and close[i] < close[i - 1]:
                ob_signal[i] = -1
            elif close[i - 1] < close[i - 2] and close[i] > close[i - 1]:
                ob_signal[i] = 1
        return pd.Series(ob_signal, index=data.index)

    def _detect_liquidity(self, data: pd.DataFrame) -> pd.Series:
        high = data["high"].values
        low = data["low"].values
        liq = np.zeros(len(data))
        for i in range(5, len(data)):
            if high[i] > np.max(high[i - 5:i]):
                liq[i] = -1
            if low[i] < np.min(low[i - 5:i]):
                liq[i] = 1
        return pd.Series(liq, index=data.index)

    def _detect_fvg(self, data: pd.DataFrame) -> pd.DataFrame:
        high = data["high"].values
        low = data["low"].values
        fvg = np.zeros(len(data))
        fvg_type = np.full(len(data), "", dtype=object)

        for i in range(2, len(data)):
            if low[i - 2] > high[i]:
                fvg[i - 1] = 1
                fvg_type[i - 1] = "bullish"
            elif high[i - 2] < low[i]:
                fvg[i - 1] = -1
                fvg_type[i - 1] = "bearish"

        return pd.DataFrame({"fvg": fvg, "fvg_type": fvg_type}, index=data.index)

    def _detect_market_structure(self, data: pd.DataFrame) -> pd.DataFrame:
        high = data["high"].values
        low = data["low"].values
        ms = np.zeros(len(data))
        ms_type = np.full(len(data), "", dtype=object)

        for i in range(2, len(data)):
            if high[i] > high[i - 1] or low[i] > low[i - 1]:
                ms[i] = 1
                ms_type[i] = "bullish"
            elif high[i] < high[i - 1] or low[i] < low[i - 1]:
                ms[i] = -1
                ms_type[i] = "bearish"

        return pd.DataFrame({"ms": ms, "ms_type": ms_type}, index=data.index)

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        close = data["close"].values
        high = data["high"].values
        low = data["low"].values

        obs = self._detect_order_blocks(data).values
        liq = self._detect_liquidity(data).values
        fvg_df = self._detect_fvg(data)
        fvg = fvg_df["fvg"].values
        ms_df = self._detect_market_structure(data)
        ms = ms_df["ms"].values

        # ATR for SL/TP
        atr = self.compute_atr(data["high"], data["low"], data["close"]).values

        latest_ob = obs[-1]
        latest_liq = liq[-1]
        latest_fvg = fvg[-1]
        latest_ms = ms[-1]

        buy_score = sum([
            1 if latest_ob == 1 else 0,
            1 if latest_liq == 1 else 0,
            1 if latest_fvg == 1 else 0,
            1 if latest_ms == 1 else 0,
        ])
        sell_score = sum([
            1 if latest_ob == -1 else 0,
            1 if latest_liq == -1 else 0,
            1 if latest_fvg == -1 else 0,
            1 if latest_ms == -1 else 0,
        ])

        latest_price = float(close[-1])
        sl_atr = float(atr[-1] * self.sl_atr_mult)
        tp_atr = float(atr[-1] * self.tp_atr_mult)
        symbol = str(data["symbol"].iloc[-1]) if "symbol" in data.columns else "UNKNOWN"

        if buy_score >= self.min_confluence:
            return Signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=min(buy_score / 4.0, 1.0),
                price=latest_price,
                stop_loss=latest_price - sl_atr,
                take_profit=latest_price + tp_atr,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"SMC BUY: OB={latest_ob} Liq={latest_liq} "
                    f"FVG={latest_fvg} MS={latest_ms} score={buy_score}/4"
                ),
            )
        elif sell_score >= self.min_confluence:
            return Signal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=min(sell_score / 4.0, 1.0),
                price=latest_price,
                stop_loss=latest_price + sl_atr,
                take_profit=latest_price - tp_atr,
                source_agent=self.name,
                source_strategy=self.name,
                reasoning=(
                    f"SMC SELL: OB={latest_ob} Liq={latest_liq} "
                    f"FVG={latest_fvg} MS={latest_ms} score={sell_score}/4"
                ),
            )

        return None
