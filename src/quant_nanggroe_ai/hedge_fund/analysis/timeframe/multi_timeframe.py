"""
Multi-Timeframe Analysis System
Analyzes markets across multiple timeframes for confluence and alignment.
Based on "Timeframe Alignment" principles from trading education.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

import numpy as np
import pandas as pd


class TrendDirection(Enum):
    """Trend direction enumeration"""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Timeframe(Enum):
    """Standard trading timeframes"""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"
    MN = "1M"

    @property
    def minutes(self) -> int:
        """Convert timeframe to minutes."""
        mapping = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080, "1M": 43200}
        return mapping.get(self.value, 60)

    @property
    def hierarchy(self) -> int:
        """Return hierarchy level (higher = longer timeframe)."""
        hierarchy = {"1m": 1, "5m": 2, "15m": 3, "30m": 4, "1h": 5, "4h": 6, "1d": 7, "1w": 8, "1M": 9}
        return hierarchy.get(self.value, 5)


@dataclass
class TimeframeSignal:
    """Signal from a single timeframe"""

    timeframe: Timeframe
    trend: str  # BULLISH, BEARISH, NEUTRAL
    strength: float  # 0-1
    key_level: float
    entry_zone: Tuple[float, float]
    stop_loss: float
    take_profit: float
    confluence_score: float
    reasons: List[str]


@dataclass
class MultiTimeframeAnalysis:
    """Combined analysis from multiple timeframes"""

    ticker: str
    primary_trend: str
    secondary_trend: str
    alignment_score: float
    highest_tf: Timeframe
    signal_tf: Timeframe
    entry_direction: str
    confluence_factors: List[str]
    risk_assessment: Dict[str, float]
    recommended_tf: Timeframe
    timestamp: datetime = field(default_factory=datetime.now)


class TrendAnalyzer:
    """Analyze trend direction and strength across timeframes."""

    @staticmethod
    def calculate_ema_trend(close: pd.Series, periods: List[int] = [20, 50, 200]) -> Dict[str, str]:
        """Determine trend based on EMA crossover."""
        trends = {}
        for period in periods:
            ema = close.rolling(period).mean()
            if len(ema) < 2:
                trends[f"ema_{period}"] = "NEUTRAL"
                continue

            if close.iloc[-1] > ema.iloc[-1]:
                trends[f"ema_{period}"] = "BULLISH"
            elif close.iloc[-1] < ema.iloc[-1]:
                trends[f"ema_{period}"] = "BEARISH"
            else:
                trends[f"ema_{period}"] = "NEUTRAL"

        return trends

    @staticmethod
    def calculate_price_position_trend(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 20) -> Tuple[str, float]:
        """
        Calculate trend based on price position within range.
        Returns (trend, strength)
        """
        highest = high.rolling(lookback).max().iloc[-1]
        lowest = low.rolling(lookback).min().iloc[-1]
        current = close.iloc[-1]

        if highest == lowest:
            return TrendDirection.NEUTRAL, 0.0

        position = (current - lowest) / (highest - lowest)

        if position > 0.8:
            return TrendDirection.BULLISH, min(1.0, position)
        elif position < 0.2:
            return TrendDirection.BEARISH, min(1.0, 1 - position)
        else:
            return TrendDirection.NEUTRAL, 0.5

    @staticmethod
    def calculate_adx_trend(adx: pd.Series, di_plus: pd.Series, di_minus: pd.Series) -> Tuple[str, float]:
        """
        Determine trend from ADX and DI indicators.
        Returns (trend, strength)
        """
        current_adx = adx.iloc[-1] if len(adx) > 0 else 0
        current_di_plus = di_plus.iloc[-1] if len(di_plus) > 0 else 0
        current_di_minus = di_minus.iloc[-1] if len(di_minus) > 0 else 0

        # ADX must be above threshold for trend
        if current_adx < 20:
            return TrendDirection.NEUTRAL, current_adx / 40

        if current_di_plus > current_di_minus:
            return TrendDirection.BULLISH, min(1.0, current_adx / 50)
        else:
            return TrendDirection.BEARISH, min(1.0, current_adx / 50)

    @staticmethod
    def calculate_trend_strength(close: pd.Series, period: int = 20) -> float:
        """
        Calculate trend strength using ATR-normalized ADX.
        Returns 0-1 strength value.
        """
        # Calculate returns
        returns = close.pct_change()

        # Direction
        direction = returns.rolling(period).sum()

        # Volatility
        volatility = returns.rolling(period).std() * np.sqrt(252)

        if volatility.iloc[-1] == 0:
            return 0.5

        # Strength ratio
        strength = abs(direction.iloc[-1]) / (volatility.iloc[-1] + 1e-10)

        return min(1.0, strength / 2)  # Normalize to 0-1

    @staticmethod
    def calculate_support_resistance(high: pd.Series, low: pd.Series, close: pd.Series, lookback: int = 50, threshold: float = 0.02) -> Dict[str, List[float]]:
        """
        Calculate key support and resistance levels.
        """
        levels = {"resistance": [], "support": []}

        # Find swing highs and lows
        for i in range(lookback, len(high)):
            is_high = True
            for j in range(max(0, i - 5), min(len(high), i + 6)):
                if j != i and high.iloc[j] >= high.iloc[i]:
                    is_high = False
                    break
            if is_high:
                levels["resistance"].append(high.iloc[i])

        for i in range(lookback, len(low)):
            is_low = True
            for j in range(max(0, i - 5), min(len(low), i + 6)):
                if j != i and low.iloc[j] <= low.iloc[i]:
                    is_low = False
                    break
            if is_low:
                levels["support"].append(low.iloc[i])

        return levels


class MultiTimeframeAnalyzer:
    """
    Comprehensive multi-timeframe analysis system.

    Analyzes alignment across timeframes to find high-probability setups.
    """

    def __init__(self, timeframes: List[Timeframe] = None):
        """
        Initialize analyzer.

        Args:
            timeframes: List of timeframes to analyze (default: H4, D1, W1)
        """
        self.timeframes = timeframes or [Timeframe.H4, Timeframe.D1, Timeframe.W1]
        self.trend_analyzer = TrendAnalyzer()

        # Ensure timeframes are sorted by hierarchy
        self.timeframes.sort(key=lambda x: x.hierarchy, reverse=True)

    def analyze(self, data_dict: Dict[Timeframe, pd.DataFrame], ticker: str = "UNKNOWN") -> MultiTimeframeAnalysis:
        """
        Perform multi-timeframe analysis.

        Args:
            data_dict: Dict of {Timeframe: OHLCV DataFrame}
            ticker: Asset ticker

        Returns:
            MultiTimeframeAnalysis with combined signals
        """
        timeframe_signals = {}

        # Analyze each timeframe
        for tf in self.timeframes:
            if tf not in data_dict:
                continue

            df = data_dict[tf]
            signal = self._analyze_timeframe(df, tf)
            timeframe_signals[tf] = signal

        if not timeframe_signals:
            return MultiTimeframeAnalysis(ticker=ticker, primary_trend="UNKNOWN", secondary_trend="UNKNOWN", alignment_score=0.0, highest_tf=self.timeframes[0] if self.timeframes else Timeframe.H1, signal_tf=Timeframe.H1, entry_direction="HOLD", confluence_factors=["No data available"], risk_assessment={})

        # Determine alignment
        trends = [s.trend for s in timeframe_signals.values()]
        strengths = [s.strength for s in timeframe_signals.values()]

        # Primary trend from highest timeframe
        primary_trend = self._get_aligned_trend(list(timeframe_signals.keys()), list(timeframe_signals.values()), use_highest=True)

        # Secondary trend from middle timeframe
        secondary_trend = self._get_aligned_trend(list(timeframe_signals.keys()), list(timeframe_signals.values()), use_highest=False)

        # Calculate alignment score
        alignment_score = self._calculate_alignment(timeframe_signals)

        # Determine entry direction
        entry_direction = self._determine_entry_direction(timeframe_signals)

        # Find confluence factors
        confluence_factors = self._find_confluence(timeframe_signals)

        # Risk assessment
        risk_assessment = self._assess_risk(timeframe_signals)

        # Determine recommended timeframe for entries
        recommended_tf = self._get_entry_timeframe(timeframe_signals)

        # Highest timeframe signal
        highest_tf = max(timeframe_signals.keys(), key=lambda x: x.hierarchy)
        signal_tf = max(timeframe_signals.keys(), key=lambda x: timeframe_signals[x].confluence_score)

        return MultiTimeframeAnalysis(ticker=ticker, primary_trend=primary_trend, secondary_trend=secondary_trend, alignment_score=alignment_score, highest_tf=highest_tf, signal_tf=signal_tf, entry_direction=entry_direction, confluence_factors=confluence_factors, risk_assessment=risk_assessment, recommended_tf=recommended_tf)

    def _analyze_timeframe(self, df: pd.DataFrame, timeframe: Timeframe) -> TimeframeSignal:
        """Analyze a single timeframe."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df.get("volume", pd.Series([1] * len(close)))

        # Calculate trend indicators
        ema_trends = self.trend_analyzer.calculate_ema_trend(close)
        position_trend, position_strength = self.trend_analyzer.calculate_price_position_trend(high, low, close)

        # Calculate trend strength
        trend_strength = self.trend_analyzer.calculate_trend_strength(close)

        # Get support/resistance
        sr_levels = self.trend_analyzer.calculate_support_resistance(high, low, close)

        # Determine overall trend
        bullish_count = sum(1 for v in ema_trends.values() if v == TrendDirection.BULLISH)
        bearish_count = sum(1 for v in ema_trends.values() if v == TrendDirection.BEARISH)

        if bullish_count > bearish_count:
            trend = TrendDirection.BULLISH
            strength = (bullish_count / len(ema_trends) + position_strength + trend_strength) / 3
        elif bearish_count > bullish_count:
            trend = TrendDirection.BEARISH
            strength = (bearish_count / len(ema_trends) + (1 - position_strength) + trend_strength) / 3
        else:
            trend = TrendDirection.NEUTRAL
            strength = 0.5

        # Key level (nearest support/resistance)
        current_price = close.iloc[-1]
        if sr_levels["resistance"]:
            nearest_res = min([r for r in sr_levels["resistance"] if r >= current_price], default=max(sr_levels["resistance"]))
        else:
            nearest_res = current_price * 1.02

        if sr_levels["support"]:
            nearest_sup = max([s for s in sr_levels["support"] if s <= current_price], default=min(sr_levels["support"]))
        else:
            nearest_sup = current_price * 0.98

        key_level = nearest_res if trend == TrendDirection.BULLISH else nearest_sup

        # Entry zone
        if trend == TrendDirection.BULLISH:
            entry_zone = (current_price, nearest_res)
            stop_loss = nearest_sup
            take_profit = nearest_res + (nearest_res - nearest_sup)
        elif trend == TrendDirection.BEARISH:
            entry_zone = (current_price, nearest_sup)
            stop_loss = nearest_res
            take_profit = nearest_sup - (nearest_res - nearest_sup)
        else:
            entry_zone = (current_price * 0.99, current_price * 1.01)
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.02

        # Confluence score
        confluence = bullish_count / len(ema_trends) + position_strength + trend_strength + (1 if trend == TrendDirection.BULLISH else 0) * 0.2

        # Reasons
        reasons = [f"{k}: {v}" for k, v in ema_trends.items()]
        reasons.append(f"Price Position: {position_trend} ({position_strength:.1%})")
        reasons.append(f"Trend Strength: {trend_strength:.1%}")

        return TimeframeSignal(timeframe=timeframe, trend=trend, strength=strength, key_level=key_level, entry_zone=entry_zone, stop_loss=stop_loss, take_profit=take_profit, confluence_score=confluence, reasons=reasons)

    def _get_aligned_trend(self, timeframes: List[Timeframe], signals: List[TimeframeSignal], use_highest: bool = True) -> str:
        """Get the dominant trend from aligned timeframes."""
        if use_highest:
            # Weight highest timeframe more
            weights = [2 ** (len(timeframes) - i - 1) for i in range(len(timeframes))]
        else:
            weights = [1] * len(timeframes)

        bullish_score = sum(s.strength if s.trend == TrendDirection.BULLISH else 0 for s, w in zip(signals, weights)) * weights[0]
        bearish_score = sum(s.strength if s.trend == TrendDirection.BEARISH else 0 for s, w in zip(signals, weights)) * weights[0]

        if bullish_score > bearish_score * 1.2:
            return TrendDirection.BULLISH
        elif bearish_score > bullish_score * 1.2:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL

    def _calculate_alignment(self, signals: Dict[Timeframe, TimeframeSignal]) -> float:
        """Calculate how well timeframes are aligned."""
        if len(signals) < 2:
            return 1.0

        trends = [s.trend for s in signals.values()]
        strengths = [s.strength for s in signals.values()]

        # Agreement score
        if len(set(trends)) == 1:
            agreement = 1.0
        elif TrendDirection.NEUTRAL in trends:
            agreement = 0.7
        else:
            agreement = 0.5

        # Strength consistency
        strength_consistency = 1 - np.std(strengths) if len(strengths) > 1 else 1.0

        return agreement * strength_consistency

    def _determine_entry_direction(self, signals: Dict[Timeframe, TimeframeSignal]) -> str:
        """Determine entry direction based on multi-timeframe alignment."""
        if len(signals) < 2:
            return "WAIT"

        # Get highest and middle timeframe signals
        sorted_tfs = sorted(signals.keys(), key=lambda x: x.hierarchy, reverse=True)
        highest = signals[sorted_tfs[0]]
        middle = signals[sorted_tfs[1]]

        # Strong alignment: higher TF confirms lower TF
        if highest.trend == middle.trend and highest.trend != "NEUTRAL":
            return f"{highest.trend}_CONFIRMED"

        # Divergence warning
        if highest.trend != middle.trend and highest.trend != "NEUTRAL":
            return "DIVERGENCE"

        return "WAIT"

    def _find_confluence(self, signals: Dict[Timeframe, TimeframeSignal]) -> List[str]:
        """Find confluence factors across timeframes."""
        factors = []

        sorted_tfs = sorted(signals.keys(), key=lambda x: x.hierarchy, reverse=True)

        # Trend alignment
        trends = [s.trend for s in signals.values()]
        if len(set(trends)) == 1 and trends[0] != "NEUTRAL":
            factors.append(f"All timeframes aligned {trends[0]}")

        # Support/resistance confluence
        levels = [s.key_level for s in signals.values()]
        price = signals[sorted_tfs[-1]].entry_zone[0]  # Current price from lowest TF

        for i, tf in enumerate(sorted_tfs):
            level = signals[tf].key_level
            if abs(level - price) / price < 0.02:  # Within 2%
                factors.append(f"{tf.value} key level near current price")

        # Trend strength
        avg_strength = np.mean([s.strength for s in signals.values()])
        if avg_strength > 0.7:
            factors.append(f"Strong trend across timeframes ({avg_strength:.1%})")

        return factors[:5]  # Top 5 factors

    def _assess_risk(self, signals: Dict[Timeframe, TimeframeSignal]) -> Dict[str, float]:
        """Assess risk based on multi-timeframe analysis."""
        sorted_tfs = sorted(signals.keys(), key=lambda x: x.hierarchy, reverse=True)

        # Stop loss distance (from lowest timeframe)
        lowest = signals[sorted_tfs[-1]]
        stop_distance = abs(lowest.entry_zone[0] - lowest.stop_loss)

        # Risk per trade (1% of account per trade)
        risk_per_trade = 0.01

        # Position size based on stop
        position_size = risk_per_trade / (stop_distance / lowest.entry_zone[0] + 1e-10)

        return {"stop_distance_pct": stop_distance / lowest.entry_zone[0] * 100, "max_position_size": min(position_size, 0.25), "reward_risk_ratio": abs(lowest.take_profit - lowest.entry_zone[0]) / (stop_distance + 1e-10), "timeframe_agreement": self._calculate_alignment(signals)}  # Max 25%

    def _get_entry_timeframe(self, signals: Dict[Timeframe, TimeframeSignal]) -> Timeframe:
        """Get recommended entry timeframe."""
        # Find timeframe with best confluence
        best_tf = max(signals.keys(), key=lambda x: signals[x].confluence_score)
        return best_tf


class TimeframeAlignmentScanner:
    """
    Scanner for finding assets with aligned multi-timeframe setups.
    """

    def __init__(self, min_alignment: float = 0.7):
        """
        Initialize scanner.

        Args:
            min_alignment: Minimum alignment score for signal
        """
        self.min_alignment = min_alignment
        self.analyzer = MultiTimeframeAnalyzer()

    def scan(self, assets: Dict[str, Dict[Timeframe, pd.DataFrame]], min_alignment: float = None) -> List[Tuple[str, MultiTimeframeAnalysis]]:
        """
        Scan multiple assets for aligned setups.

        Args:
            assets: Dict of {ticker: {Timeframe: OHLCV DataFrame}}
            min_alignment: Minimum alignment threshold

        Returns:
            List of (ticker, analysis) tuples, sorted by alignment score
        """
        min_align = min_alignment or self.min_alignment
        results = []

        for ticker, data in assets.items():
            try:
                analysis = self.analyzer.analyze(data, ticker)
                if analysis.alignment_score >= min_align:
                    results.append((ticker, analysis))
            except Exception as e:
                logger.error(f"Error analyzing {ticker}: {e}")

        # Sort by alignment score
        results.sort(key=lambda x: x[1].alignment_score, reverse=True)

        return results


# Convenience functions
def analyze_multi_timeframe(data_dict: Dict[str, pd.DataFrame], ticker: str = "UNKNOWN") -> MultiTimeframeAnalysis:
    """Quick multi-timeframe analysis."""
    analyzer = MultiTimeframeAnalyzer()
    return analyzer.analyze(data_dict, ticker)


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np

    np.random.seed(42)
    dates_d1 = pd.date_range(start="2023-01-01", periods=252, freq="D")
    dates_h4 = pd.date_range(start="2023-01-01", periods=252 * 4, freq="4h")

    # Generate synthetic data
    def generate_tf_data(dates, volatility=0.02):
        returns = np.random.randn(len(dates)) * volatility + 0.0005
        close = 100 * np.cumprod(1 + returns)
        return pd.DataFrame({"open": close * (1 + np.random.randn(len(dates)) * 0.001), "high": close * (1 + np.random.rand(len(dates)) * 0.02), "low": close * (1 - np.random.rand(len(dates)) * 0.02), "close": close, "volume": np.random.randint(1000000, 10000000, len(dates))}, index=dates)

    data = {Timeframe.D1: generate_tf_data(dates_d1, 0.015), Timeframe.H4: generate_tf_data(dates_h4, 0.02), Timeframe.W1: generate_tf_data(dates_d1[::7], 0.01)}

    print("Multi-Timeframe Analysis Test")
    print("=" * 50)

    analyzer = MultiTimeframeAnalyzer([Timeframe.H4, Timeframe.D1, Timeframe.W1])
    result = analyzer.analyze(data, "SAMPLE")

    print(f"Ticker: {result.ticker}")
    print(f"Primary Trend ({result.highest_tf.value}): {result.primary_trend}")
    print(f"Secondary Trend ({result.signal_tf.value}): {result.secondary_trend}")
    print(f"Alignment Score: {result.alignment_score:.1%}")
    print(f"Entry Direction: {result.entry_direction}")
    print(f"Recommended TF: {result.recommended_tf.value}")
    print(f"\nConfluence Factors:")
    for factor in result.confluence_factors:
        print(f"  - {factor}")
    print(f"\nRisk Assessment:")
    for k, v in result.risk_assessment.items():
        print(f"  {k}: {v:.3f}")

    print("\n" + "=" * 50)
    print("Scan Test:")

    scanner = TimeframeAlignmentScanner(min_alignment=0.6)
    assets = {"ASSET1": data, "ASSET2": data, "ASSET3": data}
    results = scanner.scan(assets)
    print(f"Found {len(results)} aligned assets")
