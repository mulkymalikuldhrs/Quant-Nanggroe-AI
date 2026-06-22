"""Multi-timeframe strategy alignment.

Aligns trading signals across higher (D1), medium (H1), and lower (M5) timeframes.
HTF sets the trend direction, MTF confirms alignment, LTF provides entry timing.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType


class TimeframeConfig:
    """Configuration for a single timeframe level."""

    def __init__(self, name: str, bars: int, weight: float = 1.0):
        self.name = name
        self.bars = bars
        self.weight = weight

    def __repr__(self) -> str:
        return f"TF({self.name}, {self.bars}b, w={self.weight})"


class MultiTimeframeStrategy:
    """Wraps a strategy and aligns signals across multiple timeframes.

    HTF (Higher Timeframe, e.g. D1): Sets the trend direction.
    MTF (Medium Timeframe, e.g. H1): Confirms trend alignment.
    LTF (Lower Timeframe, e.g. M5): Entry timing.

    Usage:
        mtf = MultiTimeframeStrategy(
            strategy=my_strategy,
            htf_data=daily_df,
            mtf_data=hourly_df,
            ltf_data=min5_df,
        )
        signal = mtf.align_signals()
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        htf_data: pd.DataFrame,
        mtf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
        htf_bars: int = 20,
        mtf_bars: int = 40,
        ltf_bars: int = 60,
        require_alignment: str = "all",
    ):
        self.strategy = strategy
        self.htf = htf_data
        self.mtf = mtf_data
        self.ltf = ltf_data
        self.htf_bars = htf_bars
        self.mtf_bars = mtf_bars
        self.ltf_bars = ltf_bars
        # 'all': all 3 must align, 'htf_mtf': HTF+MTF, 'htf': HTF only
        self.require_alignment = require_alignment

    def _detect_trend(self, data: pd.DataFrame, bars: int) -> str:
        """Detect trend direction using SMA slope."""
        if data is None or len(data) < bars:
            return "neutral"
        close = data["close"].values
        sma = pd.Series(close).rolling(bars).mean().values
        if len(sma) < 2:
            return "neutral"
        slope = (sma[-1] - sma[-bars//2]) / sma[-bars//2] if sma[-bars//2] > 0 else 0
        if slope > 0.01:
            return "bullish"
        elif slope < -0.01:
            return "bearish"
        return "neutral"

    def _detect_volatility(self, data: pd.DataFrame, bars: int) -> str:
        """Detect volatility regime."""
        if data is None or len(data) < bars:
            return "normal"
        close = data["close"].values
        returns = np.diff(close[-bars:]) / close[-bars:-1]
        vol = np.std(returns)
        if vol > np.mean(returns) * 3:
            return "high"
        return "normal"

    def _htf_filter(self, trend: str) -> bool:
        """HTF only allows trades in trend direction."""
        return trend != "neutral"

    def _mtf_filter(self, htf_trend: str, mtf_trend: str) -> bool:
        """MTF must align with HTF or be neutral."""
        if self.require_alignment == "htf":
            return True
        if mtf_trend == "neutral":
            return True
        return mtf_trend == htf_trend

    def _ltf_filter(self, htf_trend: str, mtf_trend: str, ltf_signal: Signal) -> bool:
        """LTF signal must be in the direction of HTF/MTF trend."""
        if self.require_alignment == "htf":
            return True
        if ltf_signal is None:
            return False
        buy_allowed = htf_trend in ("bullish", "neutral") and mtf_trend in ("bullish", "neutral")
        sell_allowed = htf_trend in ("bearish", "neutral") and mtf_trend in ("bearish", "neutral")
        if ltf_signal.signal_type in (SignalType.BUY, SignalType.CLOSE_SHORT):
            return buy_allowed
        elif ltf_signal.signal_type in (SignalType.SELL, SignalType.CLOSE_LONG):
            return sell_allowed
        return True

    def _adjust_confidence(self, ltf_signal: Signal, htf_trend: str, mtf_trend: str, vol: str) -> float:
        """Adjust signal confidence based on alignment."""
        base = ltf_signal.confidence
        if htf_trend == "bullish" and ltf_signal.signal_type in (SignalType.BUY, SignalType.CLOSE_SHORT):
            base += 0.15
        elif htf_trend == "bearish" and ltf_signal.signal_type in (SignalType.SELL, SignalType.CLOSE_LONG):
            base += 0.15
        if mtf_trend == htf_trend:
            base += 0.1
        if vol == "high":
            base -= 0.15
        return min(base, 0.95)

    def align_signals(self) -> Optional[Signal]:
        """Generate multi-timeframe aligned signal."""
        htf_trend = self._detect_trend(self.htf, self.htf_bars)
        mtf_trend = self._detect_trend(self.mtf, self.mtf_bars)
        vol = self._detect_volatility(self.ltf, self.ltf_bars)

        # Generate LTF signal using the strategy
        ltf_signal = self.strategy.generate_signal(self.ltf)

        if ltf_signal is None:
            return None

        # Apply filters
        if not self._htf_filter(htf_trend):
            return None
        if not self._mtf_filter(htf_trend, mtf_trend):
            return None
        if not self._ltf_filter(htf_trend, mtf_trend, ltf_signal):
            return None

        # Adjust confidence
        ltf_signal.confidence = self._adjust_confidence(ltf_signal, htf_trend, mtf_trend, vol)
        ltf_signal.reasoning += (
            f" | MTF: HTF={htf_trend} MTF={mtf_trend} Vol={vol} "
            f"aligned_conf={ltf_signal.confidence:.2f}"
        )
        return ltf_signal

    def analyze_alignment(self) -> Dict:
        """Return alignment analysis for dashboard display."""
        htf_trend = self._detect_trend(self.htf, self.htf_bars)
        mtf_trend = self._detect_trend(self.mtf, self.mtf_bars)
        vol = self._detect_volatility(self.ltf, self.ltf_bars)
        aligned = htf_trend == mtf_trend or mtf_trend == "neutral"
        return {
            "htf_trend": htf_trend,
            "mtf_trend": mtf_trend,
            "volatility": vol,
            "aligned": aligned,
            "require_alignment": self.require_alignment,
            "htf_bars": self.htf_bars,
            "mtf_bars": self.mtf_bars,
            "ltf_bars": self.ltf_bars,
        }


class MultiTimeframeManager:
    """Manages multiple strategies across multiple timeframes."""

    def __init__(self):
        self._strategies: Dict[str, BaseStrategy] = {}
        self._configs: Dict[str, TimeframeConfig] = {}

    def add_strategy(self, name: str, strategy: BaseStrategy, config: TimeframeConfig):
        self._strategies[name] = strategy
        self._configs[name] = config

    def remove_strategy(self, name: str):
        self._strategies.pop(name, None)
        self._configs.pop(name, None)

    def list_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def run_all(
        self,
        htf_data: pd.DataFrame,
        mtf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
    ) -> Dict[str, Optional[Signal]]:
        """Run all strategies with MTF alignment."""
        results = {}
        for name, strategy in self._strategies.items():
            try:
                mtf = MultiTimeframeStrategy(
                    strategy=strategy,
                    htf_data=htf_data,
                    mtf_data=mtf_data,
                    ltf_data=ltf_data,
                )
                results[name] = mtf.align_signals()
            except Exception as e:
                results[name] = None
        return results

    def get_alignment_all(
        self,
        htf_data: pd.DataFrame,
        mtf_data: pd.DataFrame,
        ltf_data: pd.DataFrame,
    ) -> Dict[str, Dict]:
        """Get alignment analysis for all strategies."""
        analysis = {}
        for name, strategy in self._strategies.items():
            try:
                mtf = MultiTimeframeStrategy(
                    strategy=strategy,
                    htf_data=htf_data,
                    mtf_data=mtf_data,
                    ltf_data=ltf_data,
                )
                analysis[name] = mtf.analyze_alignment()
            except Exception as e:
                analysis[name] = {"error": str(e)}
        return analysis
